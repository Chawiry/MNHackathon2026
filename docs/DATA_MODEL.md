# Domain data model (implemented)

Models implemented across six Django apps. Features build against these.

## Apps

- **`accounts`** — `User` (custom, `AbstractUser`)
- **`teams`** — `Department`, `Team`, `TeamMembership`, `TeamSkillRequirement`
- **`skills`** — `SkillCategory`, `Skill`, `SkillRelationship`, `SkillProficiency`,
  `Certificate`, `CertificateAward`, `SkillCriticalityAssessment`, `SkillFutureDemand`
- **`projects`** — `Project`
- **`profiles`** — `DevelopmentActivity`, `ExperienceEntry`, `PerformanceReview`
- **`insights`** — `StrategicInitiative`, `TeamFeedback`, `ReadinessSnapshot`
  (analytics logic lives in pure services in `insights/services.py`)

## Key decisions

- **User tiers**: `employee`, `team_manager`, `leadership` (field on `User`). Roles gate what each tier can see/do.
- **Proficiency scale**: 1–5 (`novice … expert`), shared `SkillProficiency.Level` choices.
- **Approval workflow**: each `User × Skill` is a single `SkillProficiency` row with a `status`
  (`pending` / `approved` / `rejected`). Manager recordings start approved; employee
  self-reports start pending until a manager approves. Only `approved` rows feed analytics.
  `CertificateAward` follows the same `status` + `approved_by` pattern (self-submitted
  certificates are pending until a manager approves).
- **Certificates back skills**: each `CertificateAward` records the `skill` it confirms and the
  `level` it implies. Approving an award upserts that `User × Skill` `SkillProficiency` row as
  approved (certificate wins over an existing self-report, but `reported_by` stays the owner so
  they can self-assess again later). Rejects never touch proficiencies. `expires_on` is collected
  and shown as an **expired** flag only — it does not downgrade coverage.
- **Provisioned accounts (no self-service)**: there is no public signup. Leadership creates
  accounts and assigns any tier on `/users/`; team managers create employee accounts that are
  added to a team they manage in one step. Re-tiers, deactivations, and the expected leave date
  (a leadership-estimated departure on `User.expected_leave_date`, used by stay/depletion
  analytics) are leadership-only.
- **Departments & multi-team**: `Team` belongs to an optional `Department`; users join teams via
  `TeamMembership` (a manager role is a membership role). The leadership dashboard can be scoped
  to one department, which rescopes both the demand (that department's team requirements) and the
  holder pool (that department's memberships).
- **Projects spawn teams**: leadership creates a **Project**, which auto-spawns the project's
  first **Team** and assigns the chosen **team manager** (a `TeamMembership` with `role=manager`).
  A project can hold one or more teams; team names are unique per project
  (`unique_project_team_name`). Team managers only manage teams they are part of.
- **Requirements are per-team**: each team owns its own **skill requirements**
  (`TeamSkillRequirement`; unique per `team × skill`). New teams start with none; team managers
  edit their own team's requirements and leadership can edit any team's. Coverage is computed
  against that team's own requirements only.
- **Current-role vs next-position gaps**: each requirement has a `purpose` (`current` /
  `promotion`). Gap analytics label promotion requirements as "next position" so an employee's
  development plan distinguishes today's role gaps from gaps blocking a future role.
- **Gig allocation**: for each requirement, `requirement_candidates(req)` suggests org-wide
  approved employees at/above the required level — excluding the team itself — ranked by level,
  fewest team memberships, recency (capped ~5). `add_candidate` assigns a chosen candidate as a
  team member in one click (managers for managed teams, leadership for any team). Suggestions
  are only shown while the requirement still has unmet spots
  (`requirement_missing` = `people_needed` − qualifying team members).
- **Profile records stay simple**: `DevelopmentActivity` (course / mentoring / job rotation with a
  status and completion date), `ExperienceEntry` (role history), and `PerformanceReview` (period,
  rating 1–5, goals/feedback/achievements) are just documented profile data — no workflow beyond
  provenance timestamps. They are surfaced on the employee profile page.
- **Critical skills**: derived, not stored — from `TeamSkillRequirement` on teams for active
  projects where `importance = critical`, combined with coverage/concentration computed over
  approved `SkillProficiency` rows. `SkillCriticalityAssessment` stores the versioned,
  department-scoped 0–100 score (computed by `criticality_formula`); `SkillFutureDemand` records
  emerging/growing/stable/declining projections with a confidence level.
- **Cascade & upward feedback**: `StrategicInitiative` chains board → c-suite → department → team.
  Only a parent's `approved_content` is inherited by the child draft. Team leads raise
  `TeamFeedback` flags that roll up into `feedback_risk_rollup()` for leadership.

## Relationships

```
User ──< TeamMembership >── Team >── Department
                             >── Project
User ──< SkillProficiency >── Skill ──> SkillCategory
User ──< CertificateAward >(skill)── Skill
Skill ──< SkillRelationship >── Skill      (related / transfers)
User ──< TeamSkillRequirement-holder >…   (approved profs only)
Team ──< TeamSkillRequirement >── Skill
Department ──< SkillCriticalityAssessment >── Skill   (versioned per dept)
Skill ──< SkillFutureDemand             (1..n projections)
StrategicInitiative ──< StrategicInitiative (parent)  (board→csuite→department→team)
StrategicInitiative ──< TeamFeedback >─ raised_by User
User ──< DevelopmentActivity >(skill)── Skill
User ──< ExperienceEntry
User ──< PerformanceReview
ReadinessSnapshot                      (org / per-department, timestamped)
```

## Analytic queries (`insights/services.py` — `GET /insights/`, leadership)

- `at_risk_skills(department=None)` — knowledge bottlenecks: low bus factor (≤ 2 approved
  holders) and/or supply–demand shortfall (requirement slots > approved holders). Optionally
  scoped to a department's demand + holder pool.
- `expected_stays()` — remaining months per active user from `expected_leave_date` (leadership-set).
- `skill_depletion(department=None)` — for each at-risk skill, the horizon the company retains it =
  the **last holder's expected leave date**; `unknown` when a holder hasn't a date. Zero holders
  when the last one leaves.
- `successors(department=None)` — people below an at-risk skill's required level, ranked by
  `(required − level) × MONTHS_PER_LEVEL` estimated months to readiness (top 3).
- `succession_for_skill(skill)` / `succession_report(department=None)` — successors via direct
  incipient proficiency or the skills graph; candidate readiness is
  `(direct/5 × 60) + (best related proficiency / 5 × 40)`, coverage ratio = qualified successors
  ÷ holders (fractional pipeline fallback when nobody has crossed the bar).
- `readiness_score(department=None)` — headline 0–100 =
  `100 × Σ(criticality × coverage) / Σ(criticality)` over the department's/org's critical skills,
  timestamped into `ReadinessSnapshot` for the trend (`readiness_trend`).
- `employee_gaps(user)` — per-requirement gaps with a priority =
  `min(50, gap × 10) + criticality×0.3 + importance + future-demand boost`, sorted descending;
  `purpose` distinguishes current-role vs next-position gaps.
- `recommendation_for_gap` / `development_recommendations` — an IF→THEN rule set (Gap 5):
  1. adjacent skill via the graph at ≥ 3 → targeted training/certification;
  2. nothing nearby → structured course + mentoring (named mentor when a holder exists);
  3. skill held at ≥ 4 elsewhere → job rotation/shadowing;
  4. critical skill with ≤ 1 high-proficiency holder → knowledge-transfer project (extra);
  5. emerging/growing high-confidence skill with ≤ 2 holders → external certification +
     community of practice (extra).
- `plan_readiness(project)` — readiness = **manning % × qualification % × availability %** per
  requirement, with diagnosis cases (hiring / qualification / availability / ready);
  `project_readiness_summary` averages the rows.
- `simulate_departure(user)` / `simulate_skill_adoption(skill)` — read-only what-if sandbox
  (coverage before/after, KT flags, hiring recommendation, training horizon).
- `draft_initiative_content` / `feedback_risk_rollup` — deterministic cascade drafting over live
  data and unflagged-team aggregation.
- Tuneable constants: `MONTHS_PER_LEVEL = 6`, `BUS_FACTOR_THRESHOLD = 2`, `SUCCESSOR_CAP = 3`,
  `CRITICALITY_THRESHOLD = 60`, `ANON_GROUP_SIZE = 5`, `QUALIFIED_SUCCESSOR_BAR = 60`,
  `READY_TODAY_BAR = 80`, `MAX_TEAMS_AVAILABILITY = 2`.

## Anonymization policy (phase 3)

Any aggregate over a group smaller than `ANON_GROUP_SIZE` (5) is suppressed or shown as a range
above the team-lead tier: exact counts become the band `1–4`, shortfalls become `lo–hi`, and
individual names are masked unless drill-down is explicitly approved.

## Seeded data

- `skills/fixtures/starter_skills.json` — 5 categories, 16 skills. Load with
  `python manage.py loaddata starter_skills` (already applied to dev DB).
- `python manage.py seed_demo` — 53 users, 5 departments, 9 teams, 217 approved proficiencies,
  56 skill requirements (incl. 5 promotion/purpose=promotion), 33 graph edges, 10 future-demand
  rows, 200 criticality assessments, and profile entries (development activities, experiences,
  performance reviews).
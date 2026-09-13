# Domain data model (implemented)

Models implemented across four Django apps. Features build against these.

## Apps

- **`accounts`** — `User` (custom, `AbstractUser`)
- **`teams`** — `Team`, `TeamMembership`, `TeamSkillRequirement`
- **`skills`** — `SkillCategory`, `Skill`, `SkillProficiency`, `Certificate`, `CertificateAward`
- **`projects`** — `Project`
- **`insights`** — no models; leadership analytics (pure services in `insights/services.py`)

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
- **Multi-team**: users join teams via `TeamMembership` (a manager role is a membership role).
- **Projects spawn teams**: leadership creates a **Project**, which auto-spawns the project's
  first **Team** and assigns the chosen **team manager** (a `TeamMembership` with `role=manager`).
  A project can hold one or more teams; team names are unique per project
  (`unique_project_team_name`). Team managers only manage teams they are part of.
- **Requirements are per-team**: each team owns its own **skill requirements**
  (`TeamSkillRequirement`; unique per `team × skill`). New teams start with none; team managers
  edit their own team's requirements and leadership can edit any team's. Coverage is computed
  against that team's own requirements only.
- **Gig allocation**: for each requirement, `requirement_candidates(req)` suggests org-wide
  approved employees at/above the required level — excluding the team itself — ranked by level,
  fewest team memberships, recency (capped ~5). `add_candidate` assigns a chosen candidate as a
  team member in one click (managers for managed teams, leadership for any team). Suggestions
  are only shown while the requirement still has unmet spots
  (`requirement_missing` = `people_needed` − qualifying team members).
- **Critical skills**: derived, not stored — from `TeamSkillRequirement` on teams for active
  projects where `importance = critical`, combined with coverage/concentration computed over
  approved `SkillProficiency` rows.

## Relationships

```
User ──< TeamMembership >── Team >── Project
User ──< SkillProficiency >── Skill ──> SkillCategory
User ──< CertificateAward >(skill)── Skill
Team ──< TeamSkillRequirement >── Skill
```

## Analytic queries (`insights/services.py` — `GET /insights/`, leadership)

- `at_risk_skills()` — knowledge bottlenecks: low bus factor (≤ 2 approved holders) and/or
  supply–demand shortfall (requirement slots > approved holders).
- `expected_stays()` — remaining months per active user from `expected_leave_date` (leadership-set).
- `skill_depletion()` — for each at-risk skill, the horizon the company retains it = the **last
  holder's expected leave date**; `unknown` when a holder hasn't a date. Zero holders when the
  last one leaves.
- `successors()` — people below an at-risk skill's required level, ranked by
  `(required − level) × MONTHS_PER_LEVEL` estimated months to readiness (top 3).
- Tuneable constants: `MONTHS_PER_LEVEL = 6`, `BUS_FACTOR_THRESHOLD = 2`, `SUCCESSOR_CAP = 3`.

## Seeded data

`skills/fixtures/starter_skills.json` — 5 categories, 16 skills. Load with
`python manage.py loaddata starter_skills` (already applied to dev DB).
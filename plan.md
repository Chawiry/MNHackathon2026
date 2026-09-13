# AI-Powered Workforce Skills Intelligence — Implementation Plan

This is the plan we follow. **We do not advance to the next phase until the
current phase is complete and the user says so.**

## Current status: Phase 6 (profile models + promotion gaps) implemented — awaiting user review before Phase 7

## Scope decisions (locked)

- **Profile models (§1):** lightweight — `DevelopmentActivity`, `ExperienceEntry`,
  `PerformanceReview` surfaced on the profile page. No periodic-evaluation
  scheduling or multi-source soft-skill assessment this round.
- **Leader tiers (§18):** keep 3 tiers (`employee`, `team_manager`,
  `leadership`) + a department filter on the leadership dashboard.
  Aggregates above team-lead are anonymized.
- **Leadership cascade (§17):** minimal UI — initiative create/approve flow +
  team-feedback raise/resolve + aggregated risk rollup on the dashboard.

## What exists already (do not rebuild)

- `skills` models: `SkillCategory` (+domain), `Skill`, `SkillRelationship`
  (related/prerequisite/transfers + weight), `SkillProficiency` (1–5, status,
  `last_used`, `validation_source`, evidence), `Certificate`/`CertificateAward`,
  `SkillCriticalityAssessment` (versioned, per-department),
  `SkillFutureDemand` (`confidence_level`).
- `teams` models: `Department`, `Team`, `TeamMembership`,
  `TeamSkillRequirement`.
- `accounts`: custom `User` with `tier`, `expected_leave_date`.
- `insights.models`: `StrategicInitiative`, `TeamFeedback`, `ReadinessSnapshot`.
- `insights.services` (logic, partially unwired):
  - bottlenecks, expected stays, skill depletion, successors
  - anonymization guards (`guarded_count`, `guard_display_name`)
  - criticality formula, rarity, risk matrix
  - succession coverage + readiness (Gap 3), org readiness score + trend
  - employee gaps + priority, 5-rule recommendation engine (Gap 5)
  - future skills, plan readiness (Manning × Qualification × Availability)
  - what-if simulations (departure, skill adoption)
- Gig allocation (`requirement_candidates`/`add_candidate`) is already wired
  into Teams/Projects UI.
- Tiers + approval workflow (proficiencies, certificates) are wired.

## Gap list this plan closes

| # | Spec | Work |
|---|------|------|
| G1 | §3, §20 | Synthetic org dataset + skill-graph edges (foundation) |
| G2 | §6–9, §10, §11, §14, §15 | Wire strategic layer into the UI |
| G3 | §19 | Enforce anonymization above team-lead tier |
| G4 | §8, §13 | Succession "risk cards" + KT recommendation display |
| G5 | §18 | Department filter on leadership dashboard |
| G6 | §17 | Minimal cascade / feedback UI + risk rollup |
| G7 | §1, §4 | Lightweight profile models + current-vs-promotion requirements |
| G8 | §5, §11 | Gaps + development plan on the employee profile page |
| G9 | — | Tests for the strategic layer and seed command |

---

## Phase 1 — Synthetic org dataset (foundation)

No dataset currently exists; only a 16-skill fixture. Everything else computes
against this, so it goes first. Also: **no `SkillRelationship` edges are
seeded**, so graph-driven rules (Rule 1, successor-via-related-skill) never
fire — the seed must add them.

- `core/seed_data.py` — deterministic org definition:
  - 4–5 departments, 2–3 teams per department
  - ~48 employees; each with role, department, team, proficiencies
  - ~20 skills (extend `starter_skills.json` with ~4 new, incl. an emerging
    "Generative AI / LLM" skill); 2–3 domains; technical + soft mix
  - ~25 `SkillRelationship` edges (related / prerequisite / transfers)
  - ~250 approved `SkillProficiency` rows with real overlap and deliberate
    scarcity (several skills held by only 1–2 people at proficiency ≥4)
  - one team with ≤4 people (for the anonymization rule)
  - critical `TeamSkillRequirement`s (importance + `people_needed`)
  - a few `CertificateAward`s (approved)
  - expected-leave dates on several key holders (drives depletion)
  - `SkillFutureDemand` rows, incl. the emerging skill with low org proficiency
  - demo accounts: ≥1 leadership, ≥1 team_manager, ≥1 employee
- `core/management/commands/seed_demo.py` — idempotent:
  - flush + reseed (dev only), or get-or-create
  - run `insights.services.reassess_all()` to generate
    `SkillCriticalityAssessment`s
  - seed initial `ReadinessSnapshot`s so the trend has data
- Update `README.md` with the seed command.
- Add a test asserting seed invariants (employee count range, ≥1 small team,
  ≥1 concentration-risk skill, ≥1 skill relationship edge). **Tests green.**

**Done when:** `manage.py seed_demo` reproducibly creates the full org and the
invariant test passes.

## Phase 2 — Wire the strategic layer to the UI

- `insights` views/templates:
  - Readiness headline score + per-department grid + trend from snapshots (§9)
  - Risk matrix: criticality × rarity (G4) (§6–7)
  - Succession risk cards: holders, successors, readiness %, coverage ratio,
    "N ready today", KT-recommended flag (§8) (G4)
  - Future skills demand vs today's scarcity (§10)
  - Existing bottlenecks / depletion / stays remain
  - GitHub-style sections separated for demo clarity
- What-if sandbox (§15): pick an employee → `simulate_departure`; pick a skill
  → `simulate_skill_adoption`. Read-only.
- `projects` view/template: `plan_readiness` table (Manning × Qualification ×
  Availability + diagnosis) on the project detail page (§14).
- `skills/me.html`: "<user>'s gaps & development plan" via
  `development_recommendations` — gap, priority, recommended action, reason,
  extras (G8) (§5, §11).
- **Done when:** every listed section renders with seeded data and is
  leadership/employee-gated correctly.

## Phase 3 — Enforce anonymization (Gap 2, §19)

- Apply `guarded_count` / `guard_display_name` to all leadership-level
  aggregate views.
- Group size < 5 → counts shown as range (e.g. "1–3 people") and individual
  names masked; drill-down disabled by default.
- Add tests: small team (<5) forces coarsening; a team ≥5 shows exact data.
- **Done when:** no raw name or exact count leaks for <5-person groups above
  team-lead tier.

## Phase 4 — Leadership cascade (minimal UI, §17)

- Add a "Cascade" section to the insights app:
  - List/create `StrategicInitiative`s; deterministic draft generator fills
    `ai_draft_content` (template text from readiness/gap data)
  - Human approve → copies/sets `approved_content`, `approved_by`,
    `approved_at`; only approved content is used downstream
  - Children inherit parent's `approved_content` (`inherited_content`)
- `TeamFeedback`: team leads raise flags (feasibility/workforce/skill/
  readiness/other); leadership resolves; unresolved flags roll up as
  aggregated readiness risks on the dashboard.
- **Done when:** an initiative can be drafted, approved, and cascaded, and a
  feedback flag rolls up visibly.

## Phase 5 — Department scoping (§18)

- Add a department filter to the leadership dashboard (readiness, risk,
  succession, bottlenecks scoped per department).
- Aggregates stay anonymized (Phase 3).
- **Done when:** choosing a department rescopes all dashboard sections.

## Phase 6 — Lightweight profile models (§1, §4)

- New models (in `skills` or a `profiles`-style location):
  - `DevelopmentActivity`: type (course / mentoring / job rotation), skill,
    status, completed_at, note
  - `ExperienceEntry`: role/position, org, start/end, summary
  - `PerformanceReview`: period, rating, goals, feedback, achievements
- Surface all on the employee profile page alongside proficiencies/certificates.
- Add `purpose` (`current` / `promotion`) to `TeamSkillRequirement` so gap
  logic can show current-role vs next-position gaps (§4).
- **Done when:** profile pages show the new sections and promotion gaps appear
  in the gap list.

## Phase 7 — Tests & verification

- Unit tests for:
  - seed command invariants + idempotence
  - succession coverage math (readiness %, coverage ratio)
  - readiness score formula
  - gap priority ordering
  - all five recommendation rules
  - plan-readiness diagnosis (Case A–D)
  - what-if departure / adoption
  - anonymization rule (<5 group)
  - cascade approval flow
- Run `manage.py check`, the full test suite, and a manual demo pass through
  every seeded scenario.
- Update `docs/DATA_MODEL.md` and `README.md`.
- **Done when:** full suite green and the manual demo walkthrough succeeds.

---

## Verification commands (Windows dev environment)

```sh
.venv\Scripts\python.exe manage.py check
.venv\Scripts\python.exe manage.py test
.venv\Scripts\python.exe manage.py seed_demo
.venv\Scripts\python.exe manage.py runserver
```
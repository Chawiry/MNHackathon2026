# Domain data model (implemented)

Models implemented across four Django apps. Features build against these.

## Apps

- **`accounts`** — `User` (custom, `AbstractUser`)
- **`teams`** — `Team`, `TeamMembership`
- **`skills`** — `SkillCategory`, `Skill`, `SkillProficiency`, `Certificate`, `CertificateAward`
- **`projects`** — `Project`, `ProjectSkillRequirement`

## Key decisions

- **User tiers**: `employee`, `team_manager`, `leadership` (field on `User`). Roles gate what each tier can see/do.
- **Proficiency scale**: 1–5 (`novice … expert`), shared `SkillProficiency.Level` choices.
- **Approval workflow**: each `User × Skill` is a single `SkillProficiency` row with a `status`
  (`pending` / `approved` / `rejected`). Manager recordings start approved; employee
  self-reports start pending until a manager approves. Only `approved` rows feed analytics.
  `CertificateAward` follows the same `status` + `approved_by` pattern (self-submitted
  certificates are pending until a manager approves).
- **Multi-team**: users join teams via `TeamMembership` (a manager role is a membership role).
- **Critical skills**: derived, not stored — from `ProjectSkillRequirement` on **active**
  projects where `importance = critical`, combined with coverage/concentration computed over
  approved `SkillProficiency` rows.

## Relationships

```
User ──< TeamMembership >── Team
User ──< SkillProficiency >── Skill ──> SkillCategory
User ──< CertificateAward >── Certificate
Project ──< ProjectSkillRequirement >── Skill
```

## Analytic queries (no extra tables needed)

- Coverage / gaps: compare the max or avg required level per active project vs the best
  approved level per skill across the org/team.
- Concentration / succession risk: count of approved holders per skill (few holders =
  high concentration), optionally broken down by role/team.
- Pending review queue: `SkillProficiency.objects.filter(status="pending")`.

## Seeded data

`skills/fixtures/starter_skills.json` — 5 categories, 16 skills. Load with
`python manage.py loaddata starter_skills` (already applied to dev DB).
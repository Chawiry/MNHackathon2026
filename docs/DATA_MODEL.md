# Agreed domain model (direction for future milestones, not yet implemented)

These are the intended models agreed with the team. Features build against this
shape so later milestones stay consistent.

## Entities

- **User** — Django's built-in auth user. Roles modeled with Django groups
  (`admin`, `manager`, `member`).
- **Team** — an org unit (the thing a "team skill management solution" manages).
  Has a name, optional description, and a roster of members.
- **Skill** — a named, catalogable capability (e.g. "Python", "Public speaking").
  Belongs to a **Category**/domain (e.g. "Backend", "Soft skills").
- **Proficiency** — the core measurement: links a `User` to a `Skill` with a
  `level` (e.g. 1–5), optional `evidence` text, an `updated_at` timestamp, and
  optionally the `User` who recorded it (self-reported vs peer).
- **TeamMembership** — join table for `User` ↔ `Team` with an optional `role`
  within that team.

## Suggested relationships

```
Team ──< TeamMembership >── User ──< Proficiency >── Skill
                                                  │
                                                  └──> Category
```

## Deliberately deferred

- CSV import/export
- Skill-gap reporting / heatmaps
- Multi-tenancy beyond a single org
- Audit trail / change history
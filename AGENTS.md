# AGENTS.md

Team skill-management web app (hackathon). Employees manage their own skills and
certificates; team managers curate their teams; leadership owns org structure via
projects that spawn teams.

## Stack & environment

- Django 6.1.1, Python 3.14.6, SQLite. Windows host; project under WSL.
- Use the project venv: `.venv\Scripts\python.exe` (via powershell.exe), not `python3`.
- Remote: `github.com/Chawiry/MNHackathon2026`, branch `main`.
- Push only works with the Windows git binary:
  `"/mnt/c/Program Files/Git/cmd/git.exe" -C 'C:\Users\jedel\Dev\Hackathon\MNHackathon2026' push origin main`
  (WSL git can commit/add but not push reliably with the mounted path).

## Commands

- Tests: `powershell.exe -NoProfile -Command "& {Set-Location 'C:\Users\jedel\Dev\Hackathon\MNHackathon2026'; .\.venv\Scripts\python.exe manage.py test}"`
- `manage.py check` after model/view changes.
- `makemigrations`/`migrate` for schema changes. Fixtures: `python manage.py loaddata starter_skills`.

## Apps & domain rules

- **accounts** — custom `User(AbstractUser)` with `tier` (`employee` / `team_manager` /
  `leadership`), `job_title`, `hire_date`. **No self-service signup**: leadership provisions
  accounts on `/users/` (any tier, re-tier, deactivate — cannot deactivate self); team managers
  create employee accounts and add them to a managed team in one step.
- **teams** — `Team`, `TeamMembership` (manager/member roles; a manager role *is* a membership
  role), `TeamSkillRequirement`. **Requirements are team-scoped**, unique per `team × skill`;
  new teams start with none. Managers edit requirements for teams they manage; leadership edits
  any. Team names unique per project.
- **skills** — `SkillCategory`, `Skill`, `SkillProficiency`, `Certificate`, `CertificateAward`.
  Approval workflow: one `SkillProficiency` row per `user × skill` with
  `pending`/`approved`/`rejected`. Manager recordings auto-approve; employee self-reports are
  pending until a manager (own team) or leadership approves. Only `approved` rows feed analytics.
  **Certificates back skills**: each `CertificateAward` carries `skill` + `level`; approval
  upserts that proficiency as approved (cert wins over a pending self-report; `reported_by`
  stays the owner so they can self-report again). Rejection never touches proficiencies.
  `expires_on` is a display-only "expired" flag.
- **projects** — `Project` = org units. Leadership creates a project (atomic: also spawns the
  project's first team + assigns the chosen team manager). A project holds one or more teams.

## Permissions (enforced by decorators in accounts/tiers.py)

- `require_tier(*tiers)` raises `PermissionDenied` (→ 403) for other tiers.
- `manages_team(user, team)`, `managed_team_ids(user)`, `team_member_ids(user)` power scoping:
  - `skills`: `me`/`self_assess`/`submit_certificate` (any logged-in); `record_skill`,
    `record_certificate`, `approvals`, approve/reject (managers + leadership; managers scoped
    to own teams, leadership org-wide); employee on approvals → 403.
  - `teams`: `team_list`, `add_member`, `change_role`, `remove_member` (managers only);
    `create_member`, requirement add/remove (managers + leadership).
  - `projects`: leadership only.
- Home redirects by tier: leadership → project_list, manager → team_list, employee → my_skills.

## Coverage

`teams/services.py::team_coverage(team)` resolves a team's own requirements against members'
approved proficiencies → `Met` / `Partial` / `Gap`. Empty/no-coverage → `Gap`.

## UI conventions

- Templates in `templates/` (Tailwind CDN, htmx, Alpine via CDN no CSP).
- Shared partial `templates/teams/_requirements.html` reused on teams + project detail pages.
- Approval actions redirect to the shared `/skills/approvals/` page.
- Validate `next` redirects against open-redirects (`teams/views.py::_safe_return`).
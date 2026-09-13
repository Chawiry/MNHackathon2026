# MNHackathon2026

Team skill management platform.

## Stack

- **Python 3.14 / Django 6.1** (server-rendered full-stack app)
- **SQLite** via Django ORM (swap to Postgres later)
- **Auth**: built-in Django auth (email/password), tier-based roles
- **Frontend**: Django templates + HTMX + Tailwind (CDN) — no Node.js build step

## Features

- **Skills & profiles** — 1–5 proficiency scale, manager/leadership approval workflows,
  certificates backing skills, and lightweight profile records (development activity, career
  experience, performance reviews) on each employee's My Skills page.
- **Team coverage & requirements** — per-team skill requirements with `current`/`promotion`
  (`next position`) purposes, org-wide candidate suggestions and one-click gig allocation.
- **Leadership analytics (`/insights/`)** — knowledge bottlenecks, skill depletion horizons,
  succession readiness, risk matrix (criticality + rarity), weighted organization readiness with
  trends, per-employee prioritized gaps with an IF→THEN recommendation rule set, plan readiness
  (manning × qualification × availability) with diagnosis cases, and a what-if sandbox
  (departure / adoption simulations). Every section can be scoped to one department.
- **Privacy-by-design** — aggregates over groups smaller than 5 are coarsened to bands and names
  are masked above the team-lead tier.
- **Cascade & feedback** — board → c-suite → department → team plan cascade with deterministic
  AI drafts, human approval, and upward team feedback that rolls up into leadership risk flags.
- **Projects** — leadership-defined projects that spawn teams with managers.
- **Demo dataset** — a deterministic seeded organization for walkthroughs.

## Apps

`accounts`, `teams`, `skills`, `projects`, `profiles`, `insights`, `core`.
See `docs/DATA_MODEL.md` for the full domain model.

## Setup (Windows)

The `.venv` in the repo root is a Windows virtualenv (created from `py`). From
PowerShell/cmd in this folder:

```sh
.venv\Scripts\python.exe manage.py migrate      # create SQLite schema first time
.venv\Scripts\python.exe manage.py runserver    # http://localhost:8000
.venv\Scripts\python.exe manage.py createsuperuser
```

Admin panel: http://localhost:8000/admin/

## Demo dataset

`seed_demo` flushes the database and builds the full deterministic demo
organization (53 users, 5 departments, 9 teams, 217 approved proficiencies,
56 skill requirements incl. 5 promotion/next-position, 33 skill-graph edges,
200 criticality assessments, future-demand projections, readiness snapshots,
and profile entries):

```sh
.venv\Scripts\python.exe manage.py seed_demo
```

All seeded accounts use the password `Testpass123!`. Demo logins:

| username        | tier        | notes                              |
|-----------------|-------------|------------------------------------|
| `alex.rivera`   | leadership  | org-wide analytics                 |
| `sam.lee`       | team manager| manages Platform Engineering       |
| `jordan.mendez` | employee    | My Skills / self-assessment        |

Caution: seeding flushes the DB, which removes any superuser. Recreate one with
`createsuperuser` after seeding if you need the admin panel.

To rebuild the venv from scratch: `py -m venv .venv` then
`.venv\Scripts\python.exe -m pip install -e .`.

## Tests

```sh
.venv\Scripts\python.exe manage.py test
```

The full suite covers seed invariants + idempotence, succession coverage math,
readiness scoring, gap priority ordering, all five recommendation rules,
plan-readiness diagnosis cases, what-if simulations, anonymization rules, the
cascade approval flow, department scoping, and profile-entry views.

## Project layout

```
config/            # Django project settings, urls
core/              # home + shared app (seed command, test utils)
accounts/          # custom User + tiers
teams/             # departments, teams, memberships, skill requirements
skills/            # taxonomy, proficiencies, certificates, criticality/demand
projects/          # project -> team spawning + coverage
profiles/          # development activities, experience, performance reviews
insights/          # leadership analytics (services + cascade models)
templates/         # base + registration templates
static/            # project-level static assets
docs/DATA_MODEL.md # agreed domain model driving future features
```

## Dev environment notes

- Repo lives on the Windows filesystem (`C:\Users\jedel\Dev\...`); develop and
  run it from Windows. Git is available natively inside WSL via a user-space
  install (`~/.local/opt/gitwsl/usr/bin/git`, on PATH from `~/.bashrc`).
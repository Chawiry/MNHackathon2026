# MNHackathon2026

Team skill management platform.

## Stack

- **Python 3.14 / Django 6.1** (server-rendered full-stack app)
- **SQLite** via Django ORM (swap to Postgres later)
- **Auth**: built-in Django auth (email/password), groups for roles
- **Frontend**: Django templates + HTMX + Tailwind (CDN) — no Node.js build step

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
organization (5 departments, 9 teams, 50 employees, 20 skills + skill-graph
edges, requirements, criticality assessments, future-demand projections, and
readiness snapshots):

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

## Project layout

```
config/           # Django project settings, urls
core/             # home + shared app (auth-required landing)
templates/        # base + registration templates
static/           # project-level static assets
docs/DATA_MODEL.md # agreed domain model driving future features
```

## Dev environment notes

- Repo lives on the Windows filesystem (`C:\Users\jedel\Dev\...`); develop and
  run it from Windows. Git is available natively inside WSL via a user-space
  install (`~/.local/opt/gitwsl/usr/bin/git`, on PATH from `~/.bashrc`).
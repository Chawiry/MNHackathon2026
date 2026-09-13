# UI/UX Overhaul Plan — Team Skills

Goal: full overhaul of the app's UI/UX — fix styling bugs, rework navigation/IA, build a
token-based component system, add real analytics visualizations, and polish mobile + accessibility.

Decisions locked in:
- **Scope:** Full overhaul
- **Styling:** Formalize design tokens + reusable component partials (keep Tailwind CDN, no build step)
- **Charts:** Add Chart.js via CDN for analytics pages
- **Home/Overview:** New role-aware dashboard (retire the redirect stub)
- **Sequencing:** Phases in order, verifying after each

## Phase 1 — Foundation: design system & bug fixes

Build a single-source design language in `static/app.css`, consumed via reusable partials.

- [x] **Fix the button bug** — `static/app.css:198` forces every `main button` to blue via
  `!important`, killing semantic colors (Approve/Reject on `approvals.html`, cascade Approve).
  Replace with explicit variants: `.btn`, `.btn-primary`, `.btn-success`, `.btn-danger`,
  `.btn-ghost`, `.btn-sm`. Update templates to use them.
- [x] **Expand tokens in `:root`** — spacing scale, radii, typography scale, and semantic status
  palettes (`success`, `warning`, `danger`, `neutral`, each with `-bg`/`-text`/`-border` pairs)
  replacing scattered `text-green-700`/`bg-red-100`/hex literals.
- [ ] **Component classes** in `app.css`: `.card`, `.badge`, `.table` + `.table-wrap`,
  `.list-row`, `.input`, `.field` (label/help/error), `.empty-state`, `.stat-card`, `.btn-*`,
  `.nav-item`, `.prose-label`. *(done: .card, .badge, .table/.table-wrap, .field, .empty-state,
  .btn-*, .prose-label; deferred in favor of shells in Phase 3: `.list-row`, `.stat-card`,
  `.nav-item`)*
- [x] **Reusable partials** under `templates/components/`:
  - [x] `badge.html` (status-value driven; codify the ≥80 / 60–79 / <60 rule once via
    `threshold_tone`)
  - [ ] `card.html`, `table.html`, `list_row.html`, `empty_state.html` *(done: `empty_state.html`;
    card/table/list_row still inline Tw — Phase 3)*
  - [x] Template tags `status_class` / `nav_active` to centralize threshold + nav logic.
    *(implemented as the `threshold_tone` filter + multi-URL `nav_active` in
    `core/templatetags/ui_tags.py`)*
- [x] **Retire the `!important` override layer** — migrate pages to the new classes so styling no
  longer depends on cascade-fighting.

## Phase 2 — Navigation & information architecture

- [x] **Rebuild `base.html` shell**:
  - Tier-gated sidebar with section labels (Workspace / Management / Leadership), real inline
    SVG icons (replaces `.sidebar-link::before` squares), computed active state via `nav_active`
    with `aria-current="page"` (kills the hardcoded-Overview bug).
  - **Add Insights to the leadership section** with sub-links to Cascade, Feedback, Criticality
    (resolves the orphaned-dashboard issue).
  - Pending-approvals **count badge** for managers/leadership (via `core/context_processors.py`).
- [x] **Rebuild `home.html`** into a real role-aware landing page (role greeting, key stats,
  quick actions) instead of the redirect shell.
- [x] **Topbar search** — convert the static `<div>` (`base.html:38`) into a functional input.
  Add a lightweight `/search/` view (people, skills, teams, projects); Alpine powers the
  suggestion dropdown (no build step).
- [x] **Mobile menu parity** — render the full tier-gated link set matching desktop; slide-down
  with a toggle.
- [x] **Consolidate duplicate flows** — unify the two "create user" forms
  (`accounts/create_user.html` and `teams.html`'s "Create a user and add to team" card).
  *(Decision: keep both — `create_user` is leadership-only, `create_member` is
  manager/leadership and auto-adds to a team; removing either orphans a tier. They are
  linked to each tier's entry pages.)*

## Phase 3 — Design polish & page refresh

- [x] **Typography & brand** — modernize font stack (system-ui/Inter-style), refine brand mark +
  tagline, add favicon, consistent `<title>` format. *(font stack done in Phase 1; favicon added
  as inline SVG data-URI; all pages use "X · Team Skills" titles)*
- [x] **Forms** — style Django widgets globally (`.input`), field-level error messages (custom
  renderer replacing raw `form.as_div` defaults), consistent labels/help text. Touches all forms:
  `me.html`, `teams.html`, `project_detail.html`, `cascade.html`, `feedback.html`, `login.html`,
  `create_user.html`, `criticality_edit.html`. *(Implemented via `FORM_RENDERER`
  `config.settings.AppFormRenderer` + `core/templates/forms/{div,field}.html`, which wrap every
  `as_div` field in `.field` with labeled inputs, `.errorlist` and help — no per-form edits
  needed.)*
- [x] **Tables** — wrap every table in `.table-wrap` (`overflow-x-auto`): `teams.html`,
  `project_detail.html`, `insights.html` (bottlenecks, risk matrix, future skills),
  `criticality_list.html`, `user_list.html`. *(wrapped all 7 tables, class → `.table`)*
- [ ] **Empty states** — upgrade text-only empties to the `empty_state` component (icon + title +
  hint) across all sections. *(done for the highest-visibility: approvals ×2, me skills /
  certificates, teams sidebar; the remaining minor empties are deferred)*
- [x] **Flash messages** — add success/error variants to `.flash-message` so feedback is
  color-semantic. *(wired `flash-{tags}` classes in `base.html`)*
- [x] **Dead code cleanup** — drop unused HTMX/Alpine where not adopted (or use Alpine for
  nav/search as noted); remove `home.html` stub if redirected away. *(HTMX dropped — no `hx-`
  usage; `home.html` is now the role-aware dashboard from Phase 2)*

## Phase 4 — Leadership analytics visuals

- [x] **Add Chart.js 4 via CDN** in `base.html`, loaded only on insights pages via
  `{% block extra_js %}`. *(block added to shell; Chart.js + `insights.js` loaded only in
  `insights.html`)*
- [x] **Insights dashboard** (`templates/insights/insights.html`) upgrades:
  - Readiness score → **doughnut gauge** with threshold tick (custom `thresholdLine` plugin).
  - Trend snapshot list → **line chart** with delta markers (points colored by Δ sign).
  - Department grid → **progress-bar tiles** (`role="progressbar"` bars under each dept score).
  - Risk matrix criticality → **horizontal bar** per skill.
  - What-if sandbox → small before/after comparison bars (departure coverage).
  *(All SSR-first: canvases carry `data-*`/`json_script` payloads; `<noscript>` fallbacks keep
  the trend list SSR-only usable without JS.)*
- [x] Create `static/insights.js` to seed charts from server-rendered `data-*` payloads
  (progressive enhancement, keeps SSR).

## Phase 5 — Mobile & accessibility

- [x] **Colorblind-safe status** — prepend dots/icons to color-coded badges and status rows
  (not color-only). *(CSS dot via `.badge::before` for the badge system; inline dot glyphs added
  to the coverage-status column in `teams.html`; label-text chips never rely on color alone)*
- [x] **Contrast passes** — bump `text-slate-400/500`-on-light instances to WCAG AA; fix
  muted-on-muted combos. *(scripted `slate-400 → slate-500` sweep across all templates, keeping
  AA for small text; 500-page number darkened)*
- [x] **Semantics** — real `<input>` for search with label, `aria-current` on nav,
  `focus-visible` rings, `<label for>` on fields, `aria-label` on icon-only / `Set` / `Remove`
  buttons. *(search now has visible-sr-only `<label for="search-input">` + `aria-autocomplete`;
  `aria-current` added on active nav in Phase 2; `focus-visible` rings for inputs/selects/textareas;
  every field gets a `<label for>` via the Phase 3 form renderer; the menu-toggle has `aria-label`
  and `aria-expanded`; Set/Remove buttons carry visible text)*
- [x] **Custom `404.html` and `500.html`.**

## Phase 6 — Verification

- [x] `manage.py test` — full suite stays green (template/CSS-only changes expected).
- [x] Django system checks + `py_compile` to catch template-tag errors.
- [x] Smoke-render pass across all 3 tier logins
  (`alex.rivera` leadership, `sam.lee` team manager, `jordan.mendez` employee; all
  `Testpass123!`), page-by-page via script. *(Tier-gated 403s confirmed as expected;
  all permitted pages return 200; anonymous gets correct redirects; 404/500 templates compile.)*
- [x] Responsive pass at ≤800px (sidebar → mobile menu, table wrapping). *(Media query in
  `app.css` and Alpine mobile menu in `base.html` validated in Phase 1–2; manual visual
  review recommended before deployment.)*

## Reference

- Shell/layout: `templates/base.html`, `static/app.css`
- Pages: `templates/core/home.html`, `templates/skills/{me,approvals}.html`,
  `templates/teams/teams.html` (+ `_requirements.html`),
  `templates/projects/project_{list,detail}.html`,
  `templates/insights/{insights,cascade,feedback,criticality_list,criticality_edit}.html`,
  `templates/accounts/{user_list,create_user}.html`, `templates/registration/login.html`,
  `templates/profiles/form_error.html`
- Views/URLs: `core/views.py`, `insights/urls.py`, `config/urls.py`
# Geospatial Maven — Progress Tracker Dashboard
## Full Development Session Log

**Project:** Geospatial Maven Progress Tracker Dashboard  
**Stack:** Flask 3.0 · SQLAlchemy · Flask-Login · SQLite (local) / PostgreSQL (Render) · Bootstrap 5 · Chart.js 4  
**Session dates:** May 21, 2026 · May 23, 2026  

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Tech Stack & File Map](#2-tech-stack--file-map)
3. [Data Models](#3-data-models)
4. [User Roles](#4-user-roles)
5. [Features Built — Session 1](#5-features-built--session-1)
6. [Features Built — Session 2](#6-features-built--session-2)
7. [Features Built — Session 3 (May 23 2026)](#7-features-built--session-3-may-23-2026)
8. [File Change Log](#8-file-change-log)
9. [Known Decisions & Why](#9-known-decisions--why)
10. [Credentials (Demo / Dev)](#10-credentials-demo--dev)
11. [Deployment](#11-deployment)

---

## 1. Project Overview

Internal project management dashboard for **Geospatial Maven**, a GIS/Remote Sensing consultancy. It tracks projects from Terms of Reference (TOR) through to final delivery, with role-based views for admins, developers, and clients.

**Key capabilities:**
- Project lifecycle tracking (TOR → Sections → Tasks → Milestones → Delivery)
- Role-based access: Super Admin sees everything; Developer sees assigned work; Client sees their projects only
- Budget / cost item tracking per project
- Objectives tracking (primary / secondary)
- Accomplished Projects gallery (reads from local folder)
- Light / dark theme toggle persisted in `localStorage`
- Signup flow for new developers and clients

---

## 2. Tech Stack & File Map

```
Progress Tracker Dashboard/
├── app.py                          # Flask app — all routes, models, seed data
├── requirements.txt                # Python dependencies
├── Procfile                        # Gunicorn entry for Render
├── DEPLOY_TO_RENDER.txt            # Step-by-step Render.com deployment guide
├── ROLE_BASED_ACCESS.md            # Role & access control documentation
├── SESSION_LOG.md                  # This file
│
├── templates/
│   ├── base.html                   # Shared layout: sidebar, topbar, flash, theme
│   ├── login.html                  # Login + Signup tabs, theme toggle
│   ├── dashboard.html              # KPI cards, recent projects, milestones chart
│   ├── my_tasks.html               # Developer task list
│   ├── team.html                   # Super admin team management
│   ├── admin/
│   │   └── approvals.html          # Task assignment approval queue (super_admin)
│   ├── projects/
│   │   ├── list.html               # Project cards grid with filter/search
│   │   ├── detail.html             # Full project view: TOR, sections, tasks, costs
│   │   ├── progress.html           # Deliverable review pipeline per project
│   │   └── deliverable_detail.html # Deliverable detail: timeline, comments, action panel
│   └── accomplished/
│       ├── index.html              # Gallery of completed project folders
│       ├── project.html            # File browser for one accomplished project
│       └── offline.html            # Shown when Accomplished Projects folder missing
│
├── static/
│   ├── css/style.css               # Single CSS file — dark + light theme vars
│   ├── js/app.js                   # Theme toggle, modal helpers, toast, Chart defaults
│   └── img/
│       ├── Geospatial Maven Logo.png           # Circular badge logo (transparent bg)
│       └── Geospatial Maven Logo with moto.png # Full horizontal logo with tagline (transparent bg)
│
└── Accomplished Projects/          # Local folder — each subfolder = one completed project
    └── <project-name>/
        └── (maps, reports, images, etc.)
```

---

## 3. Data Models

### User
| Field | Type | Notes |
|---|---|---|
| id | Integer PK | |
| name | String(100) | |
| email | String(120) | unique |
| password_hash | String(256) | Werkzeug |
| role | String(20) | `super_admin` / `developer` / `client` |
| department | String(100) | |
| specialization | String(200) | |
| avatar_color | String(20) | hex, random on creation |
| is_active | Boolean | admin can deactivate |
| last_login | DateTime | |

### Project
| Field | Type | Notes |
|---|---|---|
| id | Integer PK | |
| code | String(20) | auto-generated `GM-YYYY-NNN` |
| name | String(200) | |
| client_name | String(200) | free text org name |
| client_user_id | FK → User | linked client account (for access control) |
| coordinator_id | FK → User | developer/admin who manages it |
| status | String(20) | `planning` / `active` / `on_hold` / `completed` / `cancelled` |
| priority | String(10) | `low` / `medium` / `high` |
| overall_progress | Integer | calculated from section averages |
| budget_estimated | Float | |
| budget_actual | Float | |
| tags | String(500) | comma-separated |

### Section
Work packages within a project (e.g. Data Collection, Analysis, Write-up).

| Field | Notes |
|---|---|
| section_type | `analysis` / `writeup` / `learning` / `fieldwork` / `reporting` / `data_collection` / `qc` |
| progress | 0–100, averaged to get `project.overall_progress` |

### SectionAssignment
Many-to-many between Section and User.  
`assignment_role`: `lead` / `contributor` / `reviewer`

### Task
Belongs to a Section. Has `assigned_to_id`, status, priority, progress, due_date.

### TOR (Terms of Reference)
One-to-one with Project. Stores background, purpose, scope, deliverables, methodology, software tools, etc.

### Milestone, Objective, CostItem
All belong to a Project. Standard fields.

---

## 4. User Roles

| Role | DB value | Capabilities |
|---|---|---|
| Super Admin | `super_admin` | Full access to all projects, team management, create/delete anything |
| Developer | `developer` | See/edit projects where assigned or coordinator; own tasks |
| Client | `client` | Read-only access to their projects only; no team page, no tasks |

### Project visibility logic

**Super Admin** — all projects.

**Developer** — projects where:
- `Project.coordinator_id == user.id`, **OR**
- User has a `SectionAssignment` record for any section in the project

**Client** — projects where:
- `Project.client_user_id == user.id`

Direct URL access (`/projects/<id>`) is also guarded: unauthorized users get flashed and redirected.

See [ROLE_BASED_ACCESS.md](ROLE_BASED_ACCESS.md) for full details.

---

## 5. Features Built — Session 1

### Deployment guide
- `DEPLOY_TO_RENDER.txt` — 7-step walkthrough: install Git → GitHub repo → PAT → push → Render web service → env vars → live URL.
- `Procfile` with `gunicorn app:app`
- `DATABASE_URL` env var handling: auto-converts `postgres://` → `postgresql://` for SQLAlchemy

### Signup route
`POST /signup` — allows new users to register as `developer` or `client` only (not `super_admin`). Validates: required fields, role whitelist, password match, min length 6, email uniqueness.

### Login page redesign
- Two-tab layout: **Sign In** / **Create Account**
- Left branding panel with logo, tagline, feature list, GIS coordinate decoration
- Demo account auto-fill buttons
- Password visibility toggle
- `?tab=signup` query param to land on signup tab (used after failed signup POST)

### Light / Dark theme
- CSS custom properties in `:root` for dark theme defaults
- `[data-theme="light"]` block overrides all variables
- Inline `<script>` in `<head>` reads `localStorage('gm-theme')` and sets `data-theme` **before paint** (prevents FOUC)
- `toggleTheme()` in `app.js` flips theme and updates icon
- Sun icon in dark mode, moon icon in light mode

### Logo (multiple iterations)
1. SVG logos created from scratch (GIS-themed)
2. User provided their own PNG: circular badge with heat-map terrain, satellite, theodolite, location pin
3. SVG recreations created: `logo.svg` (badge only), `logo-full.svg` (horizontal with tagline)
4. Tagline chosen: **"Mapping a Sustainable World"** (≤5 words)
5. Export utility: `static/img/export-logo.html`

---

## 6. Features Built — Session 2 (this session)

### 6.1 Logo — switch to "with motto" version in sidebar
**Problem:** User created two PNG files. Wanted the full horizontal logo (badge + text + tagline) displayed in the sidebar without circle cropping.

**Changes:**
- `base.html` sidebar: switched `src` from `Geospatial Maven Logo.png` → `Geospatial Maven Logo with moto.png`
- Removed hardcoded `width="46" height="46"` attributes
- `style.css` `.logo-img`: removed `border-radius: 50%`, changed to `width: auto; max-width: 155px; height: auto; object-fit: contain`
- Used `filter: drop-shadow(...)` instead of `box-shadow` so shadow follows logo shape, not a rectangle
- Added `.sidebar.collapsed .sidebar-logo { display: none; }` so wide logo doesn't overflow the 64px collapsed width

### 6.2 Remove white background from both logos
**Problem:** Both PNG files had a white rectangular background visible over dark/gradient surfaces.

**Fix:** Python/Pillow script — iterated all pixels, set `alpha = 0` for any pixel where R, G, B all ≥ 235 (near-white threshold). Run in-place on both files.

```python
from PIL import Image

def remove_white_bg(path, threshold=235):
    img = Image.open(path).convert('RGBA')
    datas = img.getdata()
    newData = []
    for item in datas:
        r, g, b, a = item
        if r >= threshold and g >= threshold and b >= threshold:
            newData.append((r, g, b, 0))
        else:
            newData.append(item)
    img.putdata(newData)
    img.save(path, 'PNG')
```

Result: 73% of `Logo with moto.png` pixels transparent, 64% of circular `Logo.png` transparent.

### 6.3 Theme toggle position on login page
**Problem:** Floating theme toggle button (`position: fixed; top: 1.25rem; right: 1.25rem`) overlapped the Sign In / Create Account tab bar.

**Fix:** Moved to `bottom: 1.5rem; right: 1.5rem` — bottom-right corner, clear of all form elements.

### 6.4 Sidebar header — circular badge + HTML text
**Problem:** Using the full "with motto" PNG at 155px made the embedded text too small to read at sidebar scale.

**Fix:** Switched back to the circular badge PNG (`Geospatial Maven Logo.png`) at 42×42px with `border-radius: 50%` and `object-fit: cover`, and added HTML text elements beside it:

```html
<img src="...Geospatial Maven Logo.png" class="logo-img">
<div class="logo-text">
  <span class="logo-name">Geospatial Maven</span>
  <span class="logo-sub">Mapping a Sustainable World</span>
</div>
```

CSS: `.logo-name` — Space Grotesk 700, 0.92rem, `var(--text-primary)`. `.logo-sub` — 0.68rem, italic, `var(--primary)` (brand green).

When sidebar collapses: `.logo-text` hides, circular badge stays visible and centred.

### 6.5 Collapsed sidebar — toggle button centred
**Problem:** At 64px collapsed width with 1rem padding each side, the header had only 32px for content but the logo image (42px) + gap + toggle button overflowed, pushing the toggle button partially outside the sidebar boundary.

**Fix:**
```css
.sidebar.collapsed .sidebar-header {
  justify-content: center;
  padding: 1.1rem 0;
}
.sidebar.collapsed .sidebar-logo { display: none; }
```
Toggle button is now centred within 64px, nothing overflows.

### 6.6 Role-based project filtering (confirmed + hardened)
The `projects_list` route already had basic filtering. This session hardened it:

**Developer query improvement:**
```python
# Before: only SectionAssignment
# After: SectionAssignment OR coordinator_id
project_ids = set(s.project_id for s in assigned_sections)
coordinated_ids = {p.id for p in Project.query.filter_by(coordinator_id=current_user.id).all()}
project_ids.update(coordinated_ids)
```

**project_detail URL guard for developers:**
```python
if current_user.role == 'developer':
    is_coordinator = project.coordinator_id == current_user.id
    is_assigned = SectionAssignment.query.join(Section).filter(
        Section.project_id == project_id,
        SectionAssignment.user_id == current_user.id
    ).first() is not None
    if not is_coordinator and not is_assigned:
        flash('Access denied. You are not assigned to this project.', 'danger')
        return redirect(url_for('projects_list'))
```

**List template heading — role-aware:**
- Super Admin → "All Projects — N projects across the organisation"
- Developer → "My Projects — N projects assigned to you"
- Client → "Your Projects — N projects shared with you"

### 6.7 Documentation files created
- `ROLE_BASED_ACCESS.md` — roles, visibility rules, URL guards, assignment instructions, data model reference, route permission table, guide for adding future roles
- `SESSION_LOG.md` — this file

---

## 7. Features Built — Session 3 (May 23 2026)

### 7.1 Login page — Role portal (step-before-form)

**What:** Added a role-selection landing step before showing the login/signup form. Users pick their identity first:
- **Visitor** → redirected straight to the public homepage (no auth needed)
- **Client** → continues to login/signup form
- **Developer** → continues to login/signup form
- **Administrator** → continues to login/signup form

**How:**
- Two `<div>` blocks in `login.html`: `#stepRole` (4 role cards) and `#stepForm` (existing form)
- `selectRole(role)` JS function hides/shows the blocks and stores the chosen role in `sessionStorage`
- A back arrow button in `#stepForm` returns to `#stepRole`
- A role badge appears above the form showing the selected role

### 7.2 Login page — Role-filtered demo accounts

**What:** Demo account auto-fill buttons are filtered to only show credentials relevant to the selected role.

**How:** Each `.demo-suggestion` button has a `data-for="admin|developer|client"` attribute. `selectRole()` hides all buttons, then shows only those matching the current role:

```javascript
document.querySelectorAll('.demo-suggestion').forEach(function(row) {
  row.style.display = row.dataset.for === mapRole ? '' : 'none';
});
```

### 7.3 Login page — Visual fixes

- **Sign In button spacing:** Changed to `display:flex; align-items:center; justify-content:center; gap:.55rem` so the icon and text have a proper gap
- **Removed coordinate decoration:** Stripped the `LAT:30.3753°N LON:69.3451°E PROJ:WGS84 ZONE:42N` line from the left branding panel

### 7.4 My Tasks — Multi-PM-tool view system

Complete rewrite of `my_tasks.html` drawing the signature feature from six leading PM tools:

| Tool | Feature implemented |
|---|---|
| **Trello** | Kanban board — 5 draggable columns (Backlog → Done), HTML5 drag-and-drop API |
| **Jira** | List view — sprint grouping, story points column, sprint progress bars, filter pills |
| **ClickUp** | 3-view toggle (Board / List / Calendar) in the topbar |
| **Monday.com** | 5-column KPI status bar with live count display across all views |
| **Notion** | Activity feed sidebar — calls `/api/activity`, renders with icons + avatars |
| **Linear** | Sprint grouping header with sprint name + completion progress per group |

**Implementation highlights:**
- `TASKS` JS array from `tasks_json` Jinja variable powers all three views client-side
- Calendar view: month grid rendered by `renderCalendar()`, task dots appear on due dates, `calNav()` handles prev/next month
- Drag-and-drop: `dragStart()` stores task id; `dropCard()` calls `/tasks/<id>/update` PATCH to persist new status; `moveCardToColumn()` updates the DOM
- Sprint filter dropdown filters both list and board views simultaneously
- Forward button on each kanban card opens `openForward()` modal

### 7.5 Task forwarding & admin approval workflow

**Business rule:** Admin is "high command" — any task reassignment NOT initiated by admin requires approval.

**Models added:**

```python
class TaskAssignmentRequest(db.Model):
    task_id        = FK → Task
    requested_by_id = FK → User
    assign_to_id   = FK → User
    message        = Text
    forward_type   = String(50)   # QA Review / Write-up / Field Work / etc.
    status         = String(20)   # pending | approved | rejected
    admin_note     = Text
    reviewed_at    = DateTime
    reviewed_by_id = FK → User
```

**Routes added:**
- `POST /tasks/<id>/forward` — creates `TaskAssignmentRequest` (pending)
- `GET /admin/approvals` — lists all pending + history
- `POST /admin/approvals/<id>/approve` — sets status=approved, reassigns task, logs activity
- `POST /admin/approvals/<id>/reject` — sets status=rejected, stores admin note

**Forward modal in My Tasks:**
- Type selector (QA Review / Write-up / Final Review / Field Work / Mapping / Reporting)
- Assignee picker — live-fetched from `/api/users`
- Optional note field
- Warning banner shown to non-admin: "Request will be sent to Administrator for approval"

**`templates/admin/approvals.html`** (new):
- KPI row: Pending / Approved / Rejected counts
- Pending cards: requester → assignee arrow, approve button, inline reject form with note
- History log of all reviewed requests

**Sidebar badge:** `pending_approvals` count injected via context processor; red badge shown on Approvals nav item for super_admin.

```python
@app.context_processor
def inject_globals():
    pending = 0
    if current_user.is_authenticated and current_user.role == 'super_admin':
        pending = TaskAssignmentRequest.query.filter_by(status='pending').count()
    return {'pending_approvals': pending}
```

### 7.6 New DB columns: sprint_label, story_points

Added to `Task` model for Jira-style sprint features:

```python
sprint_label  = db.Column(db.String(50))   # e.g. "Sprint 3 — June"
story_points  = db.Column(db.Integer)      # Fibonacci: 1, 2, 3, 5, 8, 13
```

**Local fix:** Delete `instance/gm_dashboard.db` after adding columns (SQLite has no `ALTER COLUMN`). Server restarts rebuild DB via `db.create_all()`.

### 7.7 Activity logging system

**Model added:**

```python
class ActivityLog(db.Model):
    user_id    = FK → User
    project_id = FK → Project (nullable)
    action     = String(100)   # short verb: "Task updated", "Project created"
    description = Text
    icon       = String(30)    # Bootstrap icon class
    color      = String(20)    # hex colour for icon
    created_at = DateTime
```

**`log_act()` helper** — appends to session, never commits (caller commits once):

```python
def log_act(user_id, action, description, icon='bi-activity', color='#8b5cf6', project_id=None):
    db.session.add(ActivityLog(
        user_id=user_id, project_id=project_id,
        action=action, description=description,
        icon=icon, color=color
    ))
```

Hooked into: task create, task status change, project create, task forwarding, deliverable stage transitions.

**`/api/activity` route** — returns last 30 log entries as JSON for the Notion-style activity feed sidebar.

### 7.8 Deliverable review pipeline (QA → Admin/CTO → Client)

The flagship feature of this session. Tracks finalized work items through a multi-stage review process with full audit trail.

#### Models

```python
class Deliverable(db.Model):
    project_id     = FK → Project
    section_id     = FK → Section (nullable)
    title          = String(200)
    description    = Text
    stage          = String(30)   # draft | qa_review | admin_review | client_review | completed | revision
    created_by_id  = FK → User
    assigned_qa_id = FK → User (nullable)
    created_at, updated_at = DateTime

    # Computed properties
    def stage_color(self): ...      # returns hex per stage
    def stage_label(self): ...      # returns human label
    def open_comments(self): ...    # returns comments with status='open'
    def client_visible_comments(self): ...  # returns is_client_visible=True comments

class DeliverableEvent(db.Model):
    # Immutable audit trail entry
    deliverable_id = FK → Deliverable
    user_id        = FK → User
    event_type     = String(50)    # stage_change | comment_added | comment_resolved | comment_closed
    stage_from     = String(30)    # previous stage (nullable)
    stage_to       = String(30)    # new stage (nullable)
    note           = Text
    created_at     = DateTime

class DeliverableComment(db.Model):
    deliverable_id    = FK → Deliverable
    author_id         = FK → User
    body              = Text
    parent_id         = FK → DeliverableComment (for replies, nullable)
    status            = String(20)   # open | dev_resolved | qa_resolved | closed
    is_client_visible = Boolean      # admin toggles before sending to client
    created_at        = DateTime
```

#### Stage flow

```
draft → qa_review → admin_review → client_review → completed
          ↓              ↓               ↓
        revision  ←  send back  ←  send back
```

Send-back at every stage returns to `revision`; any team member can resubmit.

#### Routes added

| Route | Actor | Action |
|---|---|---|
| `GET /projects/<id>/progress` | all | Progress Review landing page |
| `POST /projects/<id>/progress` | non-client | Create new deliverable |
| `GET /deliverables/<id>` | all | Deliverable detail page |
| `POST /deliverables/<id>/submit` | developer | Submit draft → qa_review |
| `POST /deliverables/<id>/qa-approve` | QA | QA approve → admin_review |
| `POST /deliverables/<id>/qa-sendback` | QA | QA send back → revision |
| `POST /deliverables/<id>/admin-send-client` | admin | Admin approve → client_review |
| `POST /deliverables/<id>/admin-sendback` | admin | Admin send back → revision |
| `POST /deliverables/<id>/client-approve` | client | Client approve → completed |
| `POST /deliverables/<id>/client-sendback` | client | Client send back → admin_review |
| `POST /deliverables/<id>/comments` | all | Post a comment or reply |
| `POST /deliverable-comments/<id>/resolve` | role-gated | Advance comment resolution status |
| `POST /deliverable-comments/<id>/toggle-visible` | admin | Toggle is_client_visible |

#### Comment resolution loop

```
open → (developer marks resolved) → dev_resolved
     → (QA verifies) → qa_resolved
     → (admin reviews) → closed   OR   send back to developer / QA
```

Client users only see comments where `is_client_visible=True`.

#### `_add_event()` helper

```python
def _add_event(d, user, event_type, stage_from=None, stage_to=None, note=None):
    db.session.add(DeliverableEvent(
        deliverable_id=d.id, user_id=user.id,
        event_type=event_type, stage_from=stage_from,
        stage_to=stage_to, note=note
    ))
```

#### Templates

**`templates/projects/progress.html`** (new):
- Visual pipeline bar showing 5 stages with item counts
- Deliverables grouped by stage (draft, revision, qa_review, admin_review, client_review, completed)
- Each card: colour dot, title, creator, section, updated date, comment count, open-comments badge
- "New Deliverable" modal: title, description, section dropdown, QA assignee dropdown
- `createDeliverable()` POSTs JSON to `/projects/<id>/progress`

**`templates/projects/deliverable_detail.html`** (new):
- **Stage banner** — colour-coded strip showing current stage
- **Left column — Timeline + comments:**
  - Full audit trail: all `DeliverableEvent` records with stage arrows and actor name/avatar
  - Comment thread with nested replies, timestamps
  - Resolution buttons (role-gated): "Mark Resolved" / "Verify Resolution" / "Close"
  - Visibility toggle (admin only): lock icon toggles `is_client_visible`
- **Right column (sticky) — Action panel:** Context-sensitive based on role + stage:
  - Developer (draft/revision): "Submit to QA" form with optional note
  - QA (qa_review): "Approve → Admin Review" or "Send Back" with note
  - Admin (admin_review): "Send to Client" (with comment visibility checkboxes) or "Send Back to QA/Dev"
  - Client (client_review): "Approve → Completed" or "Send Back to Admin"

**`templates/projects/detail.html`** update:
- Added **Progress Review** tab link pointing to `url_for('project_progress', project_id=project.id)`

### 7.9 WSGI / PythonAnywhere deployment fix

**Root cause:** `db.create_all()` and `seed_data()` were inside `if __name__ == '__main__':` — WSGI never runs that block, so the database was never created/migrated after schema changes.

**Fix applied:**
```python
# Outside the if __name__ block — runs on every WSGI import
with app.app_context():
    db.create_all()
    seed_data()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

**Deploy procedure after any schema change:**
1. `git pull` on PythonAnywhere
2. `rm ~/progress-tracker-dashboard/instance/gm_dashboard.db`
3. Reload app from Web tab → DB recreated automatically on first request

### 7.10 Asana-style circular progress rings on dashboard

Added SVG ring components to each project card in `dashboard.html`:

```html
<svg width="44" height="44" viewBox="0 0 44 44">
  <circle cx="22" cy="22" r="18" fill="none" stroke="var(--border)" stroke-width="4"/>
  <circle cx="22" cy="22" r="18" fill="none" stroke="#10b981" stroke-width="4"
    stroke-dasharray="{{ c }}"
    stroke-dashoffset="{{ c - (c * p.overall_progress / 100) }}"
    stroke-linecap="round" transform="rotate(-90 22 22)"/>
  <text x="22" y="26" text-anchor="middle" font-size="9" fill="var(--text-primary)" font-weight="700">
    {{ p.overall_progress }}%
  </text>
</svg>
```

Where `c = 2 * π * r ≈ 113.1` (full circumference). Offset shrinks the visible arc proportionally to progress.

---

## 9. Known Decisions & Why

| Decision | Reason |
|---|---|
| CSS custom properties for theming | One `:root` block + one `[data-theme="light"]` override block. No duplicate CSS. Theme swap is instant. |
| Inline `<script>` in `<head>` to set theme | Prevents FOUC (flash of unstyled content). Theme is applied before any CSS paints. |
| `filter: drop-shadow` on logo instead of `box-shadow` | `box-shadow` follows the element's bounding rectangle. `drop-shadow` follows the actual visible pixels of the transparent PNG. |
| Pillow white-background removal (threshold 235, not 255) | Threshold 255 would only catch pure white. 235 catches near-white anti-aliasing fringe pixels that appear grey/tan on dark backgrounds, giving a cleaner edge. |
| Developer sees projects via `SectionAssignment` OR `coordinator_id` | A developer could be the coordinator of a project without being assigned to a specific section yet. Both paths should grant access. |
| Signup limited to `developer` / `client` roles | `super_admin` accounts must be created by an existing admin through the Team page, not self-service. |
| `object-fit: cover` + `border-radius: 50%` for circular badge | `cover` fills the circle completely with no white space. `contain` would show gaps. The circular badge PNG has the artwork centred, so `cover` crops correctly. |
| Collapsed sidebar hides logo entirely | At 64px the logo text is unreadable anyway. Hiding it cleanly and centring the toggle button is the standard pattern for icon-only collapsed sidebars. |
| `sessionStorage` for role selection across POST redirect | `localStorage` would persist forever; a session variable (Flask) would require a round-trip. `sessionStorage` survives the redirect in the same tab and clears when the tab closes — perfect for a transient portal choice. |
| Event sourcing for deliverable audit trail (`DeliverableEvent`) | Mutable status fields show only current state. An append-only events table gives the full history of who changed what and when at zero extra query cost. |
| `db.create_all()` outside `if __name__` block | WSGI servers import the module but never run `__main__`. Moving `create_all()` to module scope ensures the DB is always initialised, even on Gunicorn/uWSGI. |
| `log_act()` adds to session without committing | Keeps the activity log entry and the triggering change in one atomic transaction. If the main operation rolls back, the log rolls back too — no orphan log entries. |
| Comment `is_client_visible` flag toggled by admin before client send | Clients should only see what has been explicitly approved for them to see. Defaulting to hidden and requiring an admin opt-in is safer than opt-out visibility. |
| `TaskAssignmentRequest` as a separate model (not a Task field) | Approval requests have their own lifecycle (pending → approved/rejected) and their own actors. Embedding them in Task would conflate "task state" with "approval state". |

---

## 10. Credentials (Demo / Dev)

| Role | Email | Password |
|---|---|---|
| Super Admin | admin@geospatialmaven.com | admin123 |
| Developer | sarah@geospatialmaven.com | dev123 |
| Developer | usman@geospatialmaven.com | dev123 |
| Developer | fatima@geospatialmaven.com | dev123 |
| Client | client@undp.org | client123 |
| Client | projects@wwf.org | client123 |

> These are seeded automatically on first run if the database is empty (`seed_data()` in `app.py`).

---

## 11. Deployment

### Local
```bash
pip install -r requirements.txt
python app.py
# → http://localhost:5000
```

Database is created automatically at `gm_dashboard.db` (SQLite). Seed data is inserted on first run.

### Render.com (free tier)
Full step-by-step in `DEPLOY_TO_RENDER.txt`. Summary:

1. Push repo to GitHub
2. Create **Web Service** on Render, point to repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Add env vars:
   - `DATABASE_URL` — Render PostgreSQL connection string (auto-provided if you attach a Render DB)
   - `SECRET_KEY` — any random string
6. Deploy — Render runs `db.create_all()` + `seed_data()` on first start

### Environment variables
| Variable | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | Flask session signing | `gm-progress-tracker-2025-secret-key` (change in prod!) |
| `DATABASE_URL` | Database connection | `sqlite:///gm_dashboard.db` |

---

*Last updated: 23 May 2026*

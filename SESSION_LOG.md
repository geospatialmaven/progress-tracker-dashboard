# Geospatial Maven — Progress Tracker Dashboard
## Full Development Session Log

**Project:** Geospatial Maven Progress Tracker Dashboard  
**Stack:** Flask 3.0 · SQLAlchemy · Flask-Login · SQLite (local) / PostgreSQL (Render) · Bootstrap 5 · Chart.js 4  
**Session dates:** May 21, 2026  

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Tech Stack & File Map](#2-tech-stack--file-map)
3. [Data Models](#3-data-models)
4. [User Roles](#4-user-roles)
5. [Features Built — Session 1](#5-features-built--session-1)
6. [Features Built — Session 2 (this session)](#6-features-built--session-2-this-session)
7. [File Change Log](#7-file-change-log)
8. [Known Decisions & Why](#8-known-decisions--why)
9. [Credentials (Demo / Dev)](#9-credentials-demo--dev)
10. [Deployment](#10-deployment)

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
│   ├── projects/
│   │   ├── list.html               # Project cards grid with filter/search
│   │   └── detail.html             # Full project view: TOR, sections, tasks, costs
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

## 7. File Change Log

| File | Changes |
|---|---|
| `app.py` | Signup route; dashboard role logic; `projects_list` developer filter (coordinator + assignment); `project_detail` developer URL guard |
| `templates/base.html` | `id="htmlRoot"` on `<html>`; theme init script; theme toggle button in topbar; sidebar logo switched to circular badge + HTML text |
| `templates/login.html` | Full rewrite: two-tab layout; theme toggle (repositioned to bottom-right); signup form; demo fill buttons |
| `templates/projects/list.html` | Page heading made role-aware |
| `static/css/style.css` | Light theme block; `.logo-img` styles (multiple iterations); `.theme-toggle-btn`; collapsed sidebar header centring; `.logo-name` / `.logo-sub` text styles |
| `static/js/app.js` | `toggleTheme()`, `_applyThemeIcon()`, `openModal()`, `closeModal()`, animated progress bars, KPI counter animation, Chart.js defaults, toast helper |
| `static/img/Geospatial Maven Logo.png` | White background removed (Pillow, threshold 235) |
| `static/img/Geospatial Maven Logo with moto.png` | White background removed (Pillow, threshold 235) |
| `static/img/logo.svg` | Created: SVG recreation of circular badge |
| `static/img/logo-full.svg` | Created: horizontal logo with tagline |
| `static/img/export-logo.html` | Created: browser-based PNG export utility |
| `DEPLOY_TO_RENDER.txt` | Created: Render.com deployment walkthrough |
| `ROLE_BASED_ACCESS.md` | Created: role & access documentation |
| `SESSION_LOG.md` | Created: this file |

---

## 8. Known Decisions & Why

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

---

## 9. Credentials (Demo / Dev)

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

## 10. Deployment

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

*Last updated: 21 May 2026*

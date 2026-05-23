# Role-Based Access Control — Geospatial Maven Dashboard

*Last updated: 23 May 2026*

---

## Roles

| Role | Value in DB | Who it is |
|---|---|---|
| Super Admin | `super_admin` | Internal admin / project manager — **high command**, all approvals flow through here |
| Developer | `developer` | GIS analysts, remote sensing specialists, writers |
| Client | `client` | External clients / stakeholders (e.g. UNDP, WWF) |

---

## Login Portal — Role Selection

Before reaching the login / signup form, all visitors pass through a **role selection portal**:

| Selection | Behaviour |
|---|---|
| Visitor | Redirected to public homepage — no auth required |
| Client | Shown login form; demo credentials filtered to client accounts only |
| Developer | Shown login form; demo credentials filtered to developer accounts only |
| Administrator | Shown login form; demo credentials filtered to admin accounts only |

The selected role is stored in `sessionStorage` and cleared when the browser tab closes.

---

## Projects — Visibility Rules

### Super Admin
- Sees **all projects** in the system.
- Can create, edit, and delete any project.

### Developer
A developer sees a project if **any** of the following is true:
1. They are the **coordinator** of the project (`Project.coordinator_id == user.id`)
2. They are **assigned to at least one section** via `SectionAssignment`

They do **not** see projects they have no involvement in.

### Client
- Sees only projects where `Project.client_user_id == user.id`.
- This field is set by the admin when creating or editing a project.
- Clients cannot create, edit, or delete projects.
- Clients cannot access the Team page or My Tasks.

---

## Project Detail — Direct URL Access Guards

Even if a user crafts a direct URL (`/projects/<id>`), access is blocked:

| Role | Guard condition |
|---|---|
| Client | `project.client_user_id != current_user.id` → redirect to Dashboard |
| Developer | Not coordinator **and** not assigned to any section → redirect to Projects list |
| Super Admin | No restriction |

---

## My Tasks — Role Access

| Feature | super_admin | developer | client |
|---|---|---|---|
| View tasks | Yes | Own tasks only | No (redirected to Dashboard) |
| Board / List / Calendar views | Yes | Yes | — |
| Drag card to new status | Yes | Yes (own tasks) | — |
| Forward task to another person | Yes (no approval needed) | Yes (requires admin approval) | — |
| View sprint / story points | Yes | Yes | — |
| Activity feed sidebar | Yes | Yes | — |

---

## Task Forwarding & Approval Workflow

**Rule:** Admin is high command. Any task reassignment **not initiated by admin** requires admin approval before it takes effect.

### Flow

```
Developer/Client requests forward
        ↓
TaskAssignmentRequest created  (status = pending)
        ↓
Admin sees badge on sidebar + /admin/approvals queue
        ↓
Admin approves → task reassigned + activity logged
Admin rejects  → requester notified, task unchanged
```

### Who can forward

| Actor | Can forward? | Approval needed? |
|---|---|---|
| Super Admin | Yes | No — takes effect immediately |
| Developer | Yes | Yes — goes to pending queue |
| Client | Yes | Yes — goes to pending queue |

### Forward types available
`QA Review` · `Write-up` · `Final Review` · `Field Work` · `Mapping` · `Reporting` · `Other`

### Admin Approvals page (`/admin/approvals`)
- Visible to `super_admin` only.
- Shows **Pending** count badge in the sidebar nav.
- Lists pending requests (requester → proposed assignee, forward type, note).
- Approve button: reassigns task, logs activity, marks request approved.
- Reject form: stores admin note, marks request rejected.
- History log of all reviewed requests.

---

## Deliverable Review Pipeline

Each project has a **Progress Review** section (`/projects/<id>/progress`) that tracks deliverables through a multi-stage review process.

### Stages

```
draft → qa_review → admin_review → client_review → completed
             ↓             ↓              ↓
           revision ← send back ← send back
```

| Stage | Colour | Meaning |
|---|---|---|
| `draft` | Grey `#6b7280` | Created, not yet submitted |
| `qa_review` | Blue `#3b82f6` | Under QA / internal review |
| `admin_review` | Indigo `#6366f1` | Under Admin / CTO review |
| `client_review` | Amber `#f59e0b` | Sent to client for sign-off |
| `completed` | Green `#10b981` | Approved and finalized |
| `revision` | Red `#ef4444` | Sent back — needs rework |

### Who can do what

| Action | Required role | Required stage |
|---|---|---|
| Create deliverable | non-client | — |
| Submit to QA | Developer (creator) | `draft` or `revision` |
| QA Approve → Admin | Developer with QA role, or admin | `qa_review` |
| QA Send back → Revision | Same | `qa_review` |
| Admin Approve → Client | super_admin | `admin_review` |
| Admin Send back → Revision | super_admin | `admin_review` |
| Client Approve → Completed | client | `client_review` |
| Client Send back → Admin | client | `client_review` |
| Post comment | All authenticated | Any stage |
| Mark comment dev-resolved | Developer (comment author) | Any |
| Mark comment qa-resolved | QA / admin | Any |
| Close comment | super_admin | Any |
| Toggle client visibility on comment | super_admin | Any |

### Comment resolution loop

```
open
 └─ developer clicks "Mark Resolved" → dev_resolved
      └─ QA clicks "Verify Resolution" → qa_resolved
           └─ Admin clicks "Close" → closed
                OR
           Admin sends back → comment reopens for rework
```

**Client visibility:** Clients only see comments where `is_client_visible = True`. Admin toggles this flag per comment before sending to client. Default is `False` (hidden from client).

### Audit trail

Every stage transition and comment action creates an immutable `DeliverableEvent` record:

| event_type | When |
|---|---|
| `stage_change` | Any pipeline transition |
| `comment_added` | New comment or reply posted |
| `comment_resolved` | Resolution status advanced |
| `comment_closed` | Comment fully closed |

The full audit trail is visible to all non-client users on the deliverable detail page. Clients see only client-facing events.

---

## How to Assign a Developer to a Project

1. Open the project → go to a section.
2. In the section form, select the developer in the **Assignees** field.
3. This creates a `SectionAssignment` record.
4. The developer now sees the project in their Projects list.

Alternatively, set the developer as **Project Coordinator** — they also gain access.

---

## How to Assign a Client to a Project

1. When creating a project (admin only), select the client from the **Client User** dropdown.
2. Or edit an existing project and set the **Client User** field.
3. Only registered users with `role = 'client'` appear in this dropdown.

---

## Data Model Reference

```
User
  id, name, email, role (super_admin | developer | client)

Project
  coordinator_id  → FK → User
  client_user_id  → FK → User

Section
  project_id → FK → Project

SectionAssignment
  section_id       → FK → Section
  user_id          → FK → User
  assignment_role  (lead | contributor | reviewer)

Task
  assigned_to_id   → FK → User
  sprint_label     String(50)    — e.g. "Sprint 3 — June"
  story_points     Integer       — Fibonacci: 1, 2, 3, 5, 8, 13

TaskAssignmentRequest
  task_id          → FK → Task
  requested_by_id  → FK → User
  assign_to_id     → FK → User
  forward_type     String(50)
  status           String(20)    — pending | approved | rejected
  admin_note       Text
  reviewed_by_id   → FK → User

Deliverable
  project_id       → FK → Project
  section_id       → FK → Section (nullable)
  stage            String(30)    — draft | qa_review | admin_review | client_review | completed | revision
  created_by_id    → FK → User
  assigned_qa_id   → FK → User (nullable)

DeliverableEvent
  deliverable_id   → FK → Deliverable
  user_id          → FK → User
  event_type       String(50)
  stage_from       String(30)
  stage_to         String(30)
  note             Text

DeliverableComment
  deliverable_id    → FK → Deliverable
  author_id         → FK → User
  parent_id         → FK → DeliverableComment (nullable — for replies)
  status            String(20)    — open | dev_resolved | qa_resolved | closed
  is_client_visible Boolean       — default False

ActivityLog
  user_id          → FK → User
  project_id       → FK → Project (nullable)
  action           String(100)
  description      Text
  icon             String(30)    — Bootstrap icon class
  color            String(20)    — hex
```

---

## Full Route Permission Table

| Route | super_admin | developer | client |
|---|---|---|---|
| `GET /` (dashboard) | Yes | Yes | Yes |
| `GET /projects` | All projects | Assigned + coordinated | Their projects only |
| `GET /projects/<id>` | Always | Only if assigned/coordinator | Only if client_user_id matches |
| `POST /projects` | Yes | Yes | No |
| `POST /projects/<id>/update` | Yes | Yes | No |
| `POST /projects/<id>/delete` | Yes | No | No |
| `GET /team` | Yes | No | No |
| `GET /my-tasks` | Yes | Yes | No |
| `POST /tasks/<id>/forward` | Yes | Yes | Yes |
| `GET /admin/approvals` | Yes | No | No |
| `POST /admin/approvals/<id>/approve` | Yes | No | No |
| `POST /admin/approvals/<id>/reject` | Yes | No | No |
| `GET /projects/<id>/progress` | Yes | Yes | Yes (own project) |
| `POST /projects/<id>/progress` (create deliverable) | Yes | Yes | No |
| `GET /deliverables/<id>` | Yes | Yes | Yes (own project) |
| `POST /deliverables/<id>/submit` | Yes | Yes (creator) | No |
| `POST /deliverables/<id>/qa-approve` | Yes | Yes (assigned QA) | No |
| `POST /deliverables/<id>/qa-sendback` | Yes | Yes (assigned QA) | No |
| `POST /deliverables/<id>/admin-send-client` | Yes | No | No |
| `POST /deliverables/<id>/admin-sendback` | Yes | No | No |
| `POST /deliverables/<id>/client-approve` | No | No | Yes |
| `POST /deliverables/<id>/client-sendback` | No | No | Yes |
| `POST /deliverables/<id>/comments` | Yes | Yes | Yes (own project) |
| `POST /deliverable-comments/<id>/resolve` | Yes | Yes (role-gated step) | No |
| `POST /deliverable-comments/<id>/toggle-visible` | Yes | No | No |
| `GET /api/activity` | Yes | Yes | No |
| `GET /api/users` | Yes | Yes | No |

---

## Adding a New Role (Future)

1. Add the role string to `User.role` allowed values.
2. Update `role_label` and `role_color` properties on the `User` model.
3. Add a branch in `projects_list` and `project_detail` for the new visibility logic.
4. Add a card to the role portal in `login.html` with the correct `data-for` attribute on demo rows.
5. Update the deliverable pipeline permission checks in the relevant routes.
6. Update the sidebar in `base.html` if the new role needs different nav items.
7. Add the role to the route permission table above.

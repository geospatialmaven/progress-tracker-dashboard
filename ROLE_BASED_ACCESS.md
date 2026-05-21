# Role-Based Access Control — Geospatial Maven Dashboard

## Roles

| Role | Value in DB | Who it is |
|---|---|---|
| Super Admin | `super_admin` | Internal admin / project manager |
| Developer | `developer` | GIS analysts, remote sensing specialists, writers |
| Client | `client` | External clients / stakeholders (e.g. UNDP, WWF) |

---

## Projects — Visibility Rules

### Super Admin
- Sees **all projects** in the system.
- Can create, edit, and delete any project.

### Developer
A developer sees a project if **any** of the following is true:
1. They are the **coordinator** of the project (`Project.coordinator_id == user.id`)
2. They are **assigned to at least one section** in the project via `SectionAssignment`

They do **not** see projects they have no involvement in, even if those projects exist in the database.

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

## How to Assign a Developer to a Project

Developers gain project access through **section assignments**, not directly on the project.

1. Open the project → go to a section.
2. In the section form, select the developer in the **Assignees** field.
3. This creates a `SectionAssignment` record linking the developer to that section.
4. The developer now sees the project in their Projects list.

Alternatively, set the developer as **Project Coordinator** when creating or editing the project — they will also gain access.

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
  coordinator_id  → FK → User (developer/admin who manages the project)
  client_user_id  → FK → User (client who owns the project)

Section
  project_id → FK → Project

SectionAssignment
  section_id → FK → Section
  user_id    → FK → User
  assignment_role  (lead | contributor | reviewer)
```

---

## Route Summary

| Route | super_admin | developer | client |
|---|---|---|---|
| `GET /projects` | All projects | Assigned + coordinated | Their projects only |
| `GET /projects/<id>` | Always | Only if assigned/coordinator | Only if client_user_id matches |
| `POST /projects` (create) | Yes | Yes | No (redirected) |
| `POST /projects/<id>/update` | Yes | Yes | No |
| `POST /projects/<id>/delete` | Yes | No | No |
| `GET /team` | Yes | No | No |
| `GET /my-tasks` | Yes | Yes | No (redirected to dashboard) |

---

## Adding a New Role (Future)

1. Add the role string to `User.role` allowed values.
2. Update `role_label` and `role_color` properties on the `User` model.
3. Add a branch in `projects_list` and `project_detail` for the new visibility logic.
4. Update `not_client` decorator if the new role should have write access.
5. Update the sidebar in `base.html` if the role needs different nav items.

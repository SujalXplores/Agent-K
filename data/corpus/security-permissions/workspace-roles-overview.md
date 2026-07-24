# Understanding workspace roles

Flowdeck has three built-in workspace-level roles: Owner (full billing and security control, exactly one per workspace but transferable), Admin (can manage members, integrations, and security settings but not billing), and Member (standard access scoped by whatever project-level permissions they're granted).

Project-level roles layer on top of the workspace role: within a specific project, a Member can additionally be a project Admin (can edit project settings and automations), Editor (can create/edit tasks), or Viewer (read-only). A workspace Admin does not automatically get project-Admin rights on every project - project access is granted explicitly per project.

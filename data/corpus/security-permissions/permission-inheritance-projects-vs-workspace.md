# How permission inheritance works between workspace and project levels

Permissions in Flowdeck are not purely hierarchical - a workspace Admin does not automatically inherit project-Admin rights on every project, and a workspace Member has zero project access by default until explicitly added to a specific project. This is a deliberate least-privilege design rather than a bug: workspace-level roles control workspace-wide settings (billing, security, integrations), while project-level roles independently control what a member can do within a given project's tasks.

The one exception is the workspace Owner, who always has implicit project-Admin rights on every project in the workspace regardless of explicit project membership, specifically so that a single compromised or departed project-owner situation can never lock the workspace Owner out of their own data.

When a new project is created, only its creator (who becomes project Owner) and the workspace Owner have access initially - other workspace Members, including workspace Admins, must be explicitly invited to that specific project before they can see it in their projects list, even though they could technically find and request access to it via the workspace's project directory if that directory is set to "visible to all members" under Workspace Settings > Security.

Guest accounts (see guest-access-external-collaborators) sit outside this inheritance model entirely: they have no workspace-level role at all, only whatever project-level Viewer/Editor access they were explicitly granted, and that access does not expand even if they're later added to additional projects by different project owners - each project grant is fully independent.

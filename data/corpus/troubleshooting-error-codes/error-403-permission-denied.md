# Error 403: Permission denied

A 403 response means your API key or session is authenticated but lacks permission for the requested action - most commonly a read-only scoped API key attempting a write operation, or a member without project-admin rights trying to delete a project. Check the key's scope under Workspace Settings > Developer > API Keys, or the member's role under the project's Members tab.

# Error 404: Workspace not found

A 404 on a workspace-scoped API call almost always means the workspace slug or ID in the URL path is wrong, or the API key being used belongs to a different workspace than the one referenced in the URL - API keys are workspace-scoped and cannot be used to access a different workspace's data even if you have separate membership there.

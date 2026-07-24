# Understanding API key scopes

Every API key is scoped to one of three permission levels at creation time: read-only (GET requests only), read-write (create/update tasks and projects, no destructive actions), or admin (includes deletion and member management endpoints). Scopes cannot be changed after creation - generate a new key with the correct scope instead.

Choose the narrowest scope that satisfies your integration's needs; a read-only key is recommended for any reporting or dashboard tool that only needs to pull data, since a leaked read-only key cannot modify or delete anything in the workspace.

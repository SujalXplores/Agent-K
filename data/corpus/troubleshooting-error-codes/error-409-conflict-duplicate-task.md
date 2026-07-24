# Error 409: Conflict when creating a task

A 409 on task creation means a task with the same external reference ID (used by integrations like the Jira sync, or by the "idempotency_key" field on the create-task API) already exists. This is intentional deduplication behavior to prevent double-created tasks when a client retries a create request that actually succeeded the first time but timed out before the response arrived.

If you're seeing unexpected 409s during a normal (non-retry) bulk import, check whether your import script is reusing the same idempotency_key across genuinely different tasks by mistake - each distinct task needs a distinct key.

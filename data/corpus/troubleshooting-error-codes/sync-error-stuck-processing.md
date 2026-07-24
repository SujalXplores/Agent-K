# Troubleshooting: task import/sync stuck in "Processing"

Bulk imports and Jira two-way syncs both show a "Processing" status banner while they run in the background rather than blocking your UI. For imports under 500 tasks, this should complete within about 2 minutes; if it's been stuck longer than 10 minutes, something has gone wrong rather than the job simply being slow.

First check Workspace Settings > Developer > Background Jobs (visible to workspace owners) for the specific job's status - it will show "running", "failed", or "stuck" along with an error summary if one is available. A "failed" status here means the job actually errored but the UI banner didn't update, which is a known display lag of a minute or two after the underlying job actually fails.

If the job shows "stuck" (running with no progress for over 15 minutes), it usually means an external dependency the job needs (e.g., the Jira API during a sync) became unresponsive mid-job. You can safely cancel it from the Background Jobs page - cancelling a stuck import does not partially apply the import; either all tasks from a batch commit together or none do, so there's no risk of a half-imported state.

After cancelling, re-run the import or sync. If it gets stuck again at the same point (check the "processed / total" counter shown in the job details), the issue is likely one specific malformed row or task in your source data rather than a general outage - export the job's error log and inspect the item at that index.

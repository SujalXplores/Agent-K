# Setting up two-way sync between Flowdeck and Jira

Two-way sync (available on Team and Enterprise plans) keeps a Flowdeck project and a Jira project's issues mirrored in both directions: creating a task in either tool creates the matching item in the other within about 30 seconds, and status/assignee changes propagate the same way.

Configure it under Project Settings > Integrations > Jira Sync by authenticating with a Jira API token (not your Jira password - Jira deprecated password auth for API access) and mapping Flowdeck's status columns to Jira's workflow statuses one-to-one. Unmapped statuses on either side are skipped during sync rather than causing an error.

Field mapping beyond status is limited by design: only title, description, assignee, and status sync automatically. Custom fields on either side do not sync unless you explicitly add a field mapping rule under the same settings page, and Flowdeck currently supports mapping up to 10 custom fields per project.

Conflicts (the same item edited in both tools within the same sync window) are resolved by "last write wins" based on server timestamp, and the losing edit is recorded in the sync's Activity Log so nothing is silently dropped without a trace.

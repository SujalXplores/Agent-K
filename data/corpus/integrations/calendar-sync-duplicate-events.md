# Troubleshooting duplicate events in Google Calendar sync

Duplicate calendar events after enabling Google Calendar sync usually happen when the same project was connected to sync twice - for example, once by the original member who set it up and again by a second member using their own Google account. Check Account Settings > Integrations > Google Calendar on every member's account, not just yours, since sync configuration is per-member, not per-workspace.

If only one member has it connected but duplicates still appear, disconnect and reconnect the sync - this clears Flowdeck's internal mapping between tasks and calendar event IDs and rebuilds it cleanly, which resolves duplicates caused by a stale mapping after a task was deleted and recreated with the same title.

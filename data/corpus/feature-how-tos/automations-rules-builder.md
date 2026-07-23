# Building automation rules

Project Settings > Automations opens a trigger-condition-action builder: choose a trigger (task created, status changed, due date reached, custom field updated), optional conditions (e.g. only if priority = High), and one or more actions (assign to a person, move to a column, post a Slack message, add a comment).

Automations run in the order they're listed on the Automations page, and each rule fires independently - if two rules both match the same trigger event, both execute rather than the first one short-circuiting the second. This matters if you have rules with conflicting actions (e.g. two rules both trying to move a task to different columns), since the later rule in the list wins in a direct conflict.

Each project supports up to 25 active automation rules on the Team plan (10 on Starter, unlimited on Enterprise). Rules can be temporarily disabled without deleting them via the toggle next to each rule, which is useful when debugging unexpected automated behavior without losing your rule configuration.

Automation actions execute asynchronously and are logged in each task's Activity tab with a small "automation" badge next to entries they caused, distinguishing them from manual member actions - this is the primary tool for debugging why a task moved or was reassigned unexpectedly.

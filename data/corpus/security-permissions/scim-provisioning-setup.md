# Setting up SCIM for automated user provisioning

SCIM (System for Cross-domain Identity Management, Enterprise plan only) automates member creation and deactivation by syncing from your identity provider, so offboarding an employee in Okta or Azure AD automatically deactivates their Flowdeck access without a manual step in Flowdeck itself. Enable it under Workspace Settings > Security > SCIM Provisioning, which generates a SCIM base URL and bearer token for your IdP.

In your IdP's SCIM app configuration, paste the base URL and bearer token, then map user attributes (email, given name, family name are required; department and title are optional pass-throughs stored on the member profile but not used for permissions). Group mappings are optional but recommended: mapping an IdP group to a Flowdeck workspace role means adding a user to that group in your IdP automatically grants the corresponding Flowdeck role.

SCIM-provisioned members cannot have their role changed manually inside Flowdeck while SCIM group mapping is active for that member - the IdP is treated as the source of truth, and manual role edits in Flowdeck's UI would just be overwritten on the next SCIM sync cycle (which runs roughly every 15 minutes, or immediately on an IdP-side change if your IdP supports push SCIM rather than polling).

Deactivation via SCIM does not delete the member's task history or comments - it converts their account to a deactivated state, similar to a manual removal (see remove-offboard-user), preserving audit trail integrity while blocking further access.

If a member needs a role that doesn't match any mapped IdP group, either add a new group mapping on the Flowdeck side or, for a one-off exception, remove that specific member from SCIM group-based role management via the "Override role manually" toggle on their member profile, which opts just that one member out of automatic role-syncing while leaving provisioning/deprovisioning still SCIM controlled.

# Rotating an API key without downtime

To rotate a key without breaking whatever consumes it, generate a second key alongside the existing one under Workspace Settings > Developer > API Keys - Flowdeck allows up to 5 active keys per workspace simultaneously, so both old and new can be valid at once.

Update your integration or script to use the new key value, verify it works (check the "Last used" timestamp on the new key updates), and only then revoke the old key. This avoids the downtime window you'd get from revoking first and updating second.

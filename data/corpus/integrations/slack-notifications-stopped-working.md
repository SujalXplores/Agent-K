# Troubleshooting: Slack notifications suddenly stopped

Slack notifications typically stop for one of three reasons: the OAuth token was revoked on Slack's side (e.g. a Slack admin removed the Flowdeck app), the target channel was archived or deleted, or your workspace's notification rules were changed. Start by checking Workspace Settings > Integrations > Slack for a red "Reconnect required" badge, which specifically indicates a revoked token.

If there's no reconnect badge, check the specific project's Settings > Notifications tab to confirm the notification rules (task assigned, status changed, etc.) are still enabled - workspace-level reorganizations sometimes reset per-project settings when a project is moved between workspaces.

If the channel itself was archived in Slack, Flowdeck cannot detect this proactively - messages simply stop arriving with no error surfaced on the Flowdeck side, since Slack's API returns success even for posts to an archived channel's underlying ID in some cases. Re-select the target channel from the dropdown under Slack integration settings to force a fresh validation.

As a last resort, disconnect and reconnect the Slack integration entirely - this forces a brand-new OAuth handshake and re-validates channel access from scratch, which resolves the majority of "notifications silently stopped" reports that aren't explained by the two checks above.

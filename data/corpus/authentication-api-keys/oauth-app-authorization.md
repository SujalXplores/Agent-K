# Authorizing third-party OAuth apps

When a third-party app requests OAuth access to your Flowdeck workspace, you'll see a consent screen listing exactly which scopes it is requesting (read tasks, write comments, manage members, etc.) before you approve it. Approved apps appear under Workspace Settings > Security > Connected Apps, where you can review or revoke access at any time without needing the third party's cooperation.

Revoking an OAuth app's access immediately invalidates its access and refresh tokens; the app will need the member to go through the consent flow again to regain access, and any webhook subscriptions it created are automatically deleted at revocation time.

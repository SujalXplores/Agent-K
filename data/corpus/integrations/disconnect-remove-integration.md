# Disconnecting or removing an integration

To fully remove an integration, go to Workspace Settings > Integrations, find it in the "Connected" list, and click "Disconnect". This revokes the OAuth token Flowdeck holds for that service and deletes any associated webhook subscriptions - it does not delete data already synced into Flowdeck (e.g. previously-created GitHub links on tasks remain, they simply won't update anymore).

# Troubleshooting: stuck in a login redirect loop after changing SSO settings

A login loop after an SSO configuration change almost always means the ACS URL or Entity ID in your identity provider no longer matches what Flowdeck expects, or the email attribute mapping was accidentally changed or removed during the IdP-side edit. The browser bounces between Flowdeck's login page and the IdP's login page without ever landing on a workspace.

First, check whether the break-glass non-SSO admin account (see the sso-saml-setup guide) still works by logging in directly at /login?sso=bypass - if that works, the issue is confirmed to be SSO-side configuration, not a Flowdeck outage.

From that break-glass account, go to Workspace Settings > Security > Single Sign-On and re-run "Test connection". This performs a live handshake and will surface the specific SAML error (e.g. "Entity ID mismatch", "Missing email attribute", "Certificate expired") rather than leaving you guessing from the redirect loop alone.

The most common root cause we see is a certificate rotation on the IdP side that wasn't mirrored into Flowdeck's SAML config - IdPs typically rotate signing certificates annually, and if Flowdeck still has the old certificate on file, signature validation silently fails and produces exactly this loop. Re-upload the current certificate from your IdP's metadata to resolve it.

If the loop persists after re-testing with a fresh certificate, temporarily disable "Require SSO for all members" from the break-glass account to restore access for everyone while you continue diagnosing, then re-enable enforcement once the test connection passes cleanly.

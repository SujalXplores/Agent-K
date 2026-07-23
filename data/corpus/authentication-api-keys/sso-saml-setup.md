# Setting up SAML SSO for your workspace

SAML SSO is available on the Team and Enterprise plans. Start under Workspace Settings > Security > Single Sign-On > "Configure SAML", which generates a unique Assertion Consumer Service (ACS) URL and Entity ID for your workspace to paste into your identity provider (Okta, Azure AD, OneLogin, and Google Workspace are all tested).

In your IdP, create a new SAML application using Flowdeck's ACS URL and Entity ID, then map at minimum the email and full-name attributes - Flowdeck matches incoming SSO logins to existing members by email address, so the email attribute mapping is mandatory, not optional.

Download your IdP's metadata XML (or copy its SSO URL and x.509 certificate manually) and paste it back into Flowdeck's SAML configuration page. Click "Test connection" - this performs a real SSO handshake against a Flowdeck test user before you turn on enforcement, so misconfigurations surface before real members are affected.

Once the test succeeds, toggle "Require SSO for all members" to enforce it workspace-wide. We recommend keeping one break-glass password-based admin account outside of SSO enforcement in case your IdP has an outage - Flowdeck lets you designate exactly one such account per workspace under the SSO settings page.

"""Generate 50 synthetic support documents for the Acme Corp support corpus.

These are deliberately synthetic — no real data, no PII. The docs cover
common support topics (passwords, billing, shipping, account, technical)
so retrieval has enough variety to demonstrate meaningful search results.

Run: python -m corpus.generate
Output: corpus/docs/*.md (50 files)
"""

from __future__ import annotations

from pathlib import Path

# ─── 50 synthetic support documents ───────────────────────────────────
# Format: (filename, title, category, content)

DOCUMENTS: list[tuple[str, str, str, str]] = [
    # ─── Account & Login (10 docs) ───────────────────────────────
    (
        "account-01-reset-password.md",
        "How do I reset my password?",
        "account",
        """To reset your password, go to the login page and click "Forgot Password." \
Enter your registered email address and we will send you a reset link. The link \
is valid for 30 minutes. If you don't receive the email within 5 minutes, check \
your spam folder. If you still can't find it, contact support and we can resend \
the reset email manually. After clicking the link, you'll be prompted to enter a \
new password. Passwords must be at least 8 characters and include one uppercase \
letter, one number, and one special character.""",
    ),
    (
        "account-02-change-email.md",
        "How do I change my account email address?",
        "account",
        """To change your email address, log in to your account and navigate to \
Settings > Profile > Email. Enter your new email address and click "Update." \
We'll send a verification email to the new address. You must click the \
verification link within 24 hours to confirm the change. Your old email will \
remain active until the new one is verified. If you no longer have access to \
your old email, contact support with proof of identity.""",
    ),
    (
        "account-03-enable-2fa.md",
        "How do I enable two-factor authentication?",
        "account",
        """Two-factor authentication (2FA) adds an extra layer of security to your \
account. To enable it, go to Settings > Security > Two-Factor Authentication. \
Choose your preferred method: authenticator app (recommended) or SMS. Scan the \
QR code with your authenticator app (Google Authenticator, Authy, etc.) and \
enter the 6-digit code to confirm. Save your backup codes in a secure location — \
you'll need them if you lose access to your authenticator device.""",
    ),
    (
        "account-04-delete-account.md",
        "How do I delete my account?",
        "account",
        """Account deletion is permanent and cannot be undone. To delete your \
account, go to Settings > Account > Delete Account. You'll be asked to enter \
your password to confirm. All your data, including order history and saved \
preferences, will be permanently removed within 30 days. If you have an active \
subscription, it will be cancelled immediately and you won't be charged again. \
Consider exporting your data before deletion if you need it later.""",
    ),
    (
        "account-05-locked-out.md",
        "I'm locked out of my account. What should I do?",
        "account",
        """If you've entered the wrong password too many times, your account may \
be temporarily locked for security. Wait 15 minutes and try again. If you're \
still locked out after waiting, use the "Forgot Password" link to reset your \
password. If you believe your account was locked in error, contact support with \
your username and the email associated with your account. We can unlock it \
manually after verifying your identity.""",
    ),
    (
        "account-06-merge-accounts.md",
        "Can I merge two accounts?",
        "account",
        """Yes, we can merge two accounts if you can verify ownership of both. \
Contact support with the email addresses of both accounts. We'll verify your \
identity and transfer all data (orders, subscriptions, preferences) from the \
secondary account to the primary one. The secondary account will then be \
deleted. This process takes 3-5 business days. Note that duplicate orders or \
subscriptions will not be combined — only transferred.""",
    ),
    (
        "account-07-update-profile.md",
        "How do I update my profile information?",
        "account",
        """To update your profile, log in and go to Settings > Profile. You can \
change your display name, profile picture, bio, and contact preferences. \
Changes take effect immediately. Your profile picture must be under 5MB and in \
JPG, PNG, or GIF format. Your display name can be up to 50 characters and must \
not contain profanity or impersonate other users.""",
    ),
    (
        "account-08-session-timeout.md",
        "Why does my session keep timing out?",
        "account",
        """For security, your session automatically expires after 30 minutes of \
inactivity. If you're being logged out more frequently, check the following: \
1) Are you using a VPN that changes your IP address? 2) Is your browser set to \
block cookies? 3) Are you logged in on multiple devices? If none of these apply, \
try clearing your browser cache and cookies, then log in again. If the issue \
persists, contact support.""",
    ),
    (
        "account-09-social-login.md",
        "Can I log in with Google or GitHub?",
        "account",
        """Yes, we support social login with Google and GitHub. On the login page, \
click the "Continue with Google" or "Continue with GitHub" button. You'll be \
redirected to the provider to authorize the connection. If you already have an \
account with the same email, we'll link the social login to your existing \
account. If not, a new account will be created automatically. You can disconnect \
a social login at any time from Settings > Security > Connected Accounts.""",
    ),
    (
        "account-10-export-data.md",
        "How do I export my account data?",
        "account",
        """You can export all your account data (profile, orders, preferences, \
support tickets) by going to Settings > Privacy > Export Data. Click "Request \
Export" and we'll generate a downloadable ZIP file. The export is usually ready \
within 10 minutes and you'll receive an email when it's available. The download \
link expires after 7 days. The data is provided in JSON and CSV formats.""",
    ),
    # ─── Billing & Payments (10 docs) ────────────────────────────
    (
        "billing-01-payment-methods.md",
        "What payment methods do you accept?",
        "billing",
        """We accept the following payment methods: Visa, Mastercard, American \
Express, Discover, and Diners Club credit/debit cards. We also accept PayPal \
and Apple Pay. For enterprise accounts, we support wire transfer and invoicing. \
All card payments are processed through a PCI-DSS compliant payment gateway. \
We do not store your full card number on our servers — only a tokenized \
reference for recurring charges.""",
    ),
    (
        "billing-02-update-card.md",
        "How do I update my payment card?",
        "billing",
        """To update your payment card, go to Settings > Billing > Payment Methods. \
Click "Add New Card" and enter your card details. You can set the new card as \
your default payment method. The old card will remain on file unless you remove \
it. To remove a card, click the trash icon next to it. You cannot remove a card \
that's associated with an active subscription — update the subscription's \
payment method first.""",
    ),
    (
        "billing-03-failed-payment.md",
        "My payment failed. What should I do?",
        "billing",
        """If your payment failed, first check that your card hasn't expired and \
has sufficient funds. Common causes include: incorrect CVV, expired card, \
insufficient funds, or your bank blocking the transaction. You can retry the \
payment from Settings > Billing > Invoices. If the payment fails again, try a \
different card or contact your bank. After 3 failed attempts, your subscription \
will be suspended until a successful payment is made.""",
    ),
    (
        "billing-04-refund-policy.md",
        "What is your refund policy?",
        "billing",
        """We offer a 30-day money-back guarantee on all paid plans. If you're not \
satisfied, contact support within 30 days of your purchase for a full refund. \
Refunds are processed within 5-7 business days to your original payment method. \
Note that refunds are not available for: 1) accounts terminated for terms of \
service violations, 2) purchases older than 30 days, or 3) partial-month usage \
after the 30-day window. Annual plans are refunded on a pro-rated basis.""",
    ),
    (
        "billing-05-download-invoices.md",
        "How do I download my invoices?",
        "billing",
        """All past invoices are available under Settings > Billing > Invoices. \
Click on any invoice to download it as a PDF. Invoices include your company \
name, billing address, tax ID (if provided), line items, and payment status. \
If you need invoices older than what's shown, contact support — we retain \
invoice records for 7 years for tax compliance purposes.""",
    ),
    (
        "billing-06-cancel-subscription.md",
        "How do I cancel my subscription?",
        "billing",
        """To cancel your subscription, go to Settings > Billing > Subscription \
and click "Cancel Subscription." Your subscription will remain active until the \
end of your current billing period — you won't be charged again. You can \
re-subscribe at any time. If you cancel within the 30-day money-back window, \
you'll receive a full refund. Cancellation is immediate for monthly plans and \
effective at the end of the billing cycle for annual plans.""",
    ),
    (
        "billing-07-change-plan.md",
        "How do I upgrade or downgrade my plan?",
        "billing",
        """You can change your plan at any time from Settings > Billing > \
Subscription. Upgrades take effect immediately and you'll be charged a pro-rated \
amount for the remainder of the billing period. Downgrades take effect at the \
start of your next billing cycle — you'll keep your current plan's features \
until then. If you downgrade to a plan with fewer seats than your current team \
size, you'll need to remove team members first.""",
    ),
    (
        "billing-08-tax-id.md",
        "How do I add a tax ID to my invoices?",
        "billing",
        """To add a tax ID (VAT, GST, EIN, etc.) to your invoices, go to Settings > \
Billing > Tax Information. Enter your tax ID number and select the type. The \
tax ID will appear on all future invoices. For past invoices, contact support \
and we can re-issue them with your tax ID included. This is especially \
important for EU customers who need VAT-compliant invoices.""",
    ),
    (
        "billing-09-pricing-tiers.md",
        "What are your pricing tiers?",
        "billing",
        """We offer three pricing tiers: 1) Starter ($9/month) — 1 user, 5GB \
storage, email support. 2) Pro ($29/month) — 5 users, 50GB storage, priority \
email support, advanced analytics. 3) Enterprise ($99/month) — unlimited users, \
500GB storage, phone support, custom integrations, SSO. All plans include a \
30-day free trial with no credit card required. Annual billing gets a 20% \
discount. Custom pricing is available for organizations over 100 users.""",
    ),
    (
        "billing-10-team-seats.md",
        "How do I add or remove team seats?",
        "billing",
        """To add team seats, go to Settings > Team > Manage Seats. Click "Add \
Seats" and select how many additional seats you need. You'll be charged a \
pro-rated amount for the remainder of the billing period. To remove seats, \
first remove the team members occupying them, then reduce the seat count. \
Removed seats take effect at the start of the next billing cycle. You cannot \
remove seats that are currently assigned to active team members.""",
    ),
    # ─── Technical & API (10 docs) ───────────────────────────────
    (
        "tech-01-api-key.md",
        "How do I get an API key?",
        "technical",
        """To get an API key, go to Settings > Developer > API Keys. Click \
"Generate New Key" and give it a name (e.g., "Production App"). Your API key \
will be displayed once — copy it immediately as it won't be shown again. API \
keys are scoped to your account and have rate limits of 1000 requests per \
minute. Keep your API key secret — do not commit it to version control or \
expose it in client-side code. You can revoke a key at any time.""",
    ),
    (
        "tech-02-rate-limits.md",
        "What are the API rate limits?",
        "technical",
        """API rate limits depend on your plan: Starter (100 req/min), Pro (1000 \
req/min), Enterprise (10000 req/min). Rate limit headers are included in every \
response: X-RateLimit-Limit, X-RateLimit-Remaining, and X-RateLimit-Reset. If \
you exceed your limit, you'll receive a 429 Too Many Requests response. \
Implement exponential backoff in your client to handle rate limiting \
gracefully. Contact support if you need a temporary limit increase for data \
migration.""",
    ),
    (
        "tech-03-webhooks.md",
        "How do I set up webhooks?",
        "technical",
        """Webhooks allow your app to receive real-time event notifications. To \
set up webhooks, go to Settings > Developer > Webhooks. Click "Add Endpoint" \
and enter your URL. Select which events you want to subscribe to (e.g., \
order.created, payment.failed, user.updated). We'll send a POST request to \
your URL with a JSON payload for each event. Each webhook includes a signature \
header (X-Webhook-Signature) that you can verify using your webhook secret.""",
    ),
    (
        "tech-04-sdk-install.md",
        "How do I install the SDK?",
        "technical",
        """Our official SDK is available for Python, JavaScript, and Go. \
Python: pip install acme-sdk. JavaScript: npm install @acme/sdk. Go: go get \
github.com/acme/sdk. After installation, initialize the SDK with your API key: \
```python\nfrom acme import Client\nclient = Client(api_key='your-key')\n```. \
The SDK automatically handles retries, rate limiting, and pagination. See the \
full documentation at docs.acme.com/sdk for advanced configuration options.""",
    ),
    (
        "tech-05-error-codes.md",
        "What do the API error codes mean?",
        "technical",
        """Common API error codes: 400 Bad Request — your request body or \
parameters are malformed. 401 Unauthorized — your API key is missing or \
invalid. 403 Forbidden — your API key doesn't have permission for this \
resource. 404 Not Found — the requested resource doesn't exist. 429 Too Many \
Requests — you've exceeded your rate limit. 500 Internal Server Error — \
something went wrong on our side. 503 Service Unavailable — we're temporarily \
down for maintenance. All error responses include an error code and message.""",
    ),
    (
        "tech-06-pagination.md",
        "How does API pagination work?",
        "technical",
        """List endpoints use cursor-based pagination. The response includes a \
``next_cursor`` field — if it's null, you've reached the end. To get the next \
page, pass the cursor as a query parameter: GET /api/v1/items?cursor=abc123. \
The default page size is 20, and you can request up to 100 items per page using \
the ``limit`` parameter. We recommend using cursor-based pagination over offset \
pagination for large datasets as it's more performant and consistent.""",
    ),
    (
        "tech-07-ssl-certificates.md",
        "How do I configure SSL certificates?",
        "technical",
        """For custom domains, we automatically provision and renew SSL \
certificates using Let's Encrypt. To add a custom domain, go to Settings > \
Domains > Add Domain and follow the DNS verification steps. Once verified, \
SSL is provisioned within 10 minutes. If you need to use your own SSL \
certificate (e.g., for compliance), contact support — we support custom \
certificate upload for Enterprise plans. All API endpoints use TLS 1.2+.""",
    ),
    (
        "tech-08-data-export-api.md",
        "How do I export data via the API?",
        "technical",
        """You can export your data programmatically using the /api/v1/export \
endpoint. Send a POST request with the data types you want to export and the \
format (JSON or CSV). The export is asynchronous — you'll receive a job ID. \
Poll GET /api/v1/export/{job_id} to check the status. Once complete, the \
response includes a download URL valid for 24 hours. Large exports may take \
several minutes. Rate limit for exports is 1 request per hour.""",
    ),
    (
        "tech-09-uptime-status.md",
        "Where can I check system status?",
        "technical",
        """Our public status page is at status.acme.com. It shows real-time \
uptime for all services, scheduled maintenance windows, and incident history. \
You can subscribe to status updates via email, SMS, or webhook. Our uptime SLA \
is 99.9% for Pro plans and 99.99% for Enterprise plans. If we fail to meet the \
SLA, you're eligible for service credits — contact support to request them.""",
    ),
    (
        "tech-10-ip-allowlist.md",
        "Can I restrict API access to specific IP addresses?",
        "technical",
        """Yes, Enterprise plans support IP allowlisting for API access. Go to \
Settings > Developer > IP Allowlist and add the IP addresses or CIDR ranges \
you want to allow. When the allowlist is active, requests from any other IP \
address will receive a 403 Forbidden response. You can add up to 50 IP \
addresses or CIDR ranges. Changes take effect within 1 minute. This is \
independent of your API key — both the key and the IP must be valid.""",
    ),
    # ─── Shipping & Orders (10 docs) ─────────────────────────────
    (
        "shipping-01-tracking.md",
        "How do I track my order?",
        "shipping",
        """To track your order, go to your account > Orders and click on the \
order number. You'll see the current status and tracking number. Click the \
tracking number to view the carrier's tracking page. You'll also receive \
tracking updates via email. If your order has been marked as delivered but \
you haven't received it, wait 24 hours (carriers sometimes mark as delivered \
before dropping off) and then contact support with your order number.""",
    ),
    (
        "shipping-02-shipping-costs.md",
        "How much does shipping cost?",
        "shipping",
        """Shipping costs depend on your location and the shipping method: \
Standard (5-7 business days) — $5.99 or free for orders over $50. Express \
(2-3 business days) — $12.99. Overnight — $24.99. International shipping is \
calculated at checkout based on destination country and package weight. We \
ship to over 40 countries. Duties and taxes are included for orders shipped \
within the US; international orders may incur additional customs fees.""",
    ),
    (
        "shipping-03-return-item.md",
        "How do I return an item?",
        "shipping",
        """We accept returns within 30 days of delivery. Items must be unused \
and in original packaging. To initiate a return, go to Orders > select the \
order > "Request Return." Choose your reason and print the prepaid return \
label. Drop off the package at any authorized carrier location. Refunds are \
processed within 3-5 business days of receiving the returned item. Original \
shipping costs are non-refundable unless the return is due to our error.""",
    ),
    (
        "shipping-04-change-address.md",
        "Can I change my shipping address after ordering?",
        "shipping",
        """You can change your shipping address if the order hasn't been \
shipped yet. Go to Orders > select the order > "Edit Shipping Address." If \
the order has already been shipped, we can't change the address, but you can \
contact the carrier directly to request a redirect (fees may apply). If the \
package is returned to us due to an incorrect address, we'll contact you to \
arrange re-shipping at no additional cost.""",
    ),
    (
        "shipping-05-international.md",
        "Do you ship internationally?",
        "shipping",
        """Yes, we ship to over 40 countries. International shipping costs are \
calculated at checkout based on destination and weight. Delivery times vary \
by country: Canada/Mexico (7-10 business days), Europe (10-15 business days), \
Asia/Pacific (15-20 business days). International orders may be subject to \
customs duties and taxes, which are the responsibility of the recipient. \
Some items may be restricted in certain countries — check the product page \
for details.""",
    ),
    (
        "shipping-06-damaged-item.md",
        "My item arrived damaged. What should I do?",
        "shipping",
        """We're sorry your item arrived damaged. Please contact support within \
7 days of delivery with your order number and a photo of the damaged item. \
We'll send a replacement at no cost and provide a prepaid return label for \
the damaged item. If you prefer a refund instead of a replacement, let us \
know. Do not dispose of the damaged item or its packaging until we've \
resolved the issue — we may need it for the carrier claim.""",
    ),
    (
        "shipping-07-missing-items.md",
        "My order is missing items. What should I do?",
        "shipping",
        """If your order is missing items, first check the packing slip to see \
if the missing items were shipped separately (some items ship from different \
warehouses). If the packing slip indicates all items were in the same \
shipment, contact support within 7 days with your order number and a list of \
the missing items. We'll investigate with the carrier and either send \
replacements or issue a refund for the missing items.""",
    ),
    (
        "shipping-08-bulk-orders.md",
        "Do you offer bulk ordering discounts?",
        "shipping",
        """Yes, we offer bulk discounts for orders over 50 units. Contact our \
sales team at sales@acme.com with your requirements. Bulk orders of 50-99 \
units receive a 10% discount, 100-499 units receive 15%, and 500+ units \
receive 20%. Bulk orders may have a longer lead time (2-3 weeks) depending \
on inventory. Custom packaging and branding is available for orders over \
500 units at an additional cost.""",
    ),
    (
        "shipping-09-delivery-issues.md",
        "What if my package is lost in transit?",
        "shipping",
        """If your package hasn't arrived within the expected delivery window \
plus 3 business days, contact support with your order number. We'll file a \
claim with the carrier and initiate an investigation. If the carrier confirms \
the package is lost, we'll send a replacement or issue a full refund — your \
choice. Investigations typically take 5-7 business days. If the package is \
found after a replacement has been sent, we'll arrange for the original \
package to be returned.""",
    ),
    (
        "shipping-10-pickup.md",
        "Can I pick up my order in person?",
        "shipping",
        """Yes, we offer in-store pickup at select locations. During checkout, \
select "Pickup" as the shipping method and choose your preferred store \
location. You'll receive an email when your order is ready for pickup \
(usually within 2-4 hours during business hours). Bring your order \
confirmation and a photo ID. Orders must be picked up within 7 days or \
they'll be cancelled and refunded. Pickup is free with no minimum order.""",
    ),
    # ─── Product & Features (10 docs) ────────────────────────────
    (
        "product-01-dark-mode.md",
        "How do I enable dark mode?",
        "product",
        """Dark mode is available on all plans. To enable it, go to Settings > \
Appearance > Theme and select "Dark." You can also choose "System" to \
automatically match your operating system's dark mode setting. Dark mode \
applies to the web app, mobile app, and email notifications. If you're using \
the API, you can set the theme per-user via the /api/v1/users/me/preferences \
endpoint with the ``theme`` parameter set to "dark" or "light".""",
    ),
    (
        "product-02-notifications.md",
        "How do I manage notification preferences?",
        "product",
        """To manage notifications, go to Settings > Notifications. You can \
enable or disable notifications for: order updates, payment receipts, \
security alerts, product announcements, and support ticket updates. Each \
notification type can be configured independently for email, push, and SMS. \
Security alerts cannot be fully disabled — only reduced to critical-only. \
Changes take effect immediately.""",
    ),
    (
        "product-03-integrations.md",
        "What integrations are available?",
        "product",
        """We offer native integrations with: Slack (notifications), Salesforce \
(CRM sync), HubSpot (contact sync), Zapier (5000+ apps), Microsoft Teams \
(notifications), and Google Calendar (scheduling). Enterprise plans also \
support custom integrations via our REST API and webhooks. To set up an \
integration, go to Settings > Integrations and click "Connect" next to the \
service you want to integrate. Most integrations require OAuth authorization.""",
    ),
    (
        "product-04-mobile-app.md",
        "Is there a mobile app?",
        "product",
        """Yes, our mobile app is available for iOS (App Store) and Android \
(Google Play). Search for "Acme" in your app store. The app supports all \
core features: browsing, ordering, order tracking, notifications, and \
account management. Push notifications are enabled by default but can be \
customized in Settings > Notifications. The app requires iOS 14+ or Android \
8+. Offline mode is available for viewing previously loaded data.""",
    ),
    (
        "product-05-search-filters.md",
        "How do I use advanced search filters?",
        "product",
        """Advanced search filters help you find exactly what you need. On the \
search page, click "Filters" to expand the options. You can filter by: \
category, price range, brand, rating, availability, and date added. Filters \
can be combined — all selected filters must match (AND logic). To save a \
filter combination for future use, click "Save Search" after applying your \
filters. Saved searches appear in the sidebar for quick access. You can have \
up to 10 saved searches.""",
    ),
    (
        "product-06-collaboration.md",
        "How does team collaboration work?",
        "product",
        """Team collaboration features are available on Pro and Enterprise \
plans. You can: 1) Share items with team members via shared collections. \
2) Leave comments and annotations on shared items. 3) Assign tasks and track \
progress. 4) View activity feeds to see what your team is working on. \
Team members must be invited via email and accept the invitation to join. \
Each team member has their own login but shares the team's subscription and \
resources.""",
    ),
    (
        "product-07-custom-fields.md",
        "Can I create custom fields?",
        "product",
        """Yes, Pro and Enterprise plans support custom fields. Go to Settings > \
Custom Fields > Add Field. Choose the field type: text, number, date, \
dropdown, or checkbox. Give it a name and optionally a default value. Custom \
fields appear on item detail pages and can be used in search filters and \
exports. Enterprise plans also support formula fields that compute values \
based on other fields. You can have up to 25 custom fields per workspace.""",
    ),
    (
        "product-08-automation-rules.md",
        "How do I set up automation rules?",
        "product",
        """Automation rules let you trigger actions based on events. Go to \
Settings > Automation > Add Rule. Define a trigger (e.g., "when an item is \
created") and one or more actions (e.g., "assign to user," "send email," \
"set custom field"). Rules can have conditions (e.g., "only if category is \
'technical'"). Rules are evaluated in order and can be enabled/disabled \
individually. Enterprise plans support multi-step rules with delays and \
conditional branching.""",
    ),
    (
        "product-09-analytics.md",
        "What analytics are available?",
        "product",
        """Analytics are available on Pro and Enterprise plans. The analytics \
dashboard shows: total items, items by category, activity trends, team \
productivity, and custom report builder. You can filter by date range, \
category, and team member. Reports can be exported as CSV or PDF and \
scheduled for automatic email delivery (daily, weekly, or monthly). \
Enterprise plans also support custom dashboards and API-based data export \
for BI tools.""",
    ),
    (
        "product-10-accessibility.md",
        "What accessibility features are available?",
        "product",
        """We're committed to WCAG 2.2 AA compliance. Accessibility features \
include: keyboard navigation, screen reader support (ARIA labels), high \
contrast mode, font size adjustment (Settings > Appearance > Font Size), \
reduced motion option (Settings > Appearance > Reduce Motion), and alt text \
support for images. If you encounter an accessibility barrier, please \
contact us at accessibility@acme.com and we'll prioritize fixing it.""",
    ),
]


def generate_corpus(output_dir: Path) -> int:
    """Write all synthetic docs as .md files in output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for filename, title, category, content in DOCUMENTS:
        filepath = output_dir / filename
        filepath.write_text(
            f"# {title}\n\n{content}\n",
            encoding="utf-8",
        )

    print(f"Generated {len(DOCUMENTS)} documents in {output_dir}")
    return len(DOCUMENTS)


if __name__ == "__main__":
    docs_dir = Path(__file__).parent / "docs"
    generate_corpus(docs_dir)

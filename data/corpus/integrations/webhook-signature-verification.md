# Verifying Flowdeck webhook signatures

Every webhook payload includes an X-Flowdeck-Signature header, an HMAC-SHA256 hash of the raw request body signed with your webhook's signing secret (shown once at webhook creation under Workspace Settings > Developer > Webhooks). Recompute the HMAC over the raw body on your receiving end and compare it to the header value using a constant-time comparison before trusting the payload.

Skipping signature verification means any party who discovers your webhook URL could POST forged payloads to your endpoint - always verify the signature server-side rather than relying on the URL being secret, since webhook URLs can leak through logs or browser history.

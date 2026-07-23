# How do I set up webhooks?

Webhooks allow your app to receive real-time event notifications. To set up webhooks, go to Settings > Developer > Webhooks. Click "Add Endpoint" and enter your URL. Select which events you want to subscribe to (e.g., order.created, payment.failed, user.updated). We'll send a POST request to your URL with a JSON payload for each event. Each webhook includes a signature header (X-Webhook-Signature) that you can verify using your webhook secret.

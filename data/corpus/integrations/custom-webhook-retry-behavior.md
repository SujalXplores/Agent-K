# How Flowdeck retries failed outgoing webhooks

If your webhook endpoint returns a non-2xx status or times out (5 second timeout), Flowdeck retries with exponential backoff: 30 seconds, 2 minutes, 10 minutes, then 1 hour, up to 5 total attempts over roughly 90 minutes before marking the delivery as permanently failed.

Failed deliveries (after all retries are exhausted) are listed under Workspace Settings > Developer > Webhooks > "Delivery log" with the response code and body your endpoint returned on the final attempt, so you can debug without needing to reproduce the event manually.

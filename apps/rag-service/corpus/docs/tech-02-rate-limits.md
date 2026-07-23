# What are the API rate limits?

API rate limits depend on your plan: Starter (100 req/min), Pro (1000 req/min), Enterprise (10000 req/min). Rate limit headers are included in every response: X-RateLimit-Limit, X-RateLimit-Remaining, and X-RateLimit-Reset. If you exceed your limit, you'll receive a 429 Too Many Requests response. Implement exponential backoff in your client to handle rate limiting gracefully. Contact support if you need a temporary limit increase for data migration.

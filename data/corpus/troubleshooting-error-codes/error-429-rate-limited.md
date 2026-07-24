# Error 429: Too many requests

A 429 means you've exceeded the API rate limit for your plan (100/min on Starter and Team, 500/min on Enterprise - see the api-rate-limits doc). The response includes a Retry-After header in seconds; wait that long before retrying rather than retrying immediately, which only extends the throttling window.

If you're consistently hitting 429s during normal usage (not a bulk import), consider switching high-volume operations to the batch endpoints under /v1/batch/*, which count as a single request against your rate limit regardless of item count.

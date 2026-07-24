# API rate limits and how to handle 429s

Flowdeck's API allows 100 requests per minute per API key on the Starter and Team plans, and 500 requests per minute on Enterprise. Exceeding the limit returns HTTP 429 with a Retry-After header indicating how many seconds to wait before the next request will succeed.

For bulk operations (e.g. importing hundreds of tasks), use the batch endpoints under /v1/batch/* instead of looping individual create calls - batch endpoints count as a single request against your rate limit regardless of how many items are included, up to 500 items per batch call.

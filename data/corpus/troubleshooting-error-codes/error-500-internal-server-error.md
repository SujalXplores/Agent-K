# Troubleshooting: Error 500 (Internal Server Error)

A 500 response indicates an unhandled error on Flowdeck's servers, not a problem with your request - unlike 4xx errors, there's nothing client-side to fix. The first step is to check Flowdeck's status page (status.flowdeck.example) for an active incident matching the time your request failed.

If there's no active incident listed, the 500 may be isolated to a specific request payload or workspace state. Retry the exact same request once after a short delay (a few seconds) - a meaningful fraction of 500s are transient and succeed on retry without any change needed.

If the same request reliably reproduces a 500 on every retry, capture the response body's "request_id" field (every Flowdeck response includes one, success or failure) and include it when contacting support - this ID lets support locate the exact server-side error and stack trace without needing you to describe the symptom in words.

Do not build automatic retry-and-ignore logic around 500s in production integrations without a cap - repeatedly retrying a request that deterministically 500s can itself contribute to load issues on the affected endpoint. Cap retries at 2-3 attempts with backoff and surface the failure rather than looping indefinitely.

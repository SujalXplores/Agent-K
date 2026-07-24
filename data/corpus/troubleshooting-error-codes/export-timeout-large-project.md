# Export request times out on a large project

Exporting a project with more than roughly 5,000 tasks can exceed the synchronous export endpoint's 30-second timeout. For projects at or above that size, use the asynchronous export flow instead: request the export, receive a job ID immediately, then poll the job status endpoint until it reports "complete" with a download link, rather than waiting on a single long-running request.

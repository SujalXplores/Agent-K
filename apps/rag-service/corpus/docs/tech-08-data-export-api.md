# How do I export data via the API?

You can export your data programmatically using the /api/v1/export endpoint. Send a POST request with the data types you want to export and the format (JSON or CSV). The export is asynchronous — you'll receive a job ID. Poll GET /api/v1/export/{job_id} to check the status. Once complete, the response includes a download URL valid for 24 hours. Large exports may take several minutes. Rate limit for exports is 1 request per hour.

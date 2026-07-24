# Error 422: Validation failed

A 422 means the request was well-formed JSON but failed field-level validation - for example, a due_date field containing a past date on task creation, or a title exceeding the 500-character limit. The response body includes a "validation_errors" array naming exactly which field(s) failed and why, so check that array rather than guessing which field was the problem.

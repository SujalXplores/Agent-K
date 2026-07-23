# Error 401: Unauthorized

A 401 means the request had no valid authentication at all - either the API key was omitted from the Authorization header, the key was revoked (see revoke-lost-api-key), or a session cookie has expired. This is distinct from 403, which means you ARE authenticated but lack permission for that specific action.

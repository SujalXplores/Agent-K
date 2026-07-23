# How does API pagination work?

List endpoints use cursor-based pagination. The response includes a ``next_cursor`` field — if it's null, you've reached the end. To get the next page, pass the cursor as a query parameter: GET /api/v1/items?cursor=abc123. The default page size is 20, and you can request up to 100 items per page using the ``limit`` parameter. We recommend using cursor-based pagination over offset pagination for large datasets as it's more performant and consistent.

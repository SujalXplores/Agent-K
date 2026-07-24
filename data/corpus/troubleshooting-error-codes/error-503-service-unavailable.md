# Error 503: Service unavailable

A 503 typically appears during planned maintenance windows (announced in advance on the status page) or brief auto-scaling events during traffic spikes. Unlike a 500, a 503 is Flowdeck deliberately signaling "temporarily can't serve this," and the response includes a Retry-After header just like a 429 - respect it before retrying.

If 503s persist for more than a few minutes outside an announced maintenance window, check the status page for an unplanned incident before assuming it's an issue on your integration's side.

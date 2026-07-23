# Can I restrict API access to specific IP addresses?

Yes, Enterprise plans support IP allowlisting for API access. Go to Settings > Developer > IP Allowlist and add the IP addresses or CIDR ranges you want to allow. When the allowlist is active, requests from any other IP address will receive a 403 Forbidden response. You can add up to 50 IP addresses or CIDR ranges. Changes take effect within 1 minute. This is independent of your API key — both the key and the IP must be valid.

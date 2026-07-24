# Restricting access with IP allowlisting

Enterprise workspaces can restrict login and API access to a specific set of IP ranges under Workspace Settings > Security > IP Allowlist. Requests from outside the allowlisted ranges are rejected at the edge with a 403 before reaching any application logic, including for members who would otherwise have valid credentials.

Configure the allowlist carefully before enabling enforcement - Flowdeck provides a 24-hour "test mode" that logs which requests would have been blocked without actually blocking them, so you can verify your CIDR ranges are correct (e.g. covering your office VPN egress IPs) before flipping enforcement on for real.

# Personal access tokens vs. service account API keys

A personal access token is tied to an individual member's account and permissions - if that member is offboarded, every integration using their personal token breaks immediately, which makes personal tokens a poor fit for long-lived automation.

A service account API key (available on Team and Enterprise plans) belongs to the workspace itself rather than any one member, so it keeps working regardless of staff turnover. Use service account keys for CI/CD pipelines, scheduled scripts, and third-party integrations; reserve personal access tokens for a member's own ad hoc scripting or local development use.

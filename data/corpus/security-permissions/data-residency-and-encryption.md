# Data residency and encryption at rest

Flowdeck workspaces are hosted in either the US or EU region, chosen at workspace creation time and not changeable afterward without a full data migration handled by support - if data residency is a compliance requirement, confirm the region before creating the workspace, not after.

All data is encrypted at rest using AES-256 and in transit using TLS 1.2+. Enterprise plans additionally support bringing your own encryption key (BYOK) via AWS KMS or Google Cloud KMS, giving you the ability to revoke Flowdeck's access to your data by disabling the key on your side.

#!/usr/bin/env bash
# Times `foundryctl cast` end-to-end and appends a timestamped duration row
# to docs/TELEMETRY-REBUILD-LOG.md (D-08, TELE-02).
#
# The timer wraps only the `foundryctl cast` invocation itself, not the
# one-time `foundryctl` binary install - per RESEARCH.md Open Question #1's
# budget boundary for what counts toward the 15-minute (900s) TELE-02 budget.
set -euo pipefail

START=$(date +%s)
foundryctl cast -f casting.yaml
END=$(date +%s)

DURATION=$((END - START))
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

printf "| %s | %ds |\n" "$TIMESTAMP" "$DURATION" >> docs/TELEMETRY-REBUILD-LOG.md
echo "Foundry cast completed in ${DURATION}s - logged to docs/TELEMETRY-REBUILD-LOG.md"

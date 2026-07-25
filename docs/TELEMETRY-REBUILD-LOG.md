# Telemetry Rebuild Log

Append-only, judge-verifiable rebuild-duration log for TELE-02. Each row is
produced by running `scripts/time-foundry-cast.sh`, which times
`foundryctl cast -f casting.yaml` end-to-end and appends the measured
duration - this is a real, measured number, not an assumed one.

> **Note:** Rows recorded here are same-machine cold-container measurements
> (stack torn down via `docker compose down`, then re-cast). The authoritative
> clean-machine measurement (fresh clone -> running SigNoz on a teammate's
> machine that has never run this repo before) is captured separately at the
> Day 5-6 clean-machine-rebuild gate, per the ROADMAP Phase 7 constraint.

| Timestamp (UTC) | Duration |
|---|---|
| 2026-07-23T11:58:56Z | 7s |

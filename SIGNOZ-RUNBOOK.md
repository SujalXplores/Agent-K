# SigNoz Runbook

This is the standup/reproduction runbook for the self-hosted SigNoz observability
backend used by Agent K. It is written for a team with **zero prior Docker/OTel/SigNoz
experience** — follow the steps in order, don't skip the precondition check.

## 0. Precondition: Docker Desktop memory (D-03)

Before any install attempt:

1. Confirm Docker Desktop (or Docker Engine + Compose v2) is installed and running:
   ```bash
   docker compose version   # must report a v2.x version, not v1 / not "command not found"
   ```
2. Raise Docker Desktop memory to **6-8GB**: Settings → Resources → Memory → set to
   6-8GB → Apply & Restart. This is a GUI-only setting; there is no CLI equivalent.
3. Confirm the new allocation took effect:
   ```bash
   docker info --format '{{.MemTotal}}'   # bytes, should be roughly 6-8 x 1024^3
   ```

**Why this matters:** SigNoz's official minimum is 4GB Docker memory, but ClickHouse
(SigNoz's storage backend) has been observed to segfault (Keeper exit code 139) under
real load at that floor on Docker Desktop defaults. Bumping to 6-8GB up front is a
five-minute fix that avoids the #1 flagged Day-1 pitfall. If ClickHouse Keeper still
segfaults after the bump, tune the allocation further at your discretion — there is no
hard ceiling documented, just "give it more."

## 1. Primary standup: Foundry gauge → forge → cast

Foundry is SigNoz's official deployment CLI. It runs a three-stage pipeline: validate
prerequisites, generate config, then deploy.

```bash
# Install foundryctl (once per machine)
curl -fsSL https://signoz.io/foundry.sh | bash
# If the script fails, download a manual binary for your platform from:
# https://github.com/SigNoz/foundry/releases

# casting.yaml already exists in the repo root — do not recreate it. Contents:
#   apiVersion: v1alpha1
#   metadata:
#     name: signoz
#   spec:
#     deployment:
#       mode: docker
#       flavor: compose

foundryctl gauge -f casting.yaml           # validates Docker + Compose v2 prerequisites
foundryctl forge -f casting.yaml -p ./pours  # generates pours/deployment/compose.yaml + casting.yaml.lock
foundryctl cast -f casting.yaml            # full pipeline: gauge + forge + `docker compose up -d`
```

Confirm the stack is up:

```bash
docker ps                          # should list signoz-signoz-0, clickhouse, keeper, ingester, postgres containers, all healthy
curl -sf http://localhost:8080     # should return HTTP 200 (SigNoz UI)
```

ClickHouse and the UI can take a little while to become healthy on first run (image
pulls + ClickHouse startup) — retry the `curl` with a short backoff before concluding
something is broken.

## 2. CORRECTED D-02 fallback (only if `cast` blocks past a short troubleshooting window)

**Important — do NOT follow older guidance that references pulling SigNoz's plain
`docker-compose.yaml` from the `SigNoz/signoz` repo.** That file was **removed
upstream as of SigNoz v0.130.0** — SigNoz's own migration docs confirm "SigNoz no
longer distributes these files." A team that tries to `git clone`/browse the current
`SigNoz/signoz` repo looking for `deploy/docker/clickhouse-setup/docker-compose.yaml`
will not find it, burning exactly the time the fallback exists to save. This is a
correction to D-02's literal mechanism, not a change to its intent (having *a*
fallback if Foundry blocks the team).

The corrected fallback: since `forge` already generated the compose file, deploy it
directly, bypassing `cast`'s orchestration layer to isolate whether the failure is in
`cast` itself or in the underlying compose config:

```bash
foundryctl forge -f casting.yaml -p ./pours   # if not already run — generates pours/deployment/compose.yaml
docker compose -f pours/deployment/compose.yaml up -d
docker compose -f pours/deployment/compose.yaml logs -f
```

This still uses Foundry (so the `casting.yaml`/`casting.yaml.lock` commit is trivial —
`forge` already produced the lock file), it just skips `cast`'s extra deploy logic.

## 3. Port-hardening caution (threat T-01-02)

SigNoz publishes these ports to the host by default:

- `8080` — SigNoz UI + query-service API
- `4317` / `4318` — OTLP ingest (gRPC / HTTP-protobuf; this project uses 4318 only per
  the locked HTTP/protobuf exporter decision)

**SigNoz ships with no UI authentication by default.** Keep these ports reachable on
`localhost` / the team's private network only for the duration of the hackathon. Do
**not**:
- Port-forward 8080 or 4318 to a public interface or a tunneling service (ngrok, etc.)
- Bind these ports to a cloud VM's public IP without a reverse proxy + auth in front

This is a documentation-level/procedural mitigation — Foundry's generated compose
config publishes ports on the container host's `0.0.0.0` interface by default (visible
via `docker port signoz-signoz-0` / `docker port signoz-ingester-1`), so the actual
exposure boundary is the host machine's own network/firewall, not the container
binding. Treat "which network is this laptop on" as the real control here.

## 4. Reproducibility note

- `pours/` is Foundry's generated output directory (compose files, resolved config,
  clickhouse/keeper/ingester config trees). It is **gitignored** — regenerable at any
  time via `foundryctl forge -f casting.yaml -p ./pours`. Do not commit it.
- Only `casting.yaml` (hand-authored) and `casting.yaml.lock` (Foundry-generated
  checksums for deterministic rebuild) are committed together — this is what makes a
  judge's clean-machine rebuild reproducible. Verify both are tracked:
  ```bash
  git ls-files casting.yaml casting.yaml.lock   # both must return non-empty
  ```

## 5. First-time UI check pitfall

SigNoz's Traces/Logs Explorer defaults to a **"Last 30 minutes"** rolling time window.
If you stand up the stack, wait a while, then check the UI and see nothing, this is
very likely the default window, not a telemetry delivery failure. Before concluding
OTLP delivery is broken:

1. Generate fresh traffic (e.g. `curl` a running service, or wait for the next
   auto-instrumented request).
2. Widen the Explorer's time range explicitly.
3. Check console-exporter stdout output first, if the emitting app also logs to
   console — if spans print locally but never show up in SigNoz within a widened
   window, that isolates a real delivery problem; if nothing prints locally, the
   app isn't generating spans at all (a different, upstream problem).

## Quick reference

| Task | Command |
|------|---------|
| Install foundryctl | `curl -fsSL https://signoz.io/foundry.sh \| bash` |
| Validate prerequisites | `foundryctl gauge -f casting.yaml` |
| Generate config only | `foundryctl forge -f casting.yaml -p ./pours` |
| Full standup | `foundryctl cast -f casting.yaml` |
| Fallback standup (D-02 corrected) | `docker compose -f pours/deployment/compose.yaml up -d` |
| Check stack | `docker ps` |
| Check UI | `curl -sf http://localhost:8080` |
| Tear down | `docker compose -f pours/deployment/compose.yaml down` |

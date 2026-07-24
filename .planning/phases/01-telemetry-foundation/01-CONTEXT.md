# Phase 1: Telemetry Foundation - Context

**Gathered:** 2026-07-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Stand up a self-hosted SigNoz observability backend via Foundry (`casting.yaml`/`casting.yaml.lock` committed to the repo), and prove that a minimal FastAPI skeleton service's traces, metrics, and logs are visible in the SigNoz UI — before any real RAG/agent application logic exists. Includes a console-exporter fallback so the team can debug the pipeline locally when OTLP delivery doesn't arrive, and a measured (not assumed) clean-machine rebuild time under 15 minutes.

</domain>

<decisions>
## Implementation Decisions

### SigNoz Install Path
- **D-01:** Attempt Foundry (`foundryctl gauge` → `forge` → `cast`) first — it is the only path that produces the judged `casting.yaml`/`casting.yaml.lock` deliverable.
- **D-02:** Time-box Foundry troubleshooting to 2-3 hours on Day 1. If it is still blocking the team past that point, fall back to SigNoz's plain `docker-compose.yaml` (from the `SigNoz/signoz` repo) to unblock instrumentation work immediately, then retrofit `casting.yaml`/`.lock` once the stack is stable. A working demo with a retrofitted Foundry config beats a broken demo with a "correct" install path (per CLAUDE.md's own documented fallback pattern).
- **D-03:** Before any install attempt, bump Docker Desktop memory allocation to 6-8GB — research flagged ClickHouse memory starvation as the top Day-1 pitfall, and this is a five-minute preventable fix.

### Skeleton Service Scope
- **D-04:** The "minimal FastAPI skeleton" (TELE-03) is built as a **real, reusable scaffold** — `app/main.py` with FastAPI + OpenTelemetry instrumentation wired correctly (FastAPI/SQLAlchemy/logging auto-instrumentation, OTLP exporter setup) — not a disposable smoke-test script. Phase 2 extends this exact scaffold with the real `/ask` endpoint and pgvector retrieval logic, rather than re-doing the OTel wiring from scratch.
- **D-05:** "Before any app logic is written" (the phase goal) means no `/ask` route or RAG logic yet — it does not mean the FastAPI service itself gets thrown away after this phase.

### Telemetry Exporter Strategy
- **D-06:** Run the console exporter and the OTLP exporter **simultaneously, always on** — no env-var toggle to switch between them. Silent OTLP delivery failures were research-flagged as the #1 Day-1 pitfall; always-on dual export means the team can immediately see from console output whether spans are being generated at all, independent of whether they're reaching SigNoz, without restarting or reconfiguring anything.
- **D-07:** Use `opentelemetry-exporter-otlp-proto-http` (HTTP/protobuf, port 4318) as the OTLP exporter, per the locked stack decision — not gRPC.

### Rebuild-Time Measurement
- **D-08:** Automate the TELE-02 rebuild-time measurement with a small wrapper script that times `foundryctl cast` end-to-end and appends the duration + timestamp to a `TELEMETRY-REBUILD-LOG.md` file in the repo. This produces a reproducible, judge-verifiable artifact instead of a manually-noted stopwatch time.

### Claude's Discretion
- Exact directory structure inside `app/` (e.g., `app/main.py` vs. `app/telemetry.py` module split) — plan/execute can decide based on what keeps the OTel setup code cleanly separated from future RAG logic.
- Whether the rebuild-timing wrapper script is a shell script or a short Python script — whichever is simpler given the team's tooling choices made during planning.
- Exact SigNoz Docker Compose resource limits beyond the 6-8GB Docker Desktop floor — fine-tune during setup if ClickHouse still struggles.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Technology stack, versions, and pitfalls
- `.claude/CLAUDE.md` — locked technology stack (Python/FastAPI/OTel/Foundry versions and rationale), "What NOT to Use" table (legacy `install.sh`, gRPC OTLP), and the Foundry-fallback stack pattern this phase's D-02 decision is based on
- `.planning/research/STACK.md` — full stack research backing CLAUDE.md's recommendations
- `.planning/research/PITFALLS.md` — Day-1 pitfalls (ClickHouse memory starvation, silent OTLP delivery failures) that directly informed D-03 and D-06
- `.planning/research/ARCHITECTURE.md` — overall system architecture context
- `.planning/research/SUMMARY.md` — synthesized research summary across all project-level research

### Requirements and roadmap
- `.planning/REQUIREMENTS.md` — TELE-01, TELE-02, TELE-03 full requirement text
- `.planning/ROADMAP.md` — Phase 1 success criteria and dependency notes (Phase 2 depends on Phase 1's skeleton service)
- `.planning/PROJECT.md` — project-level constraints (zero-budget, zero prior Docker/OTel/SigNoz experience, single monorepo layout)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
None yet — this is a greenfield repository. The only existing file outside `.claude/` and `.planning/` is `agent-k-gsd-prompt.md` (the original hackathon spec prompt).

### Established Patterns
None yet — no code exists. This phase establishes the first patterns (OTel instrumentation wiring, exporter configuration) that later phases will follow.

### Integration Points
The `app/` directory created in this phase is the direct foundation Phase 2 (RAG Service Core) builds on — its FastAPI app object, OTel setup, and instrumentation wiring must be structured so Phase 2 can add routes/dependencies without restructuring what this phase produces.

</code_context>

<specifics>
## Specific Ideas

No specific UI/behavioral references — this is an infrastructure/observability phase with no user-facing surface. The user explicitly deferred all four gray areas to Claude's recommendation given zero prior experience with Docker/OTel/SigNoz/Foundry, so the decisions above should be treated as the team's locked starting point rather than revisited mid-build unless something concretely breaks.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 1-telemetry-foundation*
*Context gathered: 2026-07-21*

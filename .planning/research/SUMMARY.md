# Project Research Summary

**Project:** Agent K — code-enforced incident-response agent + monitored FastAPI RAG service
**Domain:** AI-native observability/AgentOps hackathon build (AI incident-response agent + AIOps, evaluated via SigNoz/OpenTelemetry)
**Researched:** 2026-07-20
**Confidence:** MEDIUM

## Executive Summary

Agent K is a two-process, code-enforced incident-response system: a small FastAPI+pgvector RAG service (the "monitored app," seeded with four injectable failure scenarios) and Agent K itself, a plain-Python state-machine agent that receives SigNoz alerts, gathers evidence via the SigNoz MCP server, proposes a root-cause hypothesis, gates any remediation behind a deterministic non-LLM policy module (Law 2), verifies evidence resolves before publishing claims (Law 1), and emits its own investigation as first-class telemetry (Law 3). This is squarely in the emerging "AI SRE" product category (Datadog Bits, PagerDuty AIOps, incident.io, Honeycomb) — the locked feature set already matches or exceeds table stakes in that category, and its strongest wedge is doing in code what competitors only do via LLM prompting: a deterministic evidence-link checker and a policy gate with zero model involvement in the allow/deny decision.

The recommended approach is a fully-verified, single-OpenAI-compatible-client Python stack (FastAPI 0.139.2, SQLAlchemy 2.0 + asyncpg + pgvector, OpenTelemetry 1.44.0 with FastAPI/SQLAlchemy/logging auto-instrumentation, `sentence-transformers` for local embeddings, `mcp` SDK for SigNoz tool calls) deployed via SigNoz's Foundry CLI (`casting.yaml`/`.lock`), with no agent framework and no separate vector database — both explicitly rejected to keep Law 1/2/3 auditable and to respect the locked "single datastore" decision. Architecturally, the two processes share nothing but SigNoz (telemetry) and a single docker-compose file (the one narrow mutation surface for rollback) — this separation is what makes the whole safety story demonstrable rather than asserted.

The dominant risk is not feature complexity but team unfamiliarity: zero prior Docker/OTel/SigNoz experience against a hard 7-day deadline. The single highest-leverage mitigation is front-loading all "novel-to-the-team" infra work (SigNoz standup via Foundry, OTel wiring with a console-exporter fallback, MCP integration) into Day 1-2, before any Agent K logic is written, and treating "clean-machine rebuild under 15 minutes" as a Day 5-6 checkpoint rather than a submission-day assumption. Secondary risks (rollback executor correctness, loop-breaker/cost-watchdog undertesting, Groq rate limits colliding with the eval harness's batch pattern) are all addressable by building safety/guardrail code inline with the feature it guards, not as a late bolt-on.

## Key Findings

### Recommended Stack

The stack is fully version-pinned and PyPI-verified: FastAPI 0.139.2 + Uvicorn 0.51.0 on Python 3.11/3.12, Postgres+pgvector as the single datastore (SQLAlchemy 2.0.51 + asyncpg 0.31.0 + pgvector 0.5.0 + Alembic), OpenTelemetry 1.44.0 core with the `opentelemetry-instrumentation-{fastapi,sqlalchemy,logging}` contrib packages (all pinned to `0.65b0`) shipping OTLP/HTTP to SigNoz (self-hosted via Foundry's `foundryctl`). LLM access goes through a single `openai` Python SDK client with `base_url` swapped per provider (Groq primary, Cerebras/Gemini Flash as fallback) — no LiteLLM proxy, no provider-specific SDKs. `mcp` 1.28.1 is Agent K's client into the SigNoz MCP server (prefer Streamable HTTP transport over stdio to sidestep stdout-corruption and subprocess-lifecycle issues). `sentence-transformers` (`all-MiniLM-L6-v2`, swappable to `bge-small-en-v1.5`) provides local embeddings with zero external API cost.

**Core technologies:**
- FastAPI + Uvicorn — async web framework for both RAG service and Agent K, first-party OTel instrumentation
- PostgreSQL + `pgvector` — single datastore for docs+embeddings, avoids a second vector-DB surface
- OpenTelemetry SDK + OTLP/HTTP exporter — traces/metrics/logs from one SDK version, shipped to SigNoz
- `mcp` Python SDK (Streamable HTTP) — Agent K's evidence-query client into SigNoz's MCP server
- `openai` SDK (single client, swappable `base_url`) — one code path for Groq/Cerebras/Gemini Flash
- SigNoz via Foundry (`foundryctl` → `casting.yaml`/`.lock`) — self-hosted observability backend, judged deliverable

### Expected Features

Agent K's locked feature set already meets or exceeds AI-SRE table stakes (alert ingestion, hypothesis-driven investigation loop, structured final artifact, deployment correlation, cited evidence, human escalation, audit trail — all confirmed present at Datadog/PagerDuty/incident.io/Honeycomb). Its differentiators are precisely the "Three Laws": a code-enforced evidence-link checker (no competitor researched does this deterministically), a non-LLM policy gate before any action, verified-outcome rollback (re-query to confirm recovery, not assume it), and agent self-telemetry as a first-class dashboard surface. Feature scope is fully locked — no v2 backlog to negotiate — but research flags three coherence gaps worth resolving explicitly in requirements: (1) "escalation" is passive (report/dashboard reflects incomplete state) not an active page/notification; (2) whether the report page shows only the latest incident or a history across the 12 eval runs; (3) denied actions must be as visible in the audit trail as approved ones — arguably the stronger safety-story beat.

**Must have (table stakes, already locked):**
- Alert ingestion via SigNoz webhook, hypothesis-driven investigation loop, structured RCA artifact, deployment/change correlation, evidence citations, human escalation path, action audit trail

**Should have (differentiators, already locked):**
- Law 1 code-enforced evidence-link checker; Law 2 deterministic policy gate; verified-outcome rollback; Law 3 self-telemetry as a demoable dashboard surface; loop breaker + cost watchdog; hybrid (LLM-propose, code-recalibrate) confidence scoring

**Defer / explicitly out of scope (not v2 — permanently excluded per locked scope):**
- Multi-channel notifications (Slack/Jira/ServiceNow), alert correlation/dedup across many alerts, expanded remediation action catalog beyond one allowlisted rollback, fully autonomous "no human" remediation, general chat/Q&A interface, cross-service dependency-graph root-causing

### Architecture Approach

Two independent OS processes on one host, coupled only through SigNoz (telemetry) and a single docker-compose file (control) — no shared database, no framework coupling. Agent K's entire lifecycle is one explicit `State` enum with a deterministic transition table; the LLM proposes structured data (hypothesis, confidence, action) at specific code-chosen points but never decides control flow. Every SigNoz MCP call routes through one wrapper function that spans, hashes (for loop detection), and returns a structured `Evidence` object with a deep link — this single call-site is what makes Law 1 and Law 3 enforceable. The policy gate (Law 2) is a pure function with no model call inside it, sitting strictly between hypothesis and action.

**Major components:**
1. RAG Service (`rag-service/`) — FastAPI app serving `/ask`, retrieval (pgvector) + generation (Groq), feature-flag-gated failure injection, fully OTel-instrumented
2. Agent K state machine (`agent-k/app/statemachine/`) — RECEIVED→INVESTIGATING→HYPOTHESIZING→POLICY_CHECK→(ACTING|REPORTING)→VERIFYING→REPORTED, the only control-flow authority
3. MCP client wrapper (`mcp_client.py`) — single call-site for all SigNoz evidence queries, spans + loop-hashes every call
4. Policy module (`policy.py`) — pure function, allowlist/SLO/cooldown/confidence/deployment-relatedness checks, unit-testable with zero mocking
5. Rollback executor (`rollback.py`) — edits docker-compose.yml via PyYAML, `docker compose up -d` (never `restart`), post-recreate health check, deployment marker, re-query for recovery
6. Report Store + HTML renderer — structured RCA JSON with evidence-link checker enforced at render time, served as `/report/{id}`

### Critical Pitfalls

1. **SigNoz/ClickHouse starves on default Docker Desktop memory (2GB)** — bump to 6-8GB and confirm bare SigNoz + a synthetic trace on Day 1, before any app code.
2. **Traces silently never reach SigNoz** (wrong OTLP port/protocol, or instrumentation never fired) — always debug via console-exporter first, then switch to OTLP; keep the console-exporter toggle available for the whole build.
3. **`docker compose restart` doesn't pick up compose-file changes** — rollback executor must always use `up -d <service>` (recreate) and explicitly verify post-recreate container health before re-querying SigNoz for recovery.
4. **Mounting the Docker socket into a containerized Agent K grants host root**, directly undercutting the "sandboxed single action" claim — run Agent K as a host process instead, or document the containerized sandbox honestly as code-level only.
5. **Loop-breaker/cost-watchdog built last and never forced to fire** — build them alongside the first working investigation loop, and write at least one adversarial test that actually triggers each guardrail before eval day.

## Implications for Roadmap

Based on research (especially ARCHITECTURE.md's "Suggested Build Order" and PITFALLS.md's phase mapping), suggested phase structure:

### Phase 1: Telemetry Foundation (SigNoz + OTel skeleton)
**Rationale:** Nothing downstream is demoable or debuggable without telemetry flowing; this is also the team's biggest experience gap (zero Docker/OTel/SigNoz background) and needs the most ramp-up buffer.
**Delivers:** SigNoz running via Foundry (`casting.yaml`/`.lock` committed), a trivial FastAPI skeleton emitting traces/metrics/logs via console-exporter then OTLP, confirmed visible in SigNoz UI.
**Addresses:** Judged deliverable "Foundry deployment, casting.yaml + casting.yaml.lock committed."
**Avoids:** Pitfall 1 (ClickHouse memory starvation), Pitfall 2 (traces never reaching SigNoz).

### Phase 2: RAG Service Core
**Rationale:** Builds on working telemetry; this is the team's most familiar territory (web-tech background) but still needs pgvector + local embeddings wiring and full `gen_ai.*` instrumentation.
**Delivers:** `/ask` endpoint with pgvector retrieval + Groq generation, synthetic corpus (50-200 docs), single-OpenAI-compatible-client provider abstraction, shared `genai_span_attrs()` helper.
**Uses:** FastAPI, SQLAlchemy+asyncpg+pgvector, `sentence-transformers`, `openai` SDK (from STACK.md).
**Implements:** RAG Service component (retrieval + generation + OTel SDK).

### Phase 3: Failure Injection + Dashboard + Alerting
**Rationale:** Blocks everything downstream needing a real incident to investigate; also the last piece of "process 1's world" before Agent K exists.
**Delivers:** In-memory feature-flag service + 4 seeded failure scenarios, hand-built 4-section SigNoz dashboard, SLO/burn-rate alert rules, a webhook notification channel proven firing end-to-end.
**Addresses:** FEATURES.md P1 items (4-section dashboard); avoids Pitfall re: deployment markers being conflated with flag toggles (Anti-Pattern 2, ARCHITECTURE.md).

### Phase 4: SigNoz MCP Integration
**Rationale:** Isolated and parallelizable with Phase 3, but must land before Agent K's investigation logic can be written against real evidence rather than mocks.
**Delivers:** SigNoz MCP server running (HTTP/Streamable transport, not stdio/SSE), a throwaway script proving the `mcp` SDK can call it and get real evidence back.
**Avoids:** Pitfall 7 (MCP stdio stdout corruption, deprecated SSE transport).

### Phase 5: Agent K Core Loop (state machine + Law 1 evidence + Law 3 telemetry inline)
**Rationale:** Law 3 self-telemetry and loop-breaker/cost-watchdog must be instrumented inline, not retrofitted — this is a standing constraint on this phase, not a separate later phase. Law 1's evidence schema is a hard dependency of Law 2.
**Delivers:** Webhook receiver, state machine shell, single-call-site MCP client wrapper, structured claim/evidence schema with link checker, hybrid confidence recalibration, loop breaker + cost watchdog with at least one forced-trigger test.
**Addresses:** FEATURES.md P1 items (investigation loop, Law 1, Law 3); avoids Pitfall 4 (orphaned background-task spans — prefer sync/separate-process investigation over `BackgroundTasks`), Pitfall 9 (undertested guardrails).

### Phase 6: Policy Gate + Rollback Executor (Law 2)
**Rationale:** Requires a stable evidence/confidence shape from Phase 5; architecturally this is where the "one team member unavailable" scheduling risk bites hardest, so the policy schema should be drafted early.
**Delivers:** Pure-function policy module (allowlist/SLO/cooldown/confidence/deployment-relatedness), rollback executor using `docker compose up -d` with PyYAML edits, post-recreate health verification, verified-outcome recheck.
**Avoids:** Pitfall 5 (`restart` vs `up -d`), Pitfall 6 (Docker socket privilege escalation — decide host-process vs. containerized Agent K here).

### Phase 7: Report Page + Dashboard Polish + Evaluation Harness
**Rationale:** Terminal dependency — consumes artifacts (reports, telemetry) that only exist once Phases 1-6 work; the evaluation harness's rate-limit behavior must be tested before eval day, not on it.
**Delivers:** HTML incident report (Jinja2, deep links, denied-actions visible), polished dashboard (agent health, action audit trail sections), 3-runs-per-incident eval harness with paced/backoff-aware Groq calls and a proven Cerebras fallback.
**Avoids:** Pitfall 8 (Groq rate limits colliding with batch eval), Pitfall 10 (clean-machine rebuild not tested until too late — this checkpoint should actually be scheduled around Day 5-6, inside or overlapping this phase).

### Phase Ordering Rationale

- Telemetry-first ordering follows directly from ARCHITECTURE.md's dependency chain: SigNoz → RAG app → failure injection → dashboard/alerts → MCP → Agent K loop → policy/action → report/eval. Every later phase depends on an earlier one having working telemetry to query or act against.
- Law 1 (evidence) must precede Law 2 (policy) because the policy module gates on evidence/confidence data that doesn't exist until Law 1's schema is built — this is a hard dependency per FEATURES.md's dependency graph, not a scheduling preference.
- Infra-heavy phases (1, 3, 4) get disproportionate time buffer relative to their apparent size because the team has zero prior Docker/OTel/SigNoz experience (Pitfall 11) — this should be reflected explicitly in day allocations, not just phase ordering.
- Guardrails (loop breaker, cost watchdog) are folded into Phase 5 rather than deferred to a later phase specifically to avoid Pitfall 9 (safety code built last and never verified to actually fire).

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (Telemetry Foundation):** SigNoz Foundry/OTLP setup specifics were only web-search verified (LOW-MEDIUM confidence in STACK/PITFALLS) — confirm exact port/protocol/env-var behavior against the installed Foundry version before building.
- **Phase 4 (MCP Integration):** exact SigNoz MCP tool names/signatures and transport-mode config were only cross-verified across 2 sources; verify against the installed `signoz/signoz-mcp-server` version at build time (also confirm it's v0.118.0+ for alert-history tools per ARCHITECTURE.md).
- **Phase 5 (Agent K Core Loop):** GenAI semantic-convention attribute names are still experimental/evolving (PITFALLS.md Pitfall 3) — recheck the current OTel GenAI semconv registry before finalizing the shared attribute helper.
- **Phase 6 (Rollback Executor):** Docker-socket-vs-host-process architecture decision has security implications not obvious to a Docker-inexperienced team — worth explicit research/discussion before implementation, not just a code review catch.

Phases with standard patterns (skip research-phase):
- **Phase 2 (RAG Service Core):** FastAPI+pgvector+SQLAlchemy is a well-documented, HIGH-confidence (PyPI-verified) pattern.
- **Phase 7 (Report Page):** Jinja2 HTML rendering over a structured JSON schema is standard, low-risk web-tech territory matching the team's existing background.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | Package versions verified live against PyPI (HIGH); ecosystem/behavioral claims (SigNoz OTLP conventions, Foundry workflow) web-search only (LOW), flagged per-row in STACK.md |
| Features | MEDIUM | Vendor blogs/docs cross-checked across 2+ sources per claim; some 2026 trend-roundup aggregator sites downgraded to LOW and excluded unless corroborated |
| Architecture | MEDIUM | SigNoz MCP tool surface cross-verified across 2 sources; most implementation specifics are single-source WebSearch synthesis — directionally correct, verify exact APIs at build time |
| Pitfalls | MEDIUM | Cross-checked against SigNoz/OTel official docs and GitHub issues (MEDIUM); generic hackathon-process advice flagged LOW and not load-bearing |

**Overall confidence:** MEDIUM

### Gaps to Address

- **Exact SigNoz MCP tool names/signatures and minimum SigNoz version** (needs v0.118.0+ for alert-history tools per ARCHITECTURE.md) — verify against the actually-installed Foundry/SigNoz version early in Phase 1/4, don't assume.
- **Current OTel GenAI semantic-convention attribute names** — still experimental as of research date; re-verify against `opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/` directly before writing the shared attribute helper, don't trust a first-found blog example.
- **Passive vs. active escalation, report history vs. single-latest, denied-action visibility** (FEATURES.md's three flagged coherence gaps) — these are clarifications within the existing locked scope that requirements/roadmap should resolve explicitly rather than leave implicit, to avoid the demo script or eval harness assuming behavior that wasn't built.
- **Clean-machine rebuild timing under 15 minutes** — currently untested; must be measured (not inferred from Foundry's idempotency guarantees) no later than Day 5-6, with enough slack to cut scope (smaller embedding model, pre-baked corpus) if it fails.
- **Groq free-tier rate limits vs. the 12-run eval harness batch pattern** — must be tested with the harness's real call pattern before final eval day, with Cerebras fallback proven working in advance, not assumed.

## Sources

### Primary (HIGH confidence)
- PyPI JSON API (live version checks for fastapi, uvicorn, sqlalchemy, asyncpg, pgvector, sentence-transformers, opentelemetry-*, openai, litellm, mcp, alembic, pydantic) — checked 2026-07-20

### Secondary (MEDIUM confidence)
- [SigNoz MCP Server — GitHub](https://github.com/SigNoz/signoz-mcp-server) and [AI Assistant Integration Guide](https://signoz.io/docs/ai/signoz-mcp-server/) — cross-verified against each other
- [SigNoz/foundry GitHub repo](https://github.com/SigNoz/foundry) and [Introducing SigNoz Foundry blog](https://signoz.io/blog/introducing-signoz-foundry/) — Foundry CLI workflow
- [OpenTelemetry GenAI Semantic Conventions registry](https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/) — official but experimental/evolving
- [SigNoz GitHub issues #6750, #5735, #7091, #10106, #10591] — OTLP/webhook/alert configuration gotchas, official repo
- [Datadog Bits AI SRE](https://www.datadoghq.com/product/ai/bits-ai-sre/), [PagerDuty AIOps](https://www.pagerduty.com/platform/aiops/), [Honeycomb Canvas](https://www.honeycomb.io/platform/canvas), [incident.io feature analysis](https://incident.io/blog/5-best-ai-powered-incident-management-platforms-2026) — competitor feature landscape
- [Groq Rate Limits — official docs](https://console.groq.com/docs/rate-limits)
- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)

### Tertiary (LOW confidence)
- SigNoz blog posts on FastAPI/OTel implementation specifics — single-source, verify against installed versions
- Docker Compose rollback community discussions (blogs, forums) — no authoritative single source
- LLM agent guardrail academic literature (AgentSpec, ShieldAgent) — used only to confirm Law 2 design direction, not as implementation reference
- Generic hackathon time-management advice — supporting context only, not load-bearing

---
*Research completed: 2026-07-20*
*Ready for roadmap: yes*

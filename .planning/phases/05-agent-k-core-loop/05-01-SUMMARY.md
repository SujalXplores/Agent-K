---
phase: 05-agent-k-core-loop
plan: 01
status: complete
requirements-completed: [INV-01, INV-02, INV-03, LAW1-01, LAW1-02, LAW1-03, LAW1-04, LAW1-05, LAW3-01, LAW3-02, LAW3-03, LAW3-04, LAW3-05, LAW3-06]
# INV-03's live/real-LLM diagnosis and LAW1-04/LAW1-05's live-alert-payload-shape and
# live-link-resolution halves are human-verification (no SigNoz stack/MCP server/LLM
# key in this environment) - see "What's not done" below.
key-files:
  created:
    - app/claims.py
    - app/investigation.py
    - scripts/check_evidence_links.py
    - tests/test_claims.py
    - tests/test_investigation.py
    - tests/test_check_evidence_links.py
  modified:
    - app/observability.py
    - app/alerts_webhook.py
completed: 2026-07-24
---

# Phase 5 Plan 01: Investigation State Machine, Law 1 Evidence, Law 3 Self-Telemetry

**Built Agent K's core investigation loop end to end: a plain Python state machine
(no agent framework) that receives an alert, gathers SigNoz evidence via the Phase-4
MCP wrapper, forms evidence-backed hypotheses via the Phase-2 LLM client, and reaches
a terminal REPORTED/ESCALATED state — with Law 1's evidence schema, Law 3's
self-telemetry, loop breaker, and cost watchdog all instrumented inline and proven
to actually fire, not just exist unexercised in code.**

## Design decisions (made directly, no discuss-phase — documented here instead)

- **Cost watchdog budgets on TOKEN COUNT, not USD.** `app/observability.py`'s
  `AGENTK_LLM_ESTIMATED_COST_USD` is deliberately pinned to `$0.0` for the locked
  free-tier providers (Groq/Cerebras/Gemini Flash) — a USD budget could never fire.
  `TOKEN_BUDGET = 20_000` (input+output tokens per investigation) is the practical,
  always-nonzero proxy the requirement's "token/cost usage" wording explicitly allows.
- **Evidence queries vary per iteration, not repeat.** `EVIDENCE_QUERY_PLAN` (traces →
  logs → metrics) gives each of the 3 iterations a distinct query, so a normal
  multi-iteration investigation never spuriously trips the loop breaker — only a
  genuine bug/adversarial repeat does. `MAX_ITERATIONS` is pinned to the plan's length
  (3) for exactly this reason.
- **`start_investigation` is fire-and-forget** (`asyncio.create_task`), so the webhook's
  HTTP response is never blocked on a multi-second investigation. `run_investigation`
  itself catches any unexpected exception and converts it into an incomplete
  `ESCALATED` state — an investigation always reaches a terminal state and is always
  recorded, never silently dropped.
- **Span links (LAW1-04) use a documented CONVENTION, not a confirmed live schema:**
  `_extract_incident_span_context` looks for `trace_id`/`span_id` hex strings in the
  alert's labels/annotations. SigNoz's real Alertmanager-shaped webhook payload's
  actual field names for this are unconfirmed in this environment — flagged below.
- **Evidence link URL paths** (`build_evidence_link`) follow SigNoz's publicly
  documented UI route conventions (`/trace/{id}`, `/logs/logs-explorer?...`,
  `/metrics-explorer?...`) but are not live-verified.

## Accomplishments

- **`app/claims.py`** (LAW1-01/02/03): `Evidence`/`Claim` Pydantic models;
  `strip_unevidenced_claims()` — the report-renderer-side backstop removing any claim
  with empty evidence; `recalibrate_confidence()` — code-based hybrid scoring (LLM
  proposes, code recalibrates via deployment-marker boost, per-evidence-item boost
  capped at 4 items, error-rate-delta boost, all clamped to [0,1]); `build_evidence_link()`.
- **`app/investigation.py`** (INV-01/02/03, LAW1-04, LAW3-01..06): `InvestigationState`
  enum (RECEIVED/INVESTIGATING/REPORTED/ESCALATED); `Investigation` dataclass +
  in-process store (`get_investigation`/`list_investigations`/`clear_investigations`,
  mirrors `alerts_webhook`'s `_alerts` pattern); `run_investigation()` drives up to 3
  iterations of gather-evidence (via `signoz_mcp.query_signoz`, MCP-02's single call
  site) → form-hypothesis (via `llm_module.generate`, the Phase-2 single LLM client),
  stopping early on high confidence (≥0.75), loop-breaker firing (>3 repeats of an
  identical query hash), or cost-watchdog firing (>20k tokens); `start_investigation()`
  is the fire-and-forget entrypoint. The `agentk.investigation` span carries duration,
  MCP query count/failures/repeats, hypothesis count, total tokens, state, incomplete
  flag (LAW3-01/02/03); `agentk.hypothesis` spans carry LLM-proposed vs. recalibrated
  confidence; `agentk.watchdog.loop_breaker`/`agentk.watchdog.cost_budget` spans record
  each watchdog firing.
- **`app/alerts_webhook.py`**: `receive_alert` now calls
  `investigation.start_investigation(alert)` per alert after persisting it (INV-01).
- **`scripts/check_evidence_links.py`** (LAW1-05, code half): `check_links(urls)` HTTP-
  checks a list of evidence links and reports resolved/failed; `collect_links_from_investigations()`
  gathers every evidence link across every in-process investigation's claims.
- **Tests**: `tests/test_claims.py` (15), `tests/test_investigation.py` (18, incl. an
  adversarial repeated-query test that forces the loop breaker to actually fire and a
  forced-token-overrun test that forces the cost watchdog to actually fire — both
  asserted via real emitted spans, not just code presence — plus all 4 seeded incident
  types each producing a hypothesis), `tests/test_check_evidence_links.py` (6, via an
  `httpx.MockTransport`, no real network).

## Verification

- New tests: 39 passed (15 + 18 + 6).
- Full offline suite: **97 passed, 1 skipped** (integration), no regressions —
  confirms the webhook wiring doesn't break existing `/alerts/webhook` tests even
  though `receive_alert` now schedules a real background investigation (which fails
  gracefully at the MCP-connection step in this sandboxed environment — no live MCP
  server binary — short-circuiting before any LLM call is attempted, so no
  `GROQ_API_KEY` is needed for the existing webhook tests to stay green).
- Grep-confirmed: `signoz_mcp.query_signoz` has exactly one caller
  (`app/investigation.py`'s evidence-gathering step, alongside its own single
  `.call_tool(` call site from Phase 4); `llm_module.generate` has exactly two callers
  (`/ask` and the investigation's hypothesis step — expected, since RAG-04's "one
  client module" constraint is about client construction, not call-site count).
- All app modules re-import together cleanly (no circular import; `investigation.py`
  imports `AlertItem` from `alerts_webhook.py` only under `TYPE_CHECKING` to avoid the
  cycle since `alerts_webhook.py` imports `investigation` at runtime).

## What's not done — human verification (mirrors the HV pattern from Phases 2-4)

This environment has no live SigNoz stack, no SigNoz MCP server binary, and no LLM
provider credential, so the following remain live-verification gaps, all offline-tested
at the plumbing level but not provable end-to-end here:

1. **INV-03's real diagnosis quality** — the state machine correctly carries evidence
   into a hypothesis for all 4 seeded incident types (offline-proven with mocked
   evidence/LLM responses), but whether a real Groq completion correctly diagnoses a
   real seeded incident is Phase 7's EVAL-01 concern, not provable here.
2. **LAW1-04's span-link field convention** — `_extract_incident_span_context`'s
   `trace_id`/`span_id` label lookup is a documented assumption; the real SigNoz alert
   payload's actual carrier field(s) need confirming against a live alert.
3. **LAW1-05's "100% resolve" claim** — `check_links`/`collect_links_from_investigations`
   are built and offline-tested; running them against real evidence links from a live
   SigNoz instance is the live-verification step.
4. **`EVIDENCE_QUERY_PLAN`'s tool names** (`query_traces`/`query_logs`/`query_metrics`)
   are plausible guesses at the real SigNoz MCP server's tool list (same gap flagged in
   Phase 4 for MCP-01) — need confirming once a live server is reachable.

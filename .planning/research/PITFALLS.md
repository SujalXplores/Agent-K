# Pitfalls Research

**Domain:** Evidence-first AI incident-response agent (FastAPI + OTel + SigNoz + SigNoz MCP + OpenRouter free-tier LLMs), built in a locked 7-day hackathon window (2026-07-20 → 2026-07-26)
**Researched:** 2026-07-20
**Confidence:** MEDIUM-HIGH (OpenTelemetry/FastAPI/SigNoz/OpenRouter mechanics verified via official docs and multiple independent sources; SigNoz MCP tool-level and Foundry lock-file behavior partially inferred from repo docs, flag as MEDIUM; free-model-specific behavior is inherently volatile, flag as MEDIUM-LOW and re-verify on Day 1)

This file is ranked by **expected damage to the locked 7-day plan**, not by topic. The first five pitfalls can each independently sink the project (empty eval matrix, fabricated evidence, or a dead demo). Everything after that is real but recoverable if caught early.

---

## Critical Pitfalls

### Pitfall 1: OpenRouter's free-tier daily request cap silently caps the entire evaluation matrix

**What goes wrong:**
An OpenRouter account that has never purchased $10+ in credits is capped at **50 free-model requests/day total** (all `:free` models share this pool) and **20 requests/minute**. The eval plan is 4 incidents × 3 runs = 12 investigations, each investigation making a fixed but non-trivial set of MCP-informed LLM calls (hypothesis generation, evidence validation reasoning, policy-input summarization, report generation — likely 5-15 calls per investigation once retries are counted). That is 60-180+ chat-completion calls, plus every embedding call for the RAG app's own traffic and any seeded-incident traffic that touches the LLM. **This blows through 50/day before the eval matrix is even collected once**, and failed/rate-limited attempts still count toward the quota. This is invisible until the second or third investigation of the day starts silently failing or truncating.

**Why it happens:**
The 50/day ceiling is not prominently surfaced in OpenRouter's playground UX, and hackathon teams typically only discover it when a live demo run returns 429s mid-investigation — often on demo day itself, with no quota reset for hours.

**How to avoid:**
- On Day 1, before writing any agent code, add **$10 in OpenRouter credits** (raises the cap to 1,000 requests/day permanently — the cap is unlocked by lifetime purchase, not remaining balance). This is the single highest-leverage $10 the team will spend all week.
- Instrument a running per-day request counter from Day 1 so the team has ground truth on real consumption, not a guess.
- Design the investigation pipeline to use the **fewest possible LLM calls per stage** (one hypothesis call, not a chain of five) — this also serves Law 3's cost/latency story.
- List 2-3 free-model fallbacks in the `models` array of every request (OpenRouter's documented pattern) so a single model's outage/rate-limit doesn't stall a run — but see Pitfall 6 for why this must not corrupt cost accounting.

**Warning signs:**
- Any 429 response from OpenRouter during local testing, even once.
- Eval harness runs that complete fewer than the expected N tool/LLM calls per investigation.
- OpenRouter dashboard showing daily usage climbing before the eval matrix has been run even once.

**Phase to address:**
Day 1 (infrastructure/account setup) — this must happen before Day 3 agent-core work starts, and must be re-verified before the Day 6 eval matrix run and again the morning of the Day 7 demo.

---

### Pitfall 2: The agent's default reasoning model (`gpt-oss-20b:free`-class model) has documented tool-calling and structured-output drift

**What goes wrong:**
Open-weight ~20B models in the gpt-oss family have multiple independently reported failure modes in production use: tool calls emitted as free text inside a reasoning block instead of a proper `tool_call` structure, malformed JSON after an otherwise-correct structured output, and models that "keep going" past the end of a JSON object requiring defensive parsing. For a project whose core thesis is "a renderer that deletes unsupported claims is a guarantee, not a request," a model that inconsistently emits valid tool calls or valid JSON directly threatens Law 1 (evidence schema) and Law 2 (policy gate inputs) — not as an occasional bug, but as a structural risk baked into the model choice.

**Why it happens:**
Free/open-weight models optimized for benchmark scores are not uniformly trained on strict function-calling/JSON-mode fidelity the way flagship closed models are, and serving-stack differences (vLLM, provider-specific routing on OpenRouter) introduce additional variance on top of the model's own weaknesses.

**How to avoid:**
- Treat structured-output/tool-call parsing as **untrusted input from Day 1**: validate every LLM response against the schema in code (this is already the project's stated posture for evidence — extend the same discipline to policy-input extraction and hypothesis structuring).
- On any schema validation failure, **do not silently retry-and-hope** — retry once with a stricter re-prompt ("your last response was not valid JSON matching schema X, return only valid JSON"), then fail the stage explicitly and route to escalation. A visible "the model failed to produce valid evidence" is on-thesis; a silently-corrected fabrication is not.
- Confirm the documented fallback (`cohere/north-mini-code:free` per the project's own key decisions) actually works for structured output *before* Day 5, not as a break-glass measure discovered live during the demo.
- Prefer OpenRouter's `structured_outputs`/JSON-schema request mode (where the provider supports it) over prompt-only "please return JSON" — schema-mode is enforced server/inference-side on models that support it, prompt-only JSON is not.

**Warning signs:**
- Any JSON parse failure or missing `tool_calls` field during local dry runs of incidents 1-4.
- Hypothesis or evidence objects with mismatched field names/types slipping through without raising.
- The agent producing an RCA claim without a preceding successful structured evidence-validation pass.

**Phase to address:**
Day 3 (agent core / Law 1 evidence pipeline) for schema validation; Day 5 (Law 3 self-telemetry) to log every schema-validation failure as its own telemetry event so the failure rate is visible and reportable, not hidden.

---

### Pitfall 3: OpenTelemetry silently drops the exact telemetry the project's audit-trail claim depends on

**What goes wrong:**
Three independent OTel failure modes compound for this project, and all three fail *silently* — the app keeps running, no exception is raised, nothing shows up in SigNoz:
1. **Wrong endpoint/protocol.** Sending gRPC-formatted OTLP to the HTTP port (4318 vs 4317), or appending `/v1/traces` to a gRPC endpoint, produces no visible error — just missing data.
2. **BatchSpanProcessor + short-lived process.** The default batch processor flushes every 5 seconds or on batch-full. Any code path that exits quickly — a CLI eval-harness script that runs an investigation and exits, the rollback-executor sidecar handling a single `POST /rollback` and returning — can exit before the batch flushes, silently dropping the investigation spans and policy-verdict spans that are the entire Law 2/Law 3 evidence trail.
3. **Exporter auth/network failures logged at WARNING**, which is routinely filtered out or ignored in demo-mode logging configs.

For this project specifically, #2 is the most dangerous: the investigation pipeline is a discrete, code-driven run (not a long-lived request handler), which is exactly the shape of process that loses spans on exit.

**Why it happens:**
The OTel SDK's `atexit` hook is registered by default but does not cover SIGTERM (relevant if the eval harness or rollback sidecar is stopped by a container orchestrator rather than exiting normally), and developers assume "the SDK auto-flushes" without checking which processor is configured.

**How to avoid:**
- Explicitly call `tracer_provider.force_flush()` (and the equivalent for the meter/logger providers) at the end of every investigation run and at the end of the rollback executor's request handler — do not rely on process exit.
- Use `SimpleSpanProcessor` (or an explicit flush-after-every-investigation pattern) for any component that is not a long-lived server, even though `BatchSpanProcessor` is correct for the FastAPI app itself.
- Verify OTLP endpoint/protocol pairing explicitly in a startup self-check: confirm exporter port matches protocol (4317 = gRPC, 4318 = HTTP/protobuf), and log a clear ERROR (not WARNING) if the exporter's first flush fails.
- Add a Day 1 smoke test: emit one span, force-flush, and assert it is queryable in SigNoz via the MCP `signoz_search_traces` tool within N seconds — run this smoke test again after every significant OTel config change, not just once.

**Warning signs:**
- Investigation completes and produces a report, but SigNoz shows zero or partial spans for that investigation's trace ID.
- Rollback executor logs "rollback succeeded" but the policy-verdict span or post-action verification span is missing from SigNoz.
- Any discrepancy between "number of investigations run" (app-side counter) and "number of investigation root spans" (SigNoz query) — this discrepancy should be a CI/smoke-test assertion, not something discovered during the demo.

**Phase to address:**
Day 1 (OTel wiring) for the endpoint/protocol self-check; Day 4-5 (rollback executor, Law 3 self-telemetry) for explicit force-flush on every short-lived component, verified by the Day 6 eval harness before trusting any recorded run.

---

### Pitfall 4: The safety gate gets hand-tuned to hit 2-allow/2-deny instead of being correct by construction

**What goes wrong:**
Under time pressure on Day 4-5, the natural failure mode is: build the six-check policy gate, run incidents 1-4, notice the gate approves the wrong incident (e.g., denies incident 1 or approves incident 3), and then adjust a threshold (confidence cutoff, SLO margin) *specifically until the observed four incidents produce the target 2/2 split*. This produces a policy that is fit to four data points rather than a policy whose checks are independently correct — exactly the "tuned by hand at the last minute" trap. A judge who varies incident parameters even slightly, or asks "what would the gate do on a fifth scenario," will expose this immediately, and it directly undermines the project's central thesis (code-enforced law, not vibes).

**Why it happens:**
With only four fixed scenarios and a hard deadline, iterating on thresholds against the visible outcome is far faster than deriving each check's correct behavior independently — and the four incidents were designed by the same team that's tuning the gate, so it's easy to unconsciously reverse-engineer the answer.

**How to avoid:**
- **Specify each of the six checks independently, in isolation, before running any incident end-to-end.** Write each check (SLO breach, allowlist, cooldown, confidence, deployment-related cause, sandbox) as a pure function with its own unit tests using *synthetic* inputs unrelated to incidents 1-4 (e.g., "confidence=0.4 with threshold=0.7 → deny," "confidence=0.9 with threshold=0.7 → pass") before the first real incident is ever run through the gate.
- Build a **decision table** (input combination → expected verdict) as a design artifact on Day 4, before implementation — this is the standard pattern for deterministic policy engines and makes the "why did it deny this" question answerable by pointing at a row, not by re-reading code.
- Design incidents 1-4 so each one is expected to fail or pass **a different check** (e.g., incident 3 denies specifically on the deployment-related-cause check, incident 4 denies specifically on confidence) — this makes the 2/2 split a structural property of the incidents' design, not a tuned threshold, and makes each denial explainable in one sentence during the demo.
- Treat "the gate produced the wrong verdict on incident N" as a bug in the incident's seeded telemetry or in one specific check's logic — fix that check's isolated unit test, not the incident's numeric knobs, and not the threshold used only to pass this incident.
- Re-run the full six-check gate against a fifth, never-designed-for scenario (even a trivial made-up one) before Day 7 to confirm it isn't overfit to exactly four cases.

**Warning signs:**
- Any commit message or debugging session that changes a threshold value while looking at incident-specific output rather than a unit test.
- A check that has no unit test independent of the four seeded incidents.
- Inability to state, for each of the four incidents, *which single check* is expected to be the deciding factor, before running the incident.

**Phase to address:**
Day 4 (policy gate design, before implementation) for the decision table and per-check unit tests; Day 6 (incident eval runs) only to *verify* the pre-specified behavior, never to *derive* it.

---

### Pitfall 5: Computed cost (from a price table) reads as fabricated numbers to a judge unless the methodology is loudly disclosed

**What goes wrong:**
Because free-tier models bill $0, the project computes cost from local token counts × a configured price table. Two things can make this look dishonest rather than principled: (1) presenting a dollar figure in the dashboard/report with no visible indication it's computed rather than billed, inviting the judge to assume it's real spend and then feel misled when they learn otherwise; (2) the token counts themselves being wrong — streaming responses only include a `usage` block if `stream_options.include_usage=True` is explicitly set, and if it's omitted, "no usage reported" can be silently treated as "zero cost" rather than "unknown, do not report."

**Why it happens:**
`stream_options.include_usage` is opt-in and easy to miss when wiring a streaming client; and once the cost watchdog and dashboard exist, it's tempting to present "$X.XX" without a footnote because the plain number reads better in a demo.

**How to avoid:**
- Explicitly set `stream_options={"include_usage": True}` (or the non-streaming equivalent) on every OpenRouter chat/embedding call and treat a missing `usage` field as an **error to log and surface**, not as zero cost — a cost watchdog that silently treats missing data as $0 defeats its own purpose (Law 3).
- Label every cost figure in the dashboard, report, and blog with a visible "(computed from token counts × configured price table, not billed — free-tier models return $0 provider cost)" — this is already the project's own Key Decision; the risk is only in execution/UI, not in the design. Make the disclosure appear next to every number, not once in a README nobody opens during the demo.
- Where possible, cross-check locally-counted tokens against the provider-reported `usage.prompt_tokens`/`usage.completion_tokens` field when present, and log (not silently reconcile) any discrepancy — this becomes a credibility asset ("we noticed X, here's how we handled it") rather than a liability if it appears in the honesty-postured blog.
- Pick a price table sourced from a real provider's public pricing for the *paid* equivalent of each free model (or the closest comparable model), and cite the source next to the table — an unsourced price table looks arbitrary; a cited one looks deliberate.

**Warning signs:**
- Any code path where `usage` is `None`/missing and cost silently computes as 0 rather than raising/flagging.
- Dashboard panels showing a dollar amount with no adjacent note about methodology.
- Cost watchdog logic that can be satisfied by a run that had no usage data at all (a `None`-tolerant comparison is a bug, not a feature).

**Phase to address:**
Day 2-3 (OTel GenAI instrumentation, per-LLM-call telemetry) for streaming/usage capture; Day 5 (Law 3 cost watchdog) for the missing-usage error path; Day 7 (dashboard/blog polish) for visible disclosure everywhere a number appears.

---

### Pitfall 6: Retry/fallback logic for flaky free models corrupts cost accounting and defeats the loop breaker

**What goes wrong:**
The project needs retries to survive free-tier flakiness (Pitfall 1, Pitfall 2) but also has a loop breaker that "hashes MCP queries and halts on excessive repetition." Two failure modes collide: (a) a naive retry loop that re-issues the *same* LLM call on a 429 or malformed-JSON response will look identical to a genuine reasoning loop to a hash-based repetition detector, tripping the watchdog on a healthy run; (b) OpenRouter's stated policy is that failed/fallback attempts aren't billed, but real-world reports show 429s and partial outputs occasionally do consume quota or get billed anyway — if the cost watchdog naively sums "attempted calls × price" rather than "successfully completed calls × price," a rate-limit storm inflates the computed cost figure and can trip the cost watchdog on a run that did no useful work, or (worse) under-report if failed attempts are silently excluded when they shouldn't be.

**Why it happens:**
Retry logic and loop-detection logic are usually built by different mental models ("keep trying until it works" vs. "the same thing happening twice is suspicious") and nobody reconciles them until they collide live.

**How to avoid:**
- Distinguish, in the telemetry schema itself, between an **MCP query hash** (used by the loop breaker — this should key on investigation *intent*, e.g., normalized query text/params, and should only count semantically-repeated queries, not raw retries of a single failed attempt) and a **retry counter** (used for reliability, exempted from loop-breaker accounting up to a small fixed retry budget, e.g., 2 retries per call).
- Only count a call toward cost once it returns a response with usable `usage` data — track attempted vs. billed calls as separate metrics, and only the billed metric feeds the price-table cost sum.
- Cap retries per LLM call (e.g., 2) and per investigation (e.g., 5 total retries budget) — exceeding either is itself a watchdog-worthy event (log it, escalate), not something to retry indefinitely.
- Write a unit test that simulates 3 consecutive 429s on the same call and asserts: (1) the loop breaker does not fire, (2) the cost total does not include the failed attempts, (3) the investigation either succeeds on the next attempt or fails explicitly with a clear reason.

**Warning signs:**
- Loop breaker firing during a run that only hit rate limits, not a genuine repeated-query pattern.
- Computed cost changing between two runs of the *same* incident with identical outcomes, purely because one run needed more retries.
- Any place in the code where "call attempted" and "call billed" are the same counter.

**Phase to address:**
Day 5 (Law 3 — loop breaker and cost watchdog) — design the retry/loop-breaker/cost-accounting interaction explicitly before wiring any of the three in isolation; verify with the Day 6 eval harness under artificially injected 429s.

---

### Pitfall 7: SigNoz self-host stack + app dependencies threaten the sub-15-minute clean-machine rebuild target

**What goes wrong:**
SigNoz's own Docker Compose bundle (ClickHouse + ZooKeeper + frontend/backend + OTel Collector) documents a 2-5 minute first-start just for ClickHouse schema initialization, before any application container, image pull, or `pip install` time is added. Layer on: pulling all container images on a clean machine (variable, network-dependent), Python dependency installation, Postgres+pgvector image pull and extension init, seed-data loading, and Foundry's own `gauge`/`forge`/`cast` pipeline — and the 15-minute budget is tight even before anything goes wrong. The project's own Key Decision to avoid local embedding models (no torch/sentence-transformers) is the right call for exactly this reason, but it only removes one risk, not all of them.

**Why it happens:**
Individually, each component's startup time looks acceptable in isolation during development (services stay warm, images stay cached) — the risk only becomes visible on a genuinely clean machine, which is rarely tested until submission day.

**How to avoid:**
- Time a **real clean-machine rebuild** (fresh VM or `docker system prune -a` + no pip cache) no later than Day 5, not Day 7 — this needs at least one iteration cycle to fix, and fixing it late means fixing it under demo-prep pressure.
- Pre-pull and document exact image tags in `casting.yaml`/compose files (no `:latest`) so rebuild time is dominated by network transfer, not resolution/build steps.
- Keep seed data volume deliberately small (the four incidents need enough realistic history to be convincing — see Pitfall 8 — but "enough for a demo" is a few hundred to low-thousands of rows, not a large synthetic corpus).
- Budget Foundry's `gauge` step explicitly — it's designed to fail fast on missing tools, which is good, but only if the clean machine actually has Docker/Compose pre-installed; document exact prerequisite versions in the README so a judge's environment doesn't fail at `gauge` itself.
- Confirm `casting.yaml.lock` is committed and actually reflects the deployed config — treat any drift between `casting.yaml` and its lock file as a rebuild-breaking bug, and regenerate the lock file as a required last step before every commit that touches deployment config.

**Warning signs:**
- Rebuild time measurements that were only ever taken on a machine with warm Docker layer cache.
- `casting.yaml.lock` older than the most recent `casting.yaml` commit.
- Any dependency (Python, model, image) with an unpinned or `:latest`/`:main` version.

**Phase to address:**
Day 1 (initial Foundry/Docker Compose setup) for pinning; Day 5 (mid-week checkpoint) for the first real clean-machine timing test; Day 7 for the final verified rebuild immediately before submission.

---

## Moderate Pitfalls

### Pitfall 8: Seeded incidents produce telemetry too clean to be convincing, or fail to actually breach their target SLO

**What goes wrong:**
A hand-scripted fault injection (e.g., `asyncio.sleep(N)` before a DB call, a hardcoded retry-storm counter) tends to produce suspiciously uniform latency/error patterns — no jitter, no background noise, error spikes that start and stop on exact second boundaries — which reads as synthetic to anyone who has looked at real production telemetry, including the judges. Separately, an incident can be implemented but simply not move the metric it's supposed to breach: a retry-storm designed to blow a cost SLO might not generate enough token volume in a short demo window to cross the configured threshold, or a latency injection implemented as a delay in the wrong layer (e.g., delaying the FastAPI handler broadly instead of the specific retrieval span) shows up as generic request latency rather than as "retrieval latency" — which breaks the evidence chain the agent is supposed to cite (Law 1) even if the user-facing symptom is technically present.

**Why it happens:**
Fault injection is usually built to satisfy "does the SLO breach fire" as a binary check, not "does this look and evidence-chain like the real failure mode it's named after," and the two are only the same by accident.

**How to avoid:**
- Inject latency/errors at the **specific span/operation** the incident claims to affect (e.g., wrap only the pgvector similarity-search call, not the whole request handler), and verify via SigNoz trace waterfall — not just an aggregate latency metric — that the injected delay is visibly attributable to that one span.
- Add small randomized jitter to injected delays/error rates rather than fixed constants, and run background "normal" traffic concurrently with the incident window so the SLO breach appears as a deviation from a baseline, not as the only traffic in the system.
- For the retry-storm/cost incident specifically: compute the actual token volume needed to cross the configured cost SLO threshold *before* building the injection, and size the retry count/loop duration to comfortably exceed it within the demo's real time window — verify this arithmetic explicitly rather than assuming "more retries = more cost" is obviously enough.
- Run each incident once manually and inspect the resulting SigNoz trace/metric view exactly as the agent (and a judge) would, before trusting it in the eval harness.

**Warning signs:**
- Injected latency numbers that are suspiciously exact (e.g., a metric spikes from exactly 50ms to exactly 5000ms flat for the incident's duration).
- No background/baseline traffic during an incident window in the SigNoz trace explorer.
- An incident's designed-to-breach SLO showing "no data"/borderline values in the alert evaluation panel.

**Phase to address:**
Day 6 (incident implementation and seeding) — validate each incident manually in SigNoz before it enters the automated 3-run eval harness.

---

### Pitfall 9: Deep links resolve to empty views or 404 despite the underlying data existing

**What goes wrong:**
The project has a hard 100%-link-resolution target. Three concrete ways this breaks: (1) URL parameters must be URI-encoded a specific number of times depending on the parameter (SigNoz's own docs note this varies by parameter) — an under- or over-encoded `compositeQuery` or filter param silently renders an empty explorer view rather than erroring; (2) timezone mismatch between the time range encoded in the link (often expected as epoch millis/nanos, effectively UTC) and how the evidence's timestamp was captured/displayed locally — a link built from a naively-formatted local-time string can point at the wrong window entirely, showing "no data" even though the evidence exists a few hours off; (3) links generated against data that later ages out of the configured retention window between when the evidence is captured and when a judge clicks the link days later.

**Why it happens:**
Deep-link generation is usually built and eyeballed once against fresh data on the developer's machine (same timezone, data still hot), and the encoding/timezone/retention issues only surface when someone else, later, in a different environment, clicks the link.

**How to avoid:**
- Build every deep link through **one centralized link-builder function** that owns encoding and timestamp formatting — never hand-format a URL string at more than one call site.
- Always construct timestamps in UTC/epoch explicitly (never `datetime.now()` without tzinfo) and unit-test the link builder against known input/output pairs, not just visually confirm one link works.
- Build the **automated link checker** (already in the requirements) to run as part of the Day 6 eval harness, not as a one-off manual check, and re-run it the morning of the demo (Day 7) against the actual data that will be shown live — retention windows and demo timing mean a link built on Day 5 may not resolve on Day 7.
- Set SigNoz retention generously (or note the demo's data will always be same-day/fresh) so this isn't a live risk on demo day specifically — but do not assume default retention settings without checking them.

**Warning signs:**
- Any deep link authored by directly string-formatting a URL outside the shared builder.
- The link checker passing in local dev but not in a machine with a different system timezone.
- A gap of more than a day between generating demo evidence and recording/giving the live demo, without re-verifying links.

**Phase to address:**
Day 3 (Law 1 — evidence and link generation) for the centralized builder and its unit tests; Day 6 for the automated link-checker integration into the eval harness; Day 7 for a same-day re-check before recording/demoing.

---

### Pitfall 10: Trace context and log-trace correlation silently break across async/background boundaries

**What goes wrong:**
Two related mechanisms are easy to half-wire: (1) `FastAPIInstrumentor`'s server span ends when the response body is sent, but Starlette can still execute `BackgroundTasks` or a detached `asyncio.create_task()` after that point — without explicitly capturing and re-attaching the OTel context, any spans created inside that background work become **orphaned** (no parent), breaking the "span links connecting investigation spans to the original incident traces" requirement; (2) Python's log-trace correlation via `LoggingInstrumentor`/`OTEL_PYTHON_LOG_CORRELATION` has open, reported issues where the environment-variable-driven auto-configuration does not reliably inject `trace_id`/`span_id` into log records, silently degrading Law 1's "logs correlated to the incident trace" evidence to logs with no correlation at all.

**Why it happens:**
Both mechanisms *look* automatic (instrumentation libraries advertise "just instrument and go") but both have documented edges — background-task boundaries and log-correlation auto-config — where the automation quietly stops working rather than erroring.

**How to avoid:**
- For any work that happens after a response is returned or that is dispatched to a new task/thread (the investigation kick-off itself is a strong candidate for this pattern), explicitly capture `context.get_current()` before dispatch and `context.attach()` it inside the task, rather than relying on implicit propagation — treat this as mandatory, not optional, per the earlier finding that "explicit passing is more reliable and easier to debug than context variables" for this exact boundary.
- Do not rely solely on `OTEL_PYTHON_LOG_CORRELATION=true`; explicitly call `LoggingInstrumentor().instrument(set_logging_format=True)` in app startup code and verify with a smoke test that a log line emitted inside an active span actually contains a non-zero `trace_id`.
- Use explicit OpenTelemetry **span links** (not just parent/child) to connect a fresh investigation trace to the original incident's trace ID, per the project's own requirement — span links are the documented mechanism for "related but not parent-child" traces and must be added explicitly in code at investigation start, using the incident's stored trace ID.

**Warning signs:**
- Any span from a background-dispatched investigation showing up as a new root trace instead of linked to the incident trace.
- Log lines in SigNoz's log explorer with empty/zero `trace_id` fields during an active investigation.
- The evidence renderer producing a "log evidence" citation whose deep link, when clicked, cannot actually correlate back to the cited trace.

**Phase to address:**
Day 2 (telemetry depth) for log-correlation verification; Day 3 (Law 1 evidence pipeline) for explicit context capture and span-link wiring at investigation dispatch.

---

### Pitfall 11: Metric cardinality explosion from putting per-investigation or per-incident IDs into metric attributes

**What goes wrong:**
It's tempting to tag Law 3's investigation-level metrics (duration, MCP query count, etc.) with a unique investigation ID or trace ID as a metric attribute/label so they can be "correlated" with the trace in one query. Every unique ID creates a new time series; with 12+ investigation runs plus ad hoc dev testing, this alone might seem small — but combined with per-query-hash labels on the loop-breaker's repetition-tracking metric, or per-model-name-plus-per-call-id combinations on cost metrics, cardinality can grow fast enough to make SigNoz's metrics explorer slow or the dashboard panels misleading (data folded into an overflow bucket) right when the team needs them most, days before the demo.

**Why it happens:**
Putting an ID in a metric attribute feels like the natural way to "join" metrics and traces, but it is the wrong mechanism — traces/logs are for that, exemplars are the correct metric-to-trace bridge.

**How to avoid:**
- Never put investigation ID, trace ID, MCP query hash, or any other high-cardinality/unique value into a metric attribute. Use bounded attributes only: incident type (4 values), model name (small fixed set), check name (6 values), verdict (allow/deny).
- Use OTel **exemplars** (or simply: put the unique IDs on the *span*, and rely on the metric being aggregate) when a specific metric data point needs to point back to a specific trace.
- Review every `metric.record(...)` call site during Day 5 specifically for attribute cardinality before the eval harness starts generating volume.

**Warning signs:**
- Any metric attribute whose value is unique per call (a UUID, a hash, a timestamp).
- SigNoz metrics explorer becoming slow or showing an "overflow"/limit warning on a dashboard panel during Day 5-6 testing.

**Phase to address:**
Day 5 (Law 3 self-telemetry instrumentation) — review attribute sets against a fixed allowlist before instrumenting.

---

### Pitfall 12: Alert evaluation windows don't fit inside the demo's compressed incident timeline

**What goes wrong:**
SigNoz alerts check on a default 1-minute evaluation interval, and best-practice evaluation windows are 5-10x the collection interval — meaning a 5-minute evaluation window wants roughly 5 data points at a 1-minute scrape interval. If a seeded incident is designed to inject a fault for only 30-60 seconds (reasonable for a snappy live demo), the alert may not have enough data points in its window to evaluate at all, and SigNoz explicitly resolves/skips alerts when below the minimum data-point threshold rather than firing early. This produces a "wait, why didn't the alert fire" moment live, or a false "the SLO wasn't breached" result during the eval harness even though the incident did what it should.

**Why it happens:**
Alert windows are typically tuned for real production noise reduction, which is the opposite goal of a demo that wants fast, legible signal — nobody revisits the default window sizing for a compressed timeline until it's tested against the actual incident duration.

**How to avoid:**
- Explicitly size each incident's injected fault duration against its alert's evaluation window and collection interval — as a rule of thumb, make sure the fault persists for at least the full evaluation window, not just past the SLO threshold instantaneously.
- Prefer shorter evaluation windows (e.g., "Last 5 minutes" rather than "Last 1 hour") for incident-linked alerts specifically, and document why, since this is a deliberate demo-timing decision, not a general alerting best practice violation.
- Test each alert's actual fire-latency during Day 6 seeding, end to end (inject fault → wait → confirm fired in SigNoz UI/API), rather than assuming the configured window "should" work.

**Warning signs:**
- An alert configured with a window longer than the incident's planned injection duration.
- Eval harness runs where the SLO was clearly breached (visible in raw data) but the alert never transitioned to firing.

**Phase to address:**
Day 6 (incident seeding and alert configuration) — validate fire-latency against actual incident duration before the eval matrix run.

---

## Minor Pitfalls

### Pitfall 13: MCP tool calls returning empty/partial results get treated as "no evidence" by a human, but as "keep guessing" by the model

**What goes wrong:**
When an MCP tool call (e.g., a metrics query) returns an empty result set — a real and expected outcome sometimes (nothing breached, no matching logs) — LLMs have a documented tendency to keep making further tool calls with randomly varied parameters rather than accepting the empty result, occasionally fabricating a plausible-sounding conclusion despite no data. For this project, an empty MCP result must produce a deliberate "no evidence found" branch in code (which then correctly fails Law 1's evidence-required check), not additional unguided tool calls that also feed the loop breaker's repetition counter.

**How to avoid:**
Define an explicit, code-level branch for empty/partial MCP results at each investigation stage — do not leave "what happens on empty results" to model judgment. Treat an empty result as a first-class outcome (e.g., "hypothesis unsupported, try next hypothesis" or "escalate: no evidence available") rather than retrying the same query shape.

**Warning signs:**
The agent issuing near-identical MCP queries with only minor parameter tweaks after an empty result, or producing a claim after a stage that returned zero evidence rows.

**Phase to address:**
Day 3 (agent core / MCP integration) — build the empty-result branch alongside the happy path, not as an afterthought.

---

### Pitfall 14: MCP tool timeouts on large SigNoz result sets stall or truncate an investigation

**What goes wrong:**
The SigNoz MCP server caps some tool result sizes explicitly (e.g., docs search capped at 25 results, metric usage lookup capped at 50 metrics with a 30-second timeout returning partial results, standalone query results capped at 100). A query built broadly (wide time range, no filter) can hit these caps or a client-side MCP timeout, returning partial data that looks complete unless the agent explicitly checks for truncation/pagination markers (`hasMore`, `nextOffset`).

**How to avoid:**
Always scope MCP queries to the incident's known time window and relevant service/attribute filters (never an unbounded query), and explicitly check pagination/truncation markers in tool results before treating a result set as exhaustive — log a warning telemetry event whenever a result was truncated so it's visible in Law 3's self-telemetry rather than silently accepted as complete.

**Warning signs:**
Investigation evidence that cites "no breach found" derived from a query that was actually truncated, not exhaustive.

**Phase to address:**
Day 3 (MCP integration) for scoped queries and truncation checks.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|-----------------|------------------|
| Tuning policy-gate thresholds against the 4 seeded incidents directly | Fast path to 2-allow/2-deny | Overfit gate that fails under any variation, undermines core thesis if a judge probes it | Never — see Pitfall 4 |
| Treating missing LLM `usage` data as zero cost | Simpler cost-sum code | Silently defeats the cost watchdog and misreports Law 3's core metric | Never |
| Skipping `force_flush()` on short-lived processes because "it usually works" | Less boilerplate | Silent, intermittent loss of exactly the spans the audit-trail thesis depends on | Never for investigation runs or rollback executor; acceptable only for throwaway local scratch scripts |
| Hardcoding one OpenRouter model with no fallback array | Simpler client code | A single rate-limit event stalls or kills a live demo | Only acceptable for the very first Day 1 smoke test, never past Day 2 |
| Putting a UUID or trace ID directly into a metric attribute for "easy correlation" | Feels like a quick join | Cardinality explosion, slow/misleading dashboard panels right before demo | Never — use exemplars or span-level IDs instead |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|-----------------|-------------------|
| OTLP exporter → SigNoz Collector | Sending gRPC payload to port 4318 (HTTP) or appending `/v1/traces` to a gRPC endpoint | Explicitly pair protocol and port (4317=gRPC, 4318=HTTP/protobuf); add a startup self-check that flushes one span and confirms it's queryable |
| SigNoz MCP server auth | Assuming stdio-mode env vars (`SIGNOZ_URL`, `SIGNOZ_API_KEY`) apply automatically to an HTTP-mode connection from a Python client | For a programmatic Python client (not a desktop MCP host), run the server in HTTP mode explicitly and pass credentials either server-side (env) or per-request via the `SIGNOZ-API-KEY` header, matching whichever mode was configured |
| OpenRouter streaming responses | Omitting `stream_options.include_usage=True`, silently losing token counts | Always request usage-inclusive streaming; treat missing usage as an explicit error, not zero cost |
| OpenRouter retries/fallbacks | Retrying the identical request without deduplication, risking double-billing on near-simultaneous cache misses | Use OpenRouter's response-caching header where safe, and separate "attempted calls" from "billed calls" in telemetry so retries don't corrupt the cost sum |
| SigNoz deep-link generation | Hand-building query strings per call site with inconsistent encoding/timezone handling | One centralized, unit-tested link-builder function; always UTC/epoch timestamps |
| Postgres + pgvector via FastAPI async | Passing a request-scoped SQLAlchemy session into a background task after the request session is closed | Give background/investigation work its own session/connection lifecycle, never inherit a request-scoped one |
| Foundry `casting.yaml` / `casting.yaml.lock` | Editing `casting.yaml` and forgetting to regenerate the lock file, so a clean-machine `cast` doesn't match what was actually tested | Regenerate and commit the lock file as part of the same commit as any casting.yaml change; treat lock drift as a CI-checkable condition |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|-----------------|
| BatchSpanProcessor default 5s flush interval on short-lived investigation scripts | Spans appear inconsistently in SigNoz, more often missing on fast runs | Explicit `force_flush()` before process/handler exit | Every time the process exits faster than the batch interval — i.e., almost every investigation run |
| Unbounded MCP query time ranges | Slow investigations, tool timeouts, truncated results treated as complete | Always scope queries to the incident's known window + relevant filters | Any query without an explicit time range or service filter |
| SigNoz self-host with no resource limits on ClickHouse (documented default in the bundled compose file) | Slow dashboard/alert queries as demo/eval data accumulates over the week | Add explicit resource limits and a data volume; keep seed + eval data volume small and bounded | Once several days of accumulated dev + eval + demo-rehearsal traffic builds up in the default (unbounded, short-TTL) setup |
| Metric cardinality from per-ID attributes | Slow metrics explorer, dashboard panels folding into overflow buckets | Bounded attribute allowlist (incident type, model, check name, verdict only) | Once investigation count + query-hash variety passes a few hundred unique combinations |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Rollback executor sidecar exposing `POST /rollback` without any auth/allowlist on caller identity | Any process on the network (or a judge poking the API during evaluation) could trigger a rollback outside the policy gate, undermining the entire "process isolation enforces Law 2" claim | Restrict the sidecar's network exposure to only Agent K's container (compose network, no published host port), and add a shared-secret or mTLS-style check even in a sandboxed demo, so the isolation claim survives a skeptical judge poking at it |
| SigNoz API key with Admin role used for the MCP server in a repo that might get shared/screen-recorded | Credential leakage in demo footage or committed config | Use a scoped-down key if SigNoz supports it, keep it in an untracked `.env`, and specifically check demo recordings/screenshots for visible key strings before submission |
| OpenRouter API key committed to a config file for reproducibility convenience | Key leakage in the public hackathon repo | Keep API keys out of `casting.yaml`/git entirely; document required env vars in the README instead |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-------------------|
| Presenting computed cost figures with no visible methodology note | Judge assumes real billing, feels misled on discovering it's computed | Inline "(computed, not billed)" label everywhere a cost number appears, not just in a README |
| Dashboard requiring the viewer to already know which of the 4 sections maps to which Law | Judge can't map the dashboard to the pitch without narration | Section headers that name the Law/claim they support directly (e.g., "Agent Health — Law 3 self-telemetry") |
| Silent denial verdicts with no evidence-linked human recommendation | Looks like the agent "gave up" rather than behaved safely | Always render the required evidence-linked human recommendation on every denial — this is already a stated requirement; verify it never gets skipped, including on unexpected failure paths |

## "Looks Done But Isn't" Checklist

- [ ] **Deep links:** Often "work" only from the developer's own machine/timezone/session — verify by opening every generated link in a fresh incognito browser session, in UTC-shifted local time if possible, right before the demo.
- [ ] **Loop breaker:** Often only tested against an intentionally pathological infinite-loop case — verify it does *not* false-positive on a healthy run that needed 2-3 legitimate retries due to rate limits.
- [ ] **Cost watchdog:** Often only tested against a run with complete usage data — verify its behavior specifically when `usage` is missing (should error/flag, not compute $0 and pass).
- [ ] **Policy gate 2-allow/2-deny:** Often verified only against the exact 4 seeded incidents as built — verify each check independently via unit tests with synthetic inputs unrelated to the 4 incidents.
- [ ] **Span-to-log correlation:** Often "instrumented" via env var alone — verify by pulling an actual log line from SigNoz for an active investigation and confirming a non-empty `trace_id` field.
- [ ] **Clean-machine rebuild:** Often only timed with warm Docker layer cache — verify with an actual `docker system prune -a` (or equivalent fresh VM) run, timed end-to-end, at least twice before submission.
- [ ] **Investigation spans in SigNoz:** Often "present" in the sense that the report file was generated, but missing in SigNoz because the process exited before flush — verify span count in SigNoz matches investigation count, not just report-file count.
- [ ] **Alert firing:** Often configured but never verified to actually fire within the demo's compressed incident timeline — verify fire-latency against the real injected fault duration, not just the SLO math on paper.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|----------------|-----------------|
| OpenRouter daily cap hit mid-eval | LOW (if caught Day 1-2) | Purchase $10 credits immediately (raises cap permanently); re-run affected eval runs |
| Policy gate overfit to 4 incidents discovered late | MEDIUM | Re-derive each check from its unit-test decision table (already should exist per Pitfall 4 prevention); re-run eval matrix — costly only if the decision-table step was skipped entirely and must now be retrofitted |
| Missing investigation spans in SigNoz discovered during Day 6 eval | LOW-MEDIUM | Add explicit `force_flush()` at every short-lived exit point; re-run the specific incidents/runs affected, not the full matrix if force_flush fixes it going forward |
| Clean-machine rebuild exceeds 15 minutes discovered Day 6-7 | MEDIUM-HIGH | Pin image tags, pre-pull during rehearsal if allowed by rules, trim seed data volume, profile which step dominates (ClickHouse init vs. image pull vs. pip install) and cut the largest single contributor first |
| Deep links found broken during final demo prep | LOW | Regenerate the specific broken links via the centralized builder immediately before recording; if a systemic encoding/timezone bug, fix the builder once and re-run the link checker against all evidence |
| Seeded incident found "too clean" or not breaching its SLO late (Day 6) | MEDIUM | Add jitter/baseline traffic and re-verify against the alert's evaluation window (Pitfall 12); this is recoverable within Day 6 but consumes the day's buffer, so treat it as a Day 6-morning check, not a Day 6-evening surprise |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|-------------------|----------------|
| OpenRouter daily rate cap (P1) | Day 1 | Real per-day usage counter matches OpenRouter dashboard; $10 credit purchase confirmed before Day 3 |
| Reasoning-model tool-call/JSON drift (P2) | Day 3, Day 5 | Schema-validation failure rate logged and reviewed; fallback model tested working before Day 5 |
| Silent OTel span/data loss (P3) | Day 1, Day 4-5 | Span-count-in-SigNoz vs. investigation-count assertion in eval harness |
| Policy gate overfitting (P4) | Day 4 (design), Day 6 (verify only) | Per-check unit tests pass independent of the 4 incidents; decision table exists as a design artifact |
| Cost accounting honesty (P5) | Day 2-3, Day 5, Day 7 | Missing-usage triggers an explicit error path; every cost figure has a visible methodology label |
| Retry/loop-breaker/cost interaction (P6) | Day 5 | Simulated 429-storm unit test passes without false loop-breaker trip or inflated cost |
| Clean-machine rebuild time (P7) | Day 1 (pin), Day 5 (first real test), Day 7 (final test) | Two independent cold-cache rebuild timings both under 15 minutes |
| Incident realism / SLO breach reliability (P8) | Day 6 | Each incident manually verified in SigNoz trace/metric view before entering automated eval harness |
| Deep-link 100% resolution (P9) | Day 3 (build), Day 6 (checker), Day 7 (recheck) | Automated link checker passes in CI and again same-day as the demo recording |
| Async context / log-trace correlation (P10) | Day 2, Day 3 | Log line smoke test shows non-zero trace_id; span-link wiring confirmed at investigation dispatch |
| Metric cardinality (P11) | Day 5 | Attribute allowlist review of every `metric.record` call site |
| Alert evaluation window vs. incident duration (P12) | Day 6 | Fire-latency measured end-to-end per incident, not assumed from configured window |
| MCP empty-result handling (P13) | Day 3 | Explicit empty-result branch exists and is exercised by a test case with no synthetic data in range |
| MCP result truncation (P14) | Day 3 | Truncation/pagination markers checked in code; scoped queries used everywhere |

## Sources

- [How to Propagate Trace Context Across Async Boundaries (Threads, Promises)](https://oneuptime.com/blog/post/2026-02-06-propagate-trace-context-async-boundaries/view) — MEDIUM confidence (single-source blog, pattern consistent with OTel spec)
- [How to Trace FastAPI Background Tasks with OpenTelemetry Spans](https://oneuptime.com/blog/post/2026-02-06-trace-fastapi-background-tasks-opentelemetry/view) — MEDIUM
- [Background tasks do not execute when decorated with opentelemetry tracing · fastapi/fastapi Discussion #10153](https://github.com/fastapi/fastapi/discussions/10153) — MEDIUM (community-reported, corroborates independently)
- [opentelemetry.sdk.trace.export — OpenTelemetry Python documentation](https://opentelemetry-python.readthedocs.io/en/latest/sdk/trace.export.html) — HIGH (official docs)
- [How to Fix 'Dropped Spans' in OpenTelemetry](https://oneuptime.com/blog/post/2026-01-24-fix-dropped-spans-opentelemetry/view) — MEDIUM
- [SigNoz MCP Server - AI Assistant Integration Guide](https://signoz.io/docs/ai/signoz-mcp-server/) — HIGH (official docs)
- [GitHub - SigNoz/signoz-mcp-server](https://github.com/SigNoz/signoz-mcp-server) — HIGH (official repo)
- [API Credit & Rate Limits - Handle 402 and 429 Errors](https://openrouter.ai/docs/api_reference/limits) — HIGH (official docs)
- [OpenRouter Rate Limits – What You Need to Know](https://openrouter.zendesk.com/hc/en-us/articles/39501163636379-OpenRouter-Rate-Limits-What-You-Need-to-Know) — HIGH (official support docs)
- [OpenRouter Free Tier 2026: Rate Limits, Models, BYOK](https://klymentiev.com/blog/openrouter-free-tier) — MEDIUM (corroborates official docs)
- [Embeddings API — OpenRouter](https://openrouter.ai/docs/api_reference/embeddings) — HIGH (official docs, confirms `/api/v1/embeddings` is real and OpenAI-schema compatible)
- [Response Caching — OpenRouter Blog](https://openrouter.ai/blog/announcements/response-caching/) — HIGH (official)
- [openai/gpt-oss-20b · Unable to Structured output (Hugging Face discussion)](https://huggingface.co/openai/gpt-oss-20b/discussions/111) — MEDIUM (community-reported, corroborated by multiple independent issues below)
- [Structured Output doesn't work for GPT-OSS-20b and GPT-OSS-120b · lmstudio-ai/lmstudio-bug-tracker#1105](https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/1105) — MEDIUM
- [OpenAIGenericClient outputs unstable for vllm serving gpt-oss-20b · getzep/graphiti#1007](https://github.com/getzep/graphiti/issues/1007) — MEDIUM
- [Interactivity in dashboards | SigNoz Docs](https://signoz.io/docs/dashboards/interactivity/) — HIGH (official docs, confirms variable URI-encoding requirement)
- [Create Logs URL for Explorer page | SigNoz](https://signoz.io/docs/logs-management/logs-api/logs-url-for-explorer-page/) — HIGH (official docs)
- [Configure Webhook Channel | SigNoz Docs](https://signoz.io/docs/alerts-management/notification-channel/webhook/) — HIGH (official; confirms Alertmanager-style grouped payload, 5-minute default grouping)
- [Understanding Alert Evaluation Patterns | SigNoz Docs](https://signoz.io/docs/alerts-management/user-guides/understanding-alert-evaluation-patterns/) — HIGH (official docs, 1-minute default eval interval, 5-10x window:interval rule of thumb)
- [Alerts Firing Without Visible Threshold Breach | SigNoz Docs](https://signoz.io/docs/alerts-management/troubleshooting/alerts-firing-without-visible-threshold-breach/) — HIGH (official)
- [GitHub - SigNoz/foundry](https://github.com/SigNoz/foundry) and [foundry CLI reference](https://github.com/SigNoz/foundry/blob/main/docs/reference/cli.md) — HIGH (official repo/docs; casting.yaml.lock described as a checksum/state-tracking file)
- [SigNoz Resources Planning | SigNoz Docs](https://signoz.io/docs/setup/capacity-planning/community/resources-planning/) — HIGH (official)
- Self-host SigNoz tutorials (Virtua Cloud, Stack Harbor, oneuptime) on first-start time and default unbounded-resource compose bundle — MEDIUM (multiple independent third-party sources corroborate 2-5 min ClickHouse init and 4GB+ Docker memory recommendation)
- [Deterministic Policy vs LLM-Based Filters for AI Agents — Data443](https://data443.com/blog/deterministic-policy-vs-llm-filters/) — MEDIUM
- [ADR-0004: Deterministic Policy — Agent Governance Toolkit (Microsoft)](https://microsoft.github.io/agent-governance-toolkit/adr/0004-keep-policy-evaluation-deterministic/) — HIGH (vendor engineering doc, directly supports decision-table pattern)
- [In the agent, LLM may produce hallucination issues during multi-round calls to MCP · langgenius/dify#22529](https://github.com/langgenius/dify/issues/22529) — MEDIUM
- [Why Your MCP Agent Keeps Timing Out](https://medium.com/@ai_transfer_lab/why-your-mcp-agent-keeps-timing-out-and-the-fix-that-just-shipped-ad9cb130f8c4) — LOW-MEDIUM (blog, but consistent with widely-reported MCP client timeout defaults)
- [Gen AI semantic conventions | OpenTelemetry](https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/) — HIGH (official spec; confirms GenAI conventions still in Development status, streaming usage is opt-in via `stream_options.include_usage`)
- OTLP exporter troubleshooting (oneuptime "Top 10 OpenTelemetry Setup Mistakes", OpenTelemetry Collector official troubleshooting docs) — HIGH for port/protocol pairing (matches official spec), MEDIUM for silent-failure framing (third-party blog)
- High-cardinality metrics guidance (oneuptime cardinality posts, Last9 guide) — MEDIUM, consistent with well-established OTel/Prometheus cardinality best practices

---
*Pitfalls research for: Agent K — evidence-first incident agent on SigNoz/OpenTelemetry/FastAPI/OpenRouter, 7-day hackathon build*
*Researched: 2026-07-20*

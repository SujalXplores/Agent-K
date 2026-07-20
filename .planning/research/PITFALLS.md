# Pitfalls Research

**Domain:** Code-enforced incident-response agent on SigNoz — OTel-instrumented FastAPI+pgvector RAG app, SigNoz-via-Foundry deployment, MCP tool-calling agent, docker-compose rollback automation — built in a hard 7-day hackathon by a team with zero prior Docker/OTel/SigNoz experience
**Researched:** 2026-07-20
**Confidence:** MEDIUM (cross-checked against SigNoz/OTel official docs, GitHub issues, and the `mcp` SDK repo; hackathon-process claims are LOW-confidence generic advice, flagged inline)

## Critical Pitfalls

### Pitfall 1: SigNoz + ClickHouse silently starves on a laptop, eating Day 1

**What goes wrong:**
The team spends the first day of a 7-day window fighting a self-hosted SigNoz stack that starts but is unusably slow, or ClickHouse Keeper crash-loops with segfaults, and nobody knows if it's their instrumentation or the platform.

**Why it happens:**
SigNoz's docker-compose stack (ClickHouse + Keeper + query-service + alertmanager + frontend + collector) needs a hard minimum of ~4GB RAM allocated to Docker, with 1.5-2GB baseline idle usage — more under any real load. On Docker Desktop for macOS/Windows this is a VM memory allocation setting most first-timers never touch. Teams with zero Docker experience default to whatever Docker Desktop ships with (often 2GB) and get segfaulting Keeper containers or a UI that never loads data, and mistake it for "our OTel setup is wrong."

**How to avoid:**
On Day 1, before writing any app code: bump Docker Desktop's VM memory to 6-8GB, bring up bare SigNoz via Foundry, confirm the UI loads and a synthetic `curl` test trace appears — with zero application code involved. Treat "empty SigNoz, but running and reachable" as the Day-1 exit criterion, separate from "our app sends traces."

**Warning signs:** Collector/Keeper containers restarting in `docker ps`, SigNoz UI spinning/timing out, `docker logs` showing OOM-kill or segfault (exit code 139) on the ClickHouse Keeper container.

**Phase to address:** Earliest infra/setup phase (Day 1), before any RAG-app instrumentation work begins — this is a pure platform-standup task, block all other work on it passing.

---

### Pitfall 2: Traces exist but never reach SigNoz — and nobody can tell why

**What goes wrong:**
The app runs, OTel SDK is wired in, no errors are thrown, but the SigNoz UI shows no traces. The team burns hours guessing between "wrong endpoint," "wrong port," "collector down," and "instrumentation isn't firing at all" because these four failure modes look identical from the app's perspective.

**Why it happens:**
This is a known class of issue (SigNoz GitHub issue #6750 and others): OTLP has two ports (4317 gRPC, 4318 HTTP) and picking the wrong one plus the wrong protocol produces cryptic errors like `http2: frame too large`; missing/incorrect auth headers on the exporter fail silently or with opaque 401s; and if the instrumentation itself never generated a span (e.g., `FastAPIInstrumentor.instrument_app()` was never called, or was called after routes were already registered), there's nothing to export at all — indistinguishable from a network problem without a console exporter to check first.

**How to avoid:**
Debug in two isolated stages, never combined: (1) console-exporter first — configure OTel to print spans to stdout, confirm the app is generating spans at all, independent of SigNoz; (2) only then switch the exporter to OTLP against SigNoz's collector, using the exact host:port:protocol triple from SigNoz's own docs (`4317` for gRPC OTLP, `4318` for HTTP OTLP) — do not guess. Keep the console exporter toggle available via env var for the rest of the build for fast triage when new instrumentation is added later.

**Warning signs:** Zero traces in SigNoz UI with zero app-side errors logged; `docker logs <collector>` showing no ingest activity at all vs. showing rejected/malformed payloads (different root causes).

**Phase to address:** Instrumentation setup phase, immediately after Pitfall 1's bare-SigNoz check — add the console-exporter fallback as a standing debug capability, not a one-time check.

---

### Pitfall 3: GenAI semantic-convention attributes are still experimental and easy to get subtly wrong

**What goes wrong:**
The team hand-rolls `gen_ai.*` attribute names from memory or a blog post, ships spans that don't match the current OTel GenAI semconv registry, and loses "deepest SigNoz integration" credibility because the judges (who know the convention) see nonstandard or stale attribute names — or the team accidentally logs full prompt/completion text as indexed span *attributes* instead of span *events*, which is explicitly called out as an anti-pattern (attributes are size-limited and indexed; content belongs in events, gated behind an opt-in).

**Why it happens:**
As of 2026 the GenAI semconv is still marked experimental in the OTel spec, so tutorials and blog posts disagree on exact attribute names, and the convention changed shape (dual old/new names) mid-adoption. A team new to OTel copies whichever example they found first without checking it against `opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/` directly.

**How to avoid:**
Build one small shared helper (`genai_span_attrs(...)`) that centralizes attribute names sourced directly from the current OTel GenAI semconv page, used everywhere an LLM call is wrapped (RAG app's answer-generation step AND Agent K's own reasoning calls) — one source of truth instead of copy-pasted literals drifting apart. Put prompt/completion text in span **events**, not attributes; keep attributes to `gen_ai.request.model`, `gen_ai.usage.input_tokens`/`output_tokens`, `gen_ai.operation.name`, `gen_ai.provider.name`, `gen_ai.response.finish_reasons`.

**Warning signs:** Attribute names that don't autocomplete/match anything in SigNoz's trace attribute filter dropdown; dashboard panels built against `gen_ai.*` fields showing no data because the actual emitted key differs by a prefix or casing.

**Phase to address:** RAG-app instrumentation phase and Agent K self-telemetry phase — both need this helper; build it once, early, and reuse.

---

### Pitfall 4: FastAPI background-task spans become orphaned (or don't link back to the investigation trace)

**What goes wrong:**
Any work that happens after an HTTP response is sent — including, critically, Agent K's own alert-webhook handler if it does the investigation loop as a FastAPI `BackgroundTask` — produces spans with no parent, breaking the "every claim links to a resolvable evidence trace" requirement (Law 1) and making the incident report's span-links dead ends.

**Why it happens:**
Starlette's `BackgroundTasks` run after the ASGI response body is sent, by which point OTel's auto-instrumentation has already ended the HTTP server span. Any span opened inside the background task with no explicit context has no parent and becomes an orphaned root trace, disconnected from the alert-handling request that triggered it.

**How to avoid:**
If Agent K's webhook handler kicks off the investigation as a background task (rather than blocking the HTTP response, which is also a valid choice), explicitly capture the OTel context before scheduling the task (`ctx = context.get_current()`) and re-attach it inside the task (`token = context.attach(ctx)` ... `context.detach(token)` in try/finally) so investigation spans are children of — or at minimum linked to — the alert-received span. If Agent K instead runs its investigation loop as a synchronous handler or a separate process/poller (which the project's "state machine" framing suggests), this pitfall mostly disappears — call this out explicitly as a reason to prefer a simple synchronous or separately-triggered investigation loop over `BackgroundTasks` for the parts that require Law 1 evidence-linking integrity.

**Warning signs:** Investigation spans appearing in SigNoz as new root traces instead of children/linked-to the triggering alert/webhook trace; span-links in the incident report resolving to a trace that has no connection back to the original alert.

**Phase to address:** Agent K core loop / Law 1 evidence-schema phase — decide the threading model (background task vs. sync vs. separate process) before building the investigation loop, since it changes how span-linking must work.

---

### Pitfall 5: Docker Compose "restart" doesn't do what a rollback needs — and the rollback executor can't tell success from a crash loop

**What goes wrong:**
The rollback executor edits `docker-compose.yml`'s image tag and calls something that looks like a restart, but the running container keeps the *old* image because plain `docker compose restart` does not pick up compose-file changes — env vars, image tag, and mounts are baked in at container creation time. Separately, if the rollback target image itself is broken, `docker compose up -d` with `restart: always` will crash-loop forever, and a naive rollback executor that just "waits, then re-queries SigNoz" will time out without ever reporting *why* — it looks identical to "rollback didn't help" from the outside.

**Why it happens:**
`docker compose restart` and `docker compose up -d` are easy to conflate for a team new to Docker — both "restart the service" in casual language, but only `up -d` recreates containers with the new compose-file config. Nobody on the team has hit this distinction before, so it's not an instinctive check.

**How to avoid:**
The rollback executor must always use `docker compose up -d <service>` (recreate), never `restart`, after editing the compose file's image tag. After recreate, explicitly check container health/exit status (`docker inspect` or `docker compose ps` for a running/healthy state) *before* re-querying SigNoz for recovery — distinguish "container is up and SigNoz still shows errors" from "container itself won't start" in the recorded outcome, since Law 3 telemetry needs to capture which failure mode actually occurred.

**Warning signs:** Rollback marked "executed" in telemetry but the error-rate metric in SigNoz never recovers; `docker compose ps` showing the rolled-back service in a `Restarting` state.

**Phase to address:** Rollback executor phase — build the health-check-then-verify step as a first-class part of the executor from the start, not bolted on after the demo reveals it's missing.

---

### Pitfall 6: Mounting the monitored app's compose file/Docker access from Agent K is a real privilege-escalation surface — even in a hackathon

**What goes wrong:**
"Agent K has direct access to the monitored app's `docker-compose.yml`/`.env` on the same host" is architecturally simplest, but if Agent K itself runs in a container and the team reaches for the obvious solution — mounting `/var/run/docker.sock` into Agent K's container so it can run `docker compose` commands — that grants Agent K (and by extension, anything that can reach its LLM-driven action path) root-equivalent control of the entire host, not just the one allowlisted rollback action. This directly undercuts the "Law 2: no action without budget, sandboxed to one allowlisted action" claim the project is trying to demonstrate.

**Why it happens:**
Docker-socket mounting is the path of least resistance in every "container needs to control other containers" tutorial, and the security implications (full host root via the Docker API) are not obvious to a team without prior Docker experience — it looks like a config detail, not a security boundary.

**How to avoid:**
Simplest safe option for a 7-day build: run Agent K as a host process (not containerized) with filesystem access to the compose file and the Docker CLI on the host — this avoids socket-mounting entirely and matches "sandboxed to one allowlisted action" more honestly, since the sandbox is enforced in Agent K's own policy code (Law 2), not by container boundaries. If Agent K must run containerized, mount the socket read-only at minimum and document in the submission that "sandbox" refers to the code-level allowlist, not container isolation — do not claim stronger isolation than exists, since judges evaluating "technical excellence" may probe this.

**Warning signs:** Any point where the rollback executor's code path could theoretically construct an arbitrary `docker` command from LLM-influenced input rather than a hardcoded, parameter-limited function.

**Phase to address:** Rollback executor design phase — decide host-process vs. containerized Agent K before writing the executor, since it's a hard-to-reverse architectural choice.

---

### Pitfall 7: MCP stdio transport breaks silently if anything writes to stdout, and SSE is already deprecated

**What goes wrong:**
If Agent K's MCP client launches the SigNoz MCP server as a stdio subprocess, any stray `print()` statement, logging misconfiguration, or third-party library that writes to stdout inside the server process corrupts the JSON-RPC message stream — producing confusing partial-parse errors that look like an MCP SDK bug rather than a logging mistake. Separately, if the team reaches for SSE transport (common in older tutorials) instead of Streamable HTTP, they's building against an already-deprecated part of the spec.

**Why it happens:**
stdio transport reserves stdout exclusively for protocol messages, but nothing else in a typical Python process nudges a team toward that assumption — `print()` for debugging is the most natural first move when something isn't working, which makes the failure worse precisely when a team is already debugging.

**How to avoid:**
Establish a hard rule from the first line of MCP integration code: all debug/log output goes to `stderr` (`logging` module configured to stderr, or explicit `print(..., file=sys.stderr)`), never `stdout`, in anything that runs as an MCP server subprocess. Confirm which transport the SigNoz MCP server actually exposes (check SigNoz's own MCP server docs/config) before assuming stdio vs. HTTP — prefer whatever SigNoz documents as current, and treat SSE as legacy if offered alongside Streamable HTTP.

**Warning signs:** MCP client raising JSON decode errors or "unexpected token" errors immediately after adding any new logging statement in the server process; connection working fine until a specific code path (that happens to print something) executes.

**Phase to address:** Agent K ↔ SigNoz MCP integration phase — set the stderr-only logging convention before the first MCP call is written, and re-affirm it in code review for that phase.

---

### Pitfall 8: Free-tier LLM rate limits (Groq: 30 RPM / 6,000 TPM) collide directly with the evaluation harness's own design

**What goes wrong:**
The evaluation harness runs 3 runs × 4 incident types = 12 full investigation loops, each involving multiple LLM calls (initial hypothesis, confidence scoring, possibly re-investigation after MCP queries) plus the RAG app's own answer-generation calls happening concurrently if the demo is "live." On Groq's free tier (30 requests/minute, 6,000 tokens/minute per published 2026 limits), a single verbose investigation prompt can consume the *entire* minute's token budget, and running eval batches back-to-back will hit 429s — exactly on eval day, with the least slack in the schedule and (per the project's own constraint) one team member already unavailable.

**Why it happens:**
Rate limits are invisible until they're hit; a team that has been testing one incident at a time all week has no signal that batch evaluation runs will behave completely differently under the same account's shared rate-limit bucket (limits apply at the org level, not per-key).

**How to avoid:**
Build a deliberate delay/backoff into the eval harness runner itself (not just retry-on-429, but paced requests with a token-budget-aware scheduler) from the day the harness is first built, not bolted on during eval day. Test the harness's rate-limit handling against at least one full incident's 3 runs *before* the final eval day, using a throwaway low-token scenario, to see actual throughput under Groq's real limits. Keep Cerebras (already planned as eval-day overflow) genuinely wired and tested in advance — not a "we'll figure it out when we hit it" fallback — since the plan already allocates it for exactly this purpose but it must be *proven working* before it's needed under pressure.

**Warning signs:** 429 responses appearing during any batch/scripted run (even outside formal eval); investigation runs taking dramatically longer in a batch than when run individually.

**Phase to address:** Evaluation harness phase — build pacing/backoff and a tested Cerebras fallback switch as part of the harness itself, verify both work days before the actual eval day (not on it).

---

### Pitfall 9: Loop-breaker and cost-watchdog logic gets built last and undertested — exactly the code most likely to fire live in the demo

**What goes wrong:**
Because loop-breaker and cost-watchdog are "safety net" features, they're naturally sequenced late in the build (after the happy-path investigation loop works), which under a 7-day deadline with reduced capacity in the final days (one member out July 24-26) means they get the least testing time — yet they are exactly the code path most likely to trigger unexpectedly during a live demo if any incident scenario behaves slightly differently than in earlier test runs (different LLM sampling, different MCP query patterns).

**Why it happens:**
This is the general "safety features get deprioritized under time pressure" pattern, but it's sharpened here because the project's own value proposition ("nothing is trust-the-model, everything is prove-it-in-telemetry") depends on these exact code paths being demonstrably correct — a loop-breaker or cost-watchdog bug isn't just a minor demo hiccup, it undermines the core pitch if a judge notices.

**How to avoid:**
Build the loop-breaker (query-hash repeat detection) and cost-watchdog (token/cost budget check) *alongside* the first working investigation loop, not after — they should be visible as guardrails from the very first end-to-end run, even with generous thresholds initially. Write at least one deliberately-adversarial test scenario that forces the loop-breaker to fire (e.g., a fifth seeded incident type used only for testing, not the demo) so the "escalates to human with partial evidence" path is exercised at least once before eval day, not left as untested code.

**Warning signs:** Loop-breaker/cost-watchdog code with no passing test that actually triggers it (only tests that confirm it *doesn't* fire); these two subsystems appearing as separate late-week checklist items rather than part of the Day-1-4 investigation-loop implementation.

**Phase to address:** Agent K core loop phase (Law 1/3 work) — build guardrails in the same phase as the investigation loop itself, verification for that phase should include at least one forced-trigger test.

---

### Pitfall 10: "Clean-machine rebuild under 15 minutes" is a testable claim the team will not actually test until it's too late

**What goes wrong:**
`casting.yaml`/`casting.yaml.lock` are committed early and assumed to "just work" for judges, but nobody actually runs the rebuild on a genuinely clean machine (or clean VM) until the final day — by which point image-pull time, first-run migration time, and any environment assumptions baked in during development (a locally-cached embedding model, a manually-created database, a hardcoded local path) surface as failures with no time left to fix them.

**Why it happens:**
`foundryctl forge` is described as safe/idempotent and never touching running containers, which correctly reassures the team about *iterating* on the casting file, but says nothing about whether a first-ever `cast` on a machine with zero cached Docker images, zero pre-pulled `sentence-transformers` model weights, and zero pre-seeded pgvector data will finish inside 15 minutes — that's an empirical question the team has to actually measure, not infer from the tool's safety guarantees.

**How to avoid:**
Run one full clean-machine rebuild test (fresh Docker Desktop VM, or a scratch cloud VM, or `docker system prune -a` locally) no later than Day 5-6, timed end-to-end, covering: SigNoz stand-up via Foundry, the monitored app's image build/pull, `sentence-transformers` model download (this alone can take minutes on a cold cache), pgvector corpus seeding, and confirmation that a trace actually reaches SigNoz. Treat anything over ~10 minutes as a signal to trim scope (smaller embedding model, pre-baked corpus seed as part of image build, fewer Docker layers) before the 15-minute constraint becomes a submission-blocking failure discovered too late to fix.

**Warning signs:** The rebuild has only ever been run on a machine with warm Docker/pip/model caches; no team member has run `docker system prune -a` and then timed a fresh `foundryctl cast`.

**Phase to address:** Should be scheduled explicitly as its own checkpoint around Day 5, distinct from the Foundry/`casting.yaml` authoring work earlier in the week — authoring and clean-rebuild-verification are different tasks with different failure modes.

---

### Pitfall 11: Team has zero prior Docker/OTel/SigNoz experience — generic "just start building" advice fails here specifically

**What goes wrong:**
Standard hackathon advice ("prioritize ruthlessly, build the riskiest thing first") assumes a team that can execute quickly once priorities are set. This team's риск isn't prioritization — it's that several early tasks (first Docker Compose stack, first OTel SDK wiring, first SigNoz alert rule) have a "day of confused Googling before the first thing works" tax that experienced teams don't pay, and that tax is not evenly distributed: instrumentation and deployment infra are disproportionately expensive for OTel/Docker novices compared to writing the FastAPI RAG app itself (familiar web-tech territory per the team's background).

**Why it happens:**
The team's self-assessment ("majority web-tech background") is accurate for the parts of this project that look like normal web development (FastAPI routes, HTML report page, Python state machine logic) but not for the parts that are genuinely new (Docker Compose semantics, OTel context propagation, SigNoz's query/alerting model, MCP transport quirks) — and a 7-day plan that allocates time proportional to "how big does this feature look" rather than "how novel is this to us" will systematically underestimate the infra-adjacent phases.

**How to avoid:**
When the roadmap allocates days to phases, weight infra/instrumentation phases (SigNoz standup, OTel wiring, Foundry deployment, MCP integration) with extra buffer relative to their apparent size, precisely because they're novel to the team — not because they're intrinsically harder than the agent-logic work. Sequence the genuinely novel, foundational pieces (SigNoz standup + basic OTel trace flowing end-to-end) as early as possible (Day 1-2) so any surprises there don't compound against later phases that depend on them (Agent K can't be tested without a working SigNoz + traces to query).

**Warning signs:** Any phase estimate that treats "wire up OTel" and "add a new FastAPI route" as similarly-sized units of work.

**Phase to address:** Roadmap/phase-sequencing itself — this is a planning-level pitfall, not a single phase's job; the fix is in how the 7-day plan allocates and orders time.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|-----------------|------------------|
| Skip console-exporter debug step, wire OTLP directly | Feels faster on paper | Every future "no traces showing" bug becomes a 2-hour guessing game instead of a 2-minute check | Never — costs almost nothing to add, pays for itself on the first debugging session |
| Use `docker compose restart` in early rollback prototype instead of `up -d` | Simpler code, works if you never actually change the image tag while testing | Silently fails to roll back once the demo actually needs a real image-tag swap | Only during pure UI/report-rendering prototyping where the executor is stubbed, never once real rollback logic is being tested |
| Hardcode `gen_ai.*` attribute names inline at each call site instead of a shared helper | Faster to write the first call | Attribute names drift across the RAG app and Agent K's self-telemetry, breaking dashboards that assume consistency | Only acceptable if there is truly one call site total — with two systems (RAG app + Agent K) both emitting GenAI spans, never acceptable here |
| Mount Docker socket into Agent K's container for convenience | Avoids deciding host-process vs. containerized architecture early | Undercuts the "sandboxed single-action" safety claim central to the project's pitch; a judge who understands Docker security will notice | Never for the shipped submission — acceptable only as a throwaway local experiment, never committed |
| Skip a forced-trigger test for loop-breaker/cost-watchdog | Saves an afternoon of writing an adversarial scenario | The exact code path most likely to matter live is the one path never verified to actually fire | Never — this is core to the "code-enforced, not trust-the-model" pitch |
| Defer the clean-machine rebuild test until submission day | Feels like it's "probably fine" | 15-minute constraint is a judged, hard requirement — discovering a 25-minute cold-cache rebuild on the last day leaves no time to fix it | Never — must be verified with days of slack remaining |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|-----------------|-------------------|
| SigNoz OTLP collector | Sending to the wrong port/protocol pair (4317 grpc vs 4318 http), or omitting required auth headers, and assuming it's an app bug | Verify collector reachability and port/protocol against SigNoz's own docs before touching app code; test with a console exporter first |
| SigNoz webhook alert channel | Assuming the channel works because it was configured in the UI, without hitting "Test" | Always use the Test button per channel; be aware multi-threshold alerts can silently drop `preferredChannels` (known SigNoz issue) — verify an actual alert fires end-to-end well before demo day |
| MCP server (stdio transport) | Any stdout write inside the server process (stray `print`, misconfigured logger) corrupts the JSON-RPC stream | Route all logging to stderr exclusively in anything running as an MCP stdio subprocess |
| MCP SDK (`mcp` package) | Installing whatever version `pip install mcp` resolves to, unaware v2 is pre-release/alpha with breaking changes | Pin an exact v1.x version in requirements; do not float on `mcp>=1.0` |
| Foundry (`casting.yaml`) | Committing `casting.yaml` but not `casting.yaml.lock`, assuming the yaml alone is enough for reproducible judge rebuilds | Commit both; the lock file is what makes the rebuild deterministic |
| Groq API | Testing incident scenarios one at a time all week, never exercising the eval harness's actual batch-call pattern until eval day | Run the full eval harness's real call pattern (12 runs) against real rate limits at least once before the final day |
| Docker Compose rollback | Using `docker compose restart` after editing the compose file's image tag, expecting the new image to take effect | Always use `docker compose up -d <service>` to recreate the container after any compose-file edit |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|-----------------|
| Cold-cache `sentence-transformers` model download baked into every rebuild | Clean-machine rebuild silently blows past 15 minutes on model download alone | Pre-bake the embedding model into the app's Docker image at build time, or use a small model chosen partly for download size | First clean-machine test — should be caught by Day 5-6, not submission day |
| Unbounded/undelayed eval harness LLM calls | Works fine for one incident at a time, 429s appear only when running the full 3×4 batch | Add pacing/backoff to the harness scheduler from when it's first built | The moment the harness runs more than ~1 incident's worth of calls back-to-back |
| ClickHouse with no resource limits under Docker Desktop defaults | UI sluggish or unresponsive under any concurrent load (e.g., demo audience refreshing dashboard while agent runs) | Explicitly raise Docker Desktop VM memory (6-8GB) and consider setting ClickHouse's `max_server_memory_usage_to_ram_ratio` | Under any concurrent load beyond a single developer's local testing |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Mounting `/var/run/docker.sock` into a containerized Agent K for rollback convenience | Grants effective host root, not just the one allowlisted action — directly contradicts the "sandboxed action" claim | Run Agent K as a host process with direct file/CLI access instead, or if containerized, treat the sandbox as strictly code-level (Law 2 policy), document that honestly |
| Capturing full prompt/completion content in span *attributes* rather than events, then displaying via SigNoz's default panels | Any secrets/PII that ever end up in an LLM prompt become permanently indexed and broadly visible in trace search, harder to redact after the fact | Use span events for content capture (gated behind explicit opt-in), keep attributes to structured metadata only |
| No allowlist enforcement bypass check | If the rollback executor's code path can be reached with any input other than the exact one action from a validated policy decision, Law 2 is not actually enforced | Keep the rollback executor's entry point parameter-limited (no arbitrary command construction), unit-test that non-allowlisted actions are rejected before any live demo |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-------------------|
| Incident report links to SigNoz deep links that require the judge to be authenticated/on the right SigNoz instance | Judge clicks an evidence link during review and gets a login wall or 404 — undermines the "every claim resolves" pitch at the worst possible moment | Test every evidence link from a fresh, unauthenticated-if-possible browser session as part of the automated link-checker; if auth is unavoidable, document exactly what credentials/URL judges need in the submission |
| Demo relies on toggling feature flags live with no visible confirmation of state | Presenter (or judge replaying the demo) can't tell if a flag toggle actually took effect before the incident "should" fire | Surface flag state visibly (in the report UI or a simple status endpoint) so the causal chain — flag toggled → deployment marker → alert fired — is legible in real time |
| Raw JSON error responses shown anywhere in the demo path (webhook failures, MCP errors) | Breaks the "polished, code-enforced" impression the whole project is built around | Wrap all demo-facing failure paths (not just the happy path) in the same structured-report rendering used for successful investigations |

## "Looks Done But Isn't" Checklist

- [ ] **OTel instrumentation:** Often missing the console-exporter fallback path — verify traces can be inspected without depending on SigNoz being up, useful for every future debugging session
- [ ] **Rollback executor:** Often missing post-recreate health verification — verify it distinguishes "container up but error rate unchanged" from "container failed to start" in its recorded outcome, not just a blanket timeout
- [ ] **Loop-breaker / cost-watchdog:** Often missing an actual test that triggers them — verify at least one adversarial test scenario forces each guardrail to fire and the escalation path executes
- [ ] **Foundry deployment (`casting.yaml`/`.lock`):** Often only tested on a warm-cache dev machine — verify a genuinely clean-machine rebuild completes under 15 minutes, timed, before Day 6
- [ ] **Evidence link checker:** Often only checks links resolve to *a* page, not that the page actually shows the claimed evidence — verify the checker confirms the linked SigNoz view actually contains data relevant to the claim, not just a 200 status
- [ ] **SigNoz alert → webhook → Agent K path:** Often configured and "tested" once manually, never re-verified after later changes to the alert rule or webhook payload shape — verify this path end-to-end again right before the demo, not just when first built
- [ ] **GenAI semconv attributes:** Often copied from a first-found blog example — verify attribute names actually match the current OTel GenAI semconv registry, and that they're consistent between the RAG app and Agent K's own self-telemetry

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|----------------|-----------------|
| SigNoz/ClickHouse resource starvation discovered mid-week | LOW | Bump Docker Desktop memory allocation, restart the stack — usually resolves within an hour once diagnosed |
| Rollback executor using `restart` instead of `up -d` discovered late | LOW | Single-line fix once diagnosed; the expensive part is *discovering* it, not fixing it — hence prioritizing the health-check-then-verify step early |
| Clean-machine rebuild exceeds 15 minutes, discovered Day 6 | MEDIUM-HIGH | Identify the largest single time cost (usually model download or image build) and cut it: swap to a smaller embedding model, pre-bake the model into the image, reduce corpus seed size — requires a same-day decision, budget a half-day buffer for this specifically |
| Docker-socket-mounted Agent K architecture discovered as a security concern late | MEDIUM | Refactor Agent K to run as a host process instead of containerized, or scope the mount read-only and document the limitation honestly in the submission — cheaper than it sounds if caught before the rollback executor has grown complex |
| Groq rate limits hit during eval day itself | MEDIUM | Switch to the pre-tested Cerebras overflow path — this is only a fast recovery if Cerebras was actually verified working in advance (see Pitfall 8); if not pre-tested, this becomes a HIGH-cost same-day scramble |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|-------------------|----------------|
| SigNoz/ClickHouse resource starvation | Day 1 infra standup | Bare SigNoz UI loads and accepts a synthetic test trace with zero app code involved |
| Traces not reaching SigNoz (port/protocol/auth confusion) | Instrumentation setup phase | Console-exporter check passes before OTLP-to-SigNoz check is attempted |
| GenAI semconv attribute drift | RAG-app instrumentation + Agent K self-telemetry phases | Shared attribute-naming helper used by both systems; attributes visible/filterable in SigNoz UI |
| Orphaned background-task spans | Agent K core loop / Law 1 phase | Investigation spans verified as children of (or linked to) the triggering alert trace in SigNoz, not appearing as new root traces |
| `restart` vs `up -d` rollback bug | Rollback executor phase | Executor's post-recreate check confirms the image tag actually changed (e.g., via `docker inspect`), not just that a command was run |
| Docker-socket privilege escalation | Rollback executor design phase | Architecture decision (host-process vs. containerized Agent K) documented and, if containerized, socket access scoped/justified in writing |
| MCP stdio stdout corruption | MCP integration phase | All server-side logging routed to stderr; a stray `print()` sweep done once before first real MCP call |
| Groq free-tier rate limits vs. eval harness batch pattern | Evaluation harness phase | Full 12-run batch pattern executed at least once before final eval day with real rate limits, Cerebras fallback proven working |
| Untested loop-breaker/cost-watchdog | Agent K core loop phase | At least one adversarial test scenario forces each guardrail to fire and the escalation-to-human path is exercised |
| Clean-machine rebuild exceeding 15 minutes | Dedicated Day 5-6 checkpoint, separate from Foundry authoring | Timed rebuild on a machine/VM with cleared Docker/pip/model caches, under 15 minutes |
| Infra/instrumentation novelty underestimated in roadmap allocation | Roadmap/phase-sequencing itself | Day-by-day plan gives disproportionate buffer to SigNoz/OTel/Foundry/MCP phases relative to their apparent feature size, and sequences them earliest |

## Sources

- [OpenTelemetry GenAI Semantic Conventions registry](https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/) — official, MEDIUM confidence
- [OpenTelemetry for LLMs: Complete SRE Guide (openobserve.ai)](https://openobserve.ai/blog/opentelemetry-for-llms/) — web, MEDIUM (cross-checked)
- [OpenTelemetry FastAPI Instrumentation docs](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html) — official, MEDIUM
- [Auto instrumentation of FastAPI not working on 1.26.0 — GH issue #4111](https://github.com/open-telemetry/opentelemetry-python/issues/4111) — official repo issue, MEDIUM
- [OpenTelemetry Psycopg2/Psycopg Instrumentation docs](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/psycopg2/psycopg2.html) — official, MEDIUM
- [SigNoz: Need some help with SigNoz and OTel collector setup — GH issue #6750](https://github.com/SigNoz/signoz/issues/6750) — official repo issue, MEDIUM
- [SigNoz OpenTelemetry Collector Configuration docs](https://signoz.io/docs/opentelemetry-collection-agents/opentelemetry-collector/configuration/) — official, MEDIUM
- [SigNoz/foundry GitHub repo](https://github.com/SigNoz/foundry) — official, MEDIUM
- [Introducing SigNoz Foundry (signoz.io blog)](https://signoz.io/blog/introducing-signoz-foundry/) — official, MEDIUM
- [foundry/docs/reference/cli.md](https://github.com/SigNoz/foundry/blob/main/docs/reference/cli.md) — official, MEDIUM
- [Webhook alert channel GET vs POST — GH issue #5735](https://github.com/SigNoz/signoz/issues/5735) — official repo issue, MEDIUM
- [Webhook Alert Channel Getting 401 — GH issue #7091](https://github.com/SigNoz/signoz/issues/7091) — official repo issue, MEDIUM
- [alerts fail "stage for receiver missing" — GH issue #10106](https://github.com/SigNoz/signoz/issues/10106) — official repo issue, MEDIUM
- [Multi-threshold alerts channel bug — GH issue #10591](https://github.com/SigNoz/signoz/issues/10591) — official repo issue, MEDIUM
- [modelcontextprotocol/python-sdk GitHub repo](https://github.com/modelcontextprotocol/python-sdk) — official, MEDIUM
- [MCP Transports specification](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports) — official, MEDIUM
- [MCP Transports Compared: stdio vs SSE vs Streamable HTTP](https://rollbrains.com/mcp/mcp-transports-compared/) — web, LOW-MEDIUM
- [Docker Compose restart policy docs / Baeldung](https://www.baeldung.com/ops/docker-compose-restart-policies) — web, MEDIUM
- [Docker compose update (and rollback) — kkovacs.eu](https://kkovacs.eu/docker-compose-rollback/) — web, LOW
- [Docker Security — OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html) — official/authoritative, MEDIUM
- [Why is Exposing the Docker Socket a Really Bad Idea? — Quarkslab](https://blog.quarkslab.com/why-is-exposing-the-docker-socket-a-really-bad-idea.html) — web, MEDIUM
- [Groq Rate Limits — GroqDocs](https://console.groq.com/docs/rate-limits) — official, MEDIUM
- [Groq Free Tier Limits 2026 — TokenMix](https://tokenmix.ai/blog/groq-free-tier-limits-2026) — web, LOW-MEDIUM (cross-checked against official docs link)
- [How to Trace FastAPI Background Tasks with OpenTelemetry Spans — OneUptime](https://oneuptime.com/blog/post/2026-02-06-trace-fastapi-background-tasks-opentelemetry/view) — web, MEDIUM
- [Exclude background tasks from request duration — GH issue #1684](https://github.com/open-telemetry/opentelemetry-python-contrib/issues/1684) — official repo issue, MEDIUM
- [AI Agent Infinite Loop Detection & Prevention — Inkog](https://inkog.io/glossary/infinite-loop-ai-agent) — web, LOW
- [How to Prevent Infinite Loops and Spiraling Costs in Autonomous Agent Deployments — Codieshub](https://codieshub.com/for-ai/prevent-agent-loops-costs) — web, LOW
- [Install SigNoz on Docker Standalone docs](https://signoz.io/docs/install%2Fdocker/) — official, MEDIUM
- Hackathon scope-creep / time-management general advice (Asana, LinkedIn, freeCodeCamp/Medium) — web, LOW confidence, treated as generic supporting context only, not load-bearing for any specific pitfall claim

---
*Pitfalls research for: Agent K — SigNoz-based incident-response agent, 7-day hackathon build*
*Researched: 2026-07-20*

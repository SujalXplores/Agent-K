# Agent K, explained

*A walkthrough of what we built, why, how it works, and what it can actually do
today. Written 2026-07-25, day 6 of a 7-day build.*

---

## 1. The problem

When a production service breaks at 3am, a human on-call engineer does roughly this:

1. Reads the alert
2. Opens the observability tool, queries traces/logs/metrics
3. Forms a theory about what broke
4. Decides whether to act (roll back?) or escalate
5. Verifies the fix worked

That takes 20-40 minutes, most of it spent clicking through dashboards. The obvious
idea is "let an LLM do it." The obvious problem is that **you cannot trust an LLM
with production**. Two specific failures:

- **It makes things up.** An LLM will confidently state a root cause it has no
  evidence for. In an incident, a plausible-sounding wrong answer is worse than no
  answer, because someone acts on it.
- **It can't be given a rollback button.** "The model decided to roll back" is not
  an acceptable audit trail. Nobody can review a decision that lives inside a
  prompt.

Most "AI SRE agent" demos hand-wave both. Agent K's entire premise is that you fix
them *in code*, not in prompting.

---

## 2. What Agent K is

An incident-response agent for a FastAPI RAG support service, built for the
"Agents of SigNoz" hackathon (Track 01 — AI & Agent Observability).

When a SigNoz alert fires, Agent K:

- investigates by querying SigNoz through its MCP server
- publishes **only** claims backed by a resolvable SigNoz link
- executes a rollback **only** if a deterministic, zero-LLM policy gate allows it
- records its own token cost, duration, and query behaviour as telemetry

**The core value:** nothing is trust-the-model, everything is prove-it-in-telemetry.

---

## 3. The Three Laws (the actual idea)

This is the part that matters. Each law is *enforced by code*, not requested in a
prompt — which means each is testable, and we can point a judge at the test.

### Law 1 — No claim without evidence

Every claim carries: claim text, a confidence value, the SigNoz query used, the
time range, and a resolvable deep link.

A claim with an empty evidence list is **stripped before a human ever sees it** —
enforced in the investigation loop *and again* in the report renderer. The report
page is the publication boundary, so that's where the rule has to actually hold.
A test writes an unevidenced claim straight into the store, bypassing the loop
entirely, and proves it never reaches HTML.

Confidence is **hybrid-scored**: the LLM proposes a number, then code adjusts it
based on evidence strength (deployment marker present, how many corroborating
queries). The model doesn't get the last word on its own credibility. It's also
capped below 100% — no evidence set justifies claiming certainty.

### Law 2 — No action without a policy gate

`app/policy.py` runs **six checks, with zero LLM involvement**:

| Check | Question |
|---|---|
| `slo_breach` | Is the error budget actually burning? |
| `allowlist` | Is this action permitted? (exactly **one** action exists: rollback) |
| `cooldown` | Did we already act on this service recently? |
| `confidence` | Is the best evidenced claim ≥ 0.70? |
| `deployment_related` | Was the cause a deployment? |
| `sandbox_scope` | Is the target inside the permitted blast radius? |

All six must pass. Any failure → **no action**, plus an evidence-linked
recommendation for a human.

The zero-LLM property is proven two ways: a runtime guard that fails the test if
`app.llm.generate` is called, and an AST walk of the module's real imports.
(My first attempt used a substring grep — it matched the module's own docstring
explaining why the import is absent. AST parsing is the honest check.)

**Everything unknown fails closed.** Unreadable burn rate → 0.0 → denied. Unknown
incident type → denied. Unparseable recovery metric → "not verified".

### Law 3 — No self without telemetry

Agent K instruments itself the way it instruments the app: tokens, duration, MCP
query count, query failures, hypothesis confidence — all spans in SigNoz.

Two guardrails run inside the loop:

- **Loop breaker** — the same query repeated past a threshold stops the
  investigation and escalates with whatever partial evidence exists
- **Cost watchdog** — a token budget overrun does the same

An investigation stopped by either is marked **incomplete** and never reaches the
action stage. It didn't finish looking; it doesn't get to act.

---

## 4. How it's put together

### The system under observation

A real RAG service, not a toy: FastAPI + PostgreSQL/pgvector + local
`sentence-transformers` embeddings + Groq for generation. `POST /ask` retrieves
docs by vector similarity, builds a prompt, calls the LLM, returns a grounded
answer with sources.

Four failure scenarios can be toggled live via `POST /admin/flags`, no restart:

| Scenario | What breaks | Deployment-class? |
|---|---|---|
| `prompt_regression` | broken prompt template | **yes** |
| `retry_storm` | tight timeouts → retry spiral | **yes** |
| `retrieval_latency` | slow pgvector query | no |
| `db_pool_exhaustion` | starved connection pool | no |

That yes/no column is load-bearing: the policy gate's `deployment_related` check
reads *the same set* the marker emitter uses. So "2 approve, 2 deny" is a
consequence of one shared definition, not two lists that happen to agree today.

### The investigation flow

```
SigNoz alert
    │
    ▼
POST /alerts/webhook ──► background task (HTTP returns immediately)
    │
    ▼
┌─ investigation loop (plain Python state machine, no agent framework) ─┐
│                                                                       │
│  1. error traces          ─┐                                          │
│  2. deployment markers     │─ via SigNoz MCP, one query per iteration  │
│  3. logs                   │  (each hashed → loop-breaker signal)      │
│  4. error-rate aggregate  ─┘                                          │
│                                                                       │
│  → LLM forms a hypothesis → code recalibrates its confidence          │
│  → stop when confident enough (but never after only one query)        │
└───────────────────────────────────────────────────────────────────────┘
    │
    ▼
strip unevidenced claims  (Law 1)
    │
    ▼
evaluate_policy() — six checks, zero LLM  (Law 2)
    │
    ├── denied ──► evidence-linked recommendation, no action
    │
    └── approved ──► POST /rollback ──► deployer sidecar
                          │
                          ▼
                    wait, re-query SigNoz, verify recovery independently
    │
    ▼
/report/{id}
```

A deliberate choice: **no agent framework** (no LangGraph, no CrewAI). A plain
`enum`-driven loop with explicit transitions. Frameworks make it *harder* to prove
"code-enforced, not trust-the-model" to a judge, because the enforcement gets
buried in someone else's abstraction.

### The privilege boundary

This is the design decision I'm most confident about.

**Agent K never holds the Docker socket.** A separate `deployer` sidecar is its
sole holder. Agent K's entire ability to change the world is:

```
POST /rollback   (authenticated, EMPTY BODY)
```

No image name. No service name. No command. The sidecar decides everything —
which service, which known-good tag, which compose command. It captures the
current image tag *before* mutating, holds a concurrency lock (409 if a rollback
is in flight), runs a hardcoded argv through `create_subprocess_exec` (no shell,
ever), and emits a deployment marker on success *and* failure.

So "the action stayed inside the sandbox" isn't a promise Agent K makes about
itself. It's a structural fact about what it is physically able to request.

The gate is also checked **twice** — once by the investigation loop, once
independently inside `execute_rollback`. That redundancy is the difference between
"we remember to call the gate" and "the gate cannot be bypassed."

### The report page

`/report/{id}` renders one incident: claims strongest-first with evidence links,
all six policy checks with pass/fail and reasoning, the action outcome, and Agent
K's own cost numbers. `/report` lists all investigations.

Two rendering rules worth knowing:

- **A denied verdict is styled informational, never red.** Agent K declining to
  act is the product *working*. The failure mode this page exists to prevent is
  someone skimming it and reading "denied" as "broken".
- **An executed rollback whose recovery couldn't be verified is never shown as
  success.** It says so explicitly, because "compose reported success" is not
  "the incident is over".

---

## 5. What it can actually do today

**The full chain runs live, end to end.** Verified 2026-07-25:

```
real alert → real MCP evidence → real LLM hypothesis → real policy verdict → report
```

A concrete run: 2 MCP queries, 0 failures, verdict **approved**, all six checks
passed, two evidence-backed claims, both links resolving.

Working and verified against live infrastructure:

- SigNoz self-hosted via Foundry, ingesting traces/metrics/logs from the app
- `/ask` answering real questions from the real corpus via real Groq
- All four failure scenarios toggling live, with deployment markers queryable
  back out of SigNoz
- MCP client pulling real evidence (`signoz-mcp-server` v0.9.0, 41 tools)
- The investigation state machine reaching terminal states
- The policy gate producing approve/deny verdicts on live evidence
- The report page rendering real investigations
- The deployer sidecar running and healthy

**Status: 36/50 requirements. 211 tests passing.**

---

## 6. What it can't do yet

Being straight about this, because the gap matters more than the 72%:

| Gap | Impact |
|---|---|
| **No rollback has ever executed** | Sidecar is up and tested, but the app isn't built into versioned images yet, so there's nothing to roll back *to* |
| **No dashboard** | 0/5. The judged Agent Health / Action Audit Trail views don't exist |
| **No eval runs** | 0/4. Diagnosis accuracy is genuinely **unmeasured** |
| **Only Groq proven** | The three-provider switch is coded but only one path exercised |
| **Link checker is unsound** | See below |

And the honest one: **diagnosis accuracy looks shaky.** In a live run it answered
`retry_storm` where `prompt_regression` was injected. Partly stale data, partly
genuine model error. We should expect less than 4/4 and report whatever we get.

---

## 7. What going live actually taught us

Every phase was built with offline tests and a mocked live half. When we finally
connected everything, **six real defects surfaced in one session** — none of which
any offline test could have found. This is the most interesting part of the build.

1. **Every MCP tool name was wrong.** We'd guessed `query_traces`, `query_logs`,
   `query_metrics`. The real ones are `signoz_search_traces`, `signoz_search_logs`,
   `signoz_aggregate_traces`. A wrong name doesn't crash — it returns an error
   result that reads exactly like "no evidence found". Every investigation would
   have escalated, the gate would have approved nothing, and the demo would have
   been silently empty.

2. **The loop breaker was structurally dead.** Our own time-window code put a
   moving millisecond into the query arguments, so two *identical* queries hashed
   differently and the breaker could never fire. It only passed tests when
   iterations landed in the same millisecond.

3. **Groq rejected the prompt entirely** — `413, Limit 6000, Requested 8424`. Raw
   trace rows carry every span attribute, nearly all null.

4. **The investigation stopped after one query, every time.** The model readily
   returns 0.9+ confidence, which cleared the stop threshold on iteration 1 — so it
   never looked at the deployment marker that decides the whole policy verdict.

5. **The test suite was writing into the live SigNoz.** Importing the app calls
   `setup_telemetry()`, so every pytest span shipped to the real backend — and
   **Agent K then investigated pytest's noise as incident evidence**, and
   misdiagnosed on that basis.

6. **We were emitting a fabricated evidence link.** `/deployments` doesn't exist in
   SigNoz. It passed our link checker because SigNoz is a single-page app that
   returns HTTP 200 for *every* path — so the status code said "resolved" while a
   human clicking it landed nowhere. That is precisely the failure Law 1 exists to
   prevent, hidden by the very method meant to catch it.

If there's one lesson: **an offline test suite tells you your code does what you
think. It cannot tell you what you think is true about the world.** Six of our
assumptions about SigNoz, Groq, and our own telemetry were wrong, and all six were
invisible until something real pushed back.

---

## 8. Where things live

| Path | What |
|---|---|
| `app/main.py` | routes; order matters (routes before OTel instrumentation) |
| `app/rag.py`, `app/llm.py` | retrieval + the single OpenAI-compatible client |
| `app/flags.py` | four failure scenarios + deployment markers |
| `app/signoz_mcp.py` | the **single** MCP call site, spans + query hashing |
| `app/investigation.py` | the state machine, evidence plan, watchdogs |
| `app/claims.py` | Law 1 — schema, stripping, confidence recalibration |
| `app/policy.py` | Law 2 — the six checks, zero LLM |
| `app/rollback.py` | Agent K's whole ability to act: one HTTP call |
| `deployer/` | the sidecar; the only thing with a Docker socket |
| `app/report.py` | the human-facing report |
| `app/observability.py` | every attribute name, in one place |

Practical guides: [RUNNING-AGENT-K.md](RUNNING-AGENT-K.md) to run it,
[GETTING-KEYS.md](GETTING-KEYS.md) for credentials,
[.planning/REQUIREMENTS.md](.planning/REQUIREMENTS.md) for per-requirement status.

---

## 9. The one-paragraph version

Agent K watches a RAG service through SigNoz. When something breaks, it queries
its own telemetry through the SigNoz MCP server, forms a root-cause theory, and
publishes it — but only with a working link to the evidence behind it. If it wants
to roll back, six deterministic checks run in code with no model involved, and it
can only ever ask one sandboxed sidecar to do one hardcoded thing. It records its
own cost and behaviour as telemetry, stops itself when it loops or overspends, and
escalates to a human rather than guessing. The full chain works end to end today;
the dashboard, the evaluation runs, and one real rollback are what remain.

---
phase: 06-policy-gate-rollback-executor
plan: 01
status: complete
requirements-completed: [LAW2-01, LAW2-02, LAW2-03, LAW2-04, LAW2-05, LAW2-06, LAW2-07]
# LAW2-03/04's LIVE halves are human-verification (HV-3): no containerized rag-app
# and no versioned image tags exist yet, so no real rollback has been executed.
# See "What's not done" below.
key-files:
  created:
    - app/policy.py
    - app/rollback.py
    - deployer/__init__.py
    - deployer/constants.py
    - deployer/main.py
    - deployer/Dockerfile
    - deployer/requirements.txt
    - tests/test_policy.py
    - tests/test_rollback.py
    - tests/test_deployer.py
  modified:
    - app/observability.py
    - app/investigation.py
    - tests/test_investigation.py
    - docker-compose.yaml
    - .planning/REQUIREMENTS.md
completed: 2026-07-25
---

# Phase 6 Plan 01: Law 2 Policy Gate + Privilege-Isolated Rollback Executor

**Built the deterministic zero-LLM policy gate every action must pass, and the
`deployer` sidecar that is the sole holder of the Docker socket — so Agent K's
entire capability to change the world is one authenticated HTTP call to one
endpoint that does one hardcoded thing.**

Executed directly (no gsd discuss/plan/execute-phase), per explicit user
instruction — same mode as Phases 4 and 5.

## Design decisions (made directly, documented here instead of in a CONTEXT.md)

- **The 2-approved/2-denied split (LAW2-07) is a consequence, not a config.** The
  deployment-relatedness check reads `app.flags.DEPLOYMENT_CLASS_FLAGS` — the
  *same* set Phase 3's FLAG-06 marker emitter uses to decide whether a scenario
  gets a deployment marker at all. Two hand-maintained lists that happen to agree
  today would silently diverge later; one shared definition cannot.
- **Everything unknown fails closed.** An unreadable burn rate → 0.0 → SLO check
  fails → denied. An unrecognized incident type → denied. An unparseable recovery
  metric → `verified=False`. The alternative (optimistic defaults) would let the
  gate approve actions on evidence Agent K never actually read.
- **The gate is checked twice.** `_run_act_stage` checks `decision.approved`, and
  `execute_rollback` re-checks it independently. That redundancy is the difference
  between "we remember to call the gate" and "the gate cannot be bypassed" by a
  future caller who forgets.
- **Incomplete investigations never reach the act stage.** A loop-broken or
  cost-capped investigation stopped early by definition; acting on its half-formed
  picture is exactly what Law 3's watchdogs exist to prevent. No policy decision is
  recorded for one — honest silence rather than a verdict on evidence never gathered.
- **The sidecar duplicates two attribute-name constants rather than importing
  them.** Importing `app.observability` would drag sqlalchemy/pgvector/
  sentence-transformers/openai into the one container holding the Docker socket,
  which is precisely the blast radius the isolation boundary exists to keep small.
  D-06's single-source-of-truth is preserved by
  `test_deployment_marker_attribute_names_match_app` instead of by an import.
- **Sidecar auth fails closed, unlike the RAG app's `/admin/flags`.** An unset
  `DEPLOYER_TOKEN` makes `/rollback` return 503 rather than running open. There is
  no configuration of a socket-holding process that should be unauthenticated.
- **Cooldown starts on real execution only** — not on a denial and not on a failed
  call, so a failure stays retryable rather than being blocked by a cooldown that
  never protected anything.

## Accomplishments

- **`app/policy.py`** (LAW2-01/02/05/06): `evaluate_policy()` runs six checks —
  slo_breach, allowlist, cooldown, confidence, deployment_related, sandbox_scope —
  and returns a `PolicyDecision` carrying every field LAW2-06 enumerates plus a
  per-check breakdown. `ACTION_ALLOWLIST` has exactly one entry (LAW2-02). Denials
  carry a human-facing `recommendation` and the winning claim's evidence links
  (LAW2-05). An unevidenced claim contributes 0.0 confidence, so LAW1-02's rule
  extends to actions: a claim too weak to publish is too weak to act on.
- **`deployer/`** (LAW2-03/04): a dependency-light FastAPI sidecar with exactly one
  mutating endpoint (`POST /rollback`, empty body — the caller names no image, no
  service, no command). Captures the pre-mutation image tag *before* mutating, pins
  the known-good tag, runs a fixed argv `docker compose up -d --force-recreate`
  through `create_subprocess_exec` (no shell anywhere), holds a concurrency lock
  (409 if in flight), and emits a `deployment.marker` span on success *and* failure.
- **`app/rollback.py`** (LAW2-03/04, Agent K side): one authenticated POST, then an
  independent recovery re-query through the Phase-4 MCP wrapper after a wait. A 2xx
  from the sidecar means "compose reported success", not "the incident is over" —
  so `verified` is only True when a recovered error rate is actually read back.
- **`app/investigation.py`**: `_run_act_stage` wired into `run_investigation` inside
  the investigation span, so policy/action spans are its children and a human opening
  `agentk.investigation` sees reasoning and verdict in one trace. Guarded so an
  act-stage crash cannot destroy the Law 1/3 investigation record.
- **`app/observability.py`**: 15 policy + 6 action attribute-name constants (D-06).
- **`docker-compose.yaml`**: the `deployer` service, with the socket mount as the
  single documented privilege boundary.

## Verification

- New tests: **56** — `tests/test_policy.py` (22), `tests/test_deployer.py` (17),
  `tests/test_rollback.py` (17), plus 6 act-stage wiring tests appended to
  `tests/test_investigation.py`.
- Full offline suite: **158 passed, 1 skipped** (integration), up from 97/1 — no
  regressions.
- `docker compose config` validates.
- LAW2-01's zero-LLM claim is proven two ways: a runtime guard that replaces
  `app.llm.generate` with a function that fails the test if called, and an AST
  walk of `app/policy.py`'s real import statements. The first attempt at the
  latter was a naive substring grep, which failed against this module's own
  docstring — replaced with AST parsing, which also catches aliased imports a
  grep would miss.
- One act-stage test initially failed and the **test** was wrong, not the code: it
  used confidence 0.99 to satisfy the policy, which tripped the high-confidence
  early-stop at iteration 1 so the loop breaker never fired. Lowered to 0.1 and
  sharpened the assertion to `policy_decision is None`, which uniquely proves the
  incomplete-guard fired rather than some later check denying anyway.

## What's not done — human verification (HV-3)

The sidecar's full contract is offline-tested with the Docker layer faked, but **no
real rollback has ever been executed**, because the prerequisite does not exist:

1. **The RAG app is not containerized.** There is no Dockerfile for it and no
   `rag-app` service in `docker-compose.yaml` — it runs as a local `uvicorn`
   process. The roadmap named "versioned images existing" as a sidecar dependency
   ([ROADMAP.md](../../ROADMAP.md) Phase 6 constraint) but no phase was ever
   assigned to deliver it.
2. **No versioned image tags exist**, so there is nothing to roll back *to*.
   Cheapest path: build `agent-k-rag:v1-good` and `agent-k-rag:v2-broken` from the
   same source with the `prompt_regression` flag default baked ON in v2 — no second
   codebase needed.
3. `DEPLOYER_TOKEN` must be added to `.env.example` by hand (this environment's
   permissions block edits to `.env*` files).

Until those land, `LAW2-03`/`LAW2-04` are code-complete, not verified. Steps are
written up in [RUNNING-AGENT-K.md](../../../RUNNING-AGENT-K.md).

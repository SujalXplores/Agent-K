# Agent K — Submission

**Hackathon:** Agents of SigNoz — Track 01, AI & Agent Observability
**Repo:** this repository
**Demo video:** _TODO — paste link_
**Blog post:** _TODO — paste link (SUB-02)_

---

## AI assistant usage disclosure (SUB-01)

**This project was built with heavy use of an AI coding assistant — Anthropic's
Claude Code — and we are disclosing that up front, per hackathon rules.**

What the assistant was used for:

- **Planning and architecture.** The roadmap, phase breakdown, and requirement
  traceability were drafted with Claude Code and reviewed by the team.
- **Implementation.** The RAG service, OpenTelemetry instrumentation, SigNoz MCP
  wrapper, Agent K investigation loop, the Law 2 policy gate, the privilege-isolated
  deployer sidecar, and the incident report page were all written with Claude Code
  in the loop, under human direction and review.
- **Tests.** The offline test suite (188 tests) was largely assistant-written,
  including the adversarial tests that force the loop breaker and cost watchdog to
  fire, and the AST-based check that proves the policy gate imports no LLM client.
- **Documentation.** `RUNNING-AGENT-K.md`, `SIGNOZ-RUNBOOK.md`, and the per-phase
  build summaries were assistant-drafted from the actual build.

What the assistant was **not** used for:

- Agent K's own runtime does **not** call Claude or any Anthropic API. The shipped
  agent uses only free-tier providers (Groq primary, Cerebras overflow, Gemini Flash
  fallback) behind one OpenAI-compatible client, and local `sentence-transformers`
  embeddings. Claude Code is a **build-time tool only** and is not part of the
  running system or its cost model.

Commits made with assistant involvement carry a `Co-Authored-By: Claude
<noreply@anthropic.com>` trailer where the workflow recorded one. Note this trailer
undercounts: earlier phases were also assistant-assisted without the trailer being
applied, which is why this disclosure is written broadly rather than as a commit count.

---

## What Agent K is

A code-enforced incident-response agent for a FastAPI RAG support service. When a
SigNoz alert fires, Agent K investigates through the SigNoz MCP server, publishes only
evidence-backed root-cause claims, executes a sandboxed rollback **only** when a
code-based policy allows it, and records its own cost and behaviour as telemetry.

### The Three Laws

1. **No claim without evidence.** Every published claim carries claim text, a
   code-recalibrated confidence, the SigNoz query used, the time range, and a
   resolvable deep link. A claim with no evidence is stripped before it reaches a
   human — enforced at the investigation loop *and* again at the report renderer.
2. **No action without a policy gate.** Six deterministic checks, zero LLM calls.
   The action allowlist has exactly one entry. The gate's zero-LLM property is proven
   by a runtime guard and an AST walk of the module's imports, not by convention.
3. **No self without telemetry.** Token counts, duration, MCP query counts and
   hypothesis confidence are emitted as spans. A loop breaker stops repeated identical
   queries; a cost watchdog stops budget overruns. Both escalate to a human rather
   than continuing on a half-formed picture.

---

## Honest status

_TODO before submitting: replace this section with the real eval results (EVAL-01/02)
and keep the failures in. Do not inflate beyond "4/4 on four controlled scenarios."_

See `SUBMISSION.md` (this file) for per-requirement status.

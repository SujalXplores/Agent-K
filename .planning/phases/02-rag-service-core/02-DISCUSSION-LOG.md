# Phase 2: RAG Service Core - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-23
**Phase:** 2-rag-service-core
**Areas discussed:** Support corpus domain, Answer response contract, No-match/empty retrieval behavior, Prompt template & persona

---

## Gray Areas Presented

| Option | Description | Selected |
|--------|-------------|----------|
| Support corpus domain | What fictional product/company do the 50-200 synthetic support docs belong to? | |
| Answer response contract | Plain answer text only, or answer + cited source doc references? | |
| No-match/empty retrieval behavior | What happens when no doc is a good match — refuse, answer with caveat, or something else? | |
| Prompt template & persona | System prompt voice/style for the generation step | |

**User's choice:** Freeform response — declined to pick individual areas and instead delegated all Phase 2 decisions to Claude: *"give recommendations based on the .planning folder content and that stays on track with all the phases. i genuinely dont have any idea about what to choose or what to target so based on the project target take the necessary decisions and your decisions should be made by keeping hackathon in mind."*

**Notes:** No per-area discussion loop was run since the user opted out of choosing. Claude synthesized recommendations for all four presented areas, plus GenAI instrumentation and LLM provider abstraction details, directly from PROJECT.md/REQUIREMENTS.md/ROADMAP.md/CLAUDE.md and hackathon judging criteria. Full rationale for each decision (D-01 through D-08) is recorded in `02-CONTEXT.md`.

---

## Claude's Discretion

Per the user's blanket delegation, effectively the entire phase's implementation decisions were left to Claude's judgment, anchored to project docs rather than invented. Additionally, within the decisions made:
- Doc-authoring method (hand-written vs. templated/generated)
- Exact module layout inside `app/` beyond the Phase 1 scaffold
- Embedding model choice (MiniLM default, swap to bge-small only if retrieval quality looks weak in rehearsal)

## Deferred Ideas

None — the user did not raise any new-capability ideas or scope additions during this discussion.

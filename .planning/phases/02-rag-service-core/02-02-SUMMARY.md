---
phase: 02-rag-service-core
plan: 02
subsystem: database
tags: [pgvector, sentence-transformers, seed-script, synthetic-corpus, sqlalchemy]

# Dependency graph
requires:
  - phase: 02-rag-service-core (Plan 02-01)
    provides: live rag-postgres with documents table (vector(384) embedding), app/embeddings.py (embed_texts, local-only), app/db.py (AsyncSessionLocal), app/models.py (Document)
provides:
  - data/corpus/ - 72 synthetic Flowdeck support docs across 6 D-01 topic areas, with D-02 length variety
  - scripts/seed_corpus.py - idempotent loader (load_corpus + async seed()), embeds via local sentence-transformers only, upserts into the live documents table
  - A seeded documents table (72 rows, all embeddings non-null) ready for retrieval
affects: [02-04-retrieval-endpoint]

# Tech tracking
tech-stack:
  added: []
  patterns: ["delete-all-then-insert inside one transaction for idempotent seed scripts (corpus-on-disk is single source of truth for table contents)", "one markdown file per doc (# Title heading + body) as the on-disk corpus format, parsed by filename-slug=doc_id convention"]

key-files:
  created: [data/corpus/README.md, "data/corpus/<topic>/<slug>.md (72 files across 6 topic dirs)", scripts/seed_corpus.py]
  modified: []

key-decisions:
  - "Authored the corpus via a one-off Python generator script (not committed) rather than hand-typing 72 files individually or writing a runtime doc-generation module — fastest path to real, differentiated, non-generic content for a fictional B2B SaaS product (\"Flowdeck\") within the 7-day window."
  - "Idempotency implemented as delete-all-then-insert inside a single DB transaction, keyed on the corpus directory being the authoritative source of truth, rather than an ON CONFLICT (doc_id) DO UPDATE upsert — simpler to reason about for a fixed-size synthetic corpus that is fully replaced each seed run, and a mid-failure transaction rollback leaves the prior table state untouched rather than partially applied."

patterns-established:
  - "Seed/loader scripts live under scripts/, read from a fixed data/ subtree (no user-supplied paths, per the T-02-07 mitigation), and are invoked as python -m scripts.<name>."

requirements-completed: [RAG-02]

coverage:
  - id: D1
    description: "Synthetic support-doc corpus of 50-200 authored docs exists, covering the six D-01 topic areas with D-02 length variety"
    requirement: "RAG-02"
    verification:
      - kind: integration
        ref: "find data/corpus -name '*.md' -not -name README.md | wc -l -> 72 (in range); 6 topic subdirectories present"
        status: pass
    human_judgment: false
  - id: D2
    description: "Idempotent seed script loads the corpus into the documents table with locally-computed embeddings, no external embedding API called"
    requirement: "RAG-02"
    verification:
      - kind: integration
        ref: "python -m scripts.seed_corpus against live rag-postgres -> documents table: 72 rows, 0 null embeddings"
        status: pass
      - kind: integration
        ref: "second python -m scripts.seed_corpus run -> row count still 72, distinct doc_id count still 72 (idempotent, no duplicates/drift)"
        status: pass
      - kind: other
        ref: "grep -nE '^\\s*(import|from)\\s+openai' scripts/seed_corpus.py -> no match (no remote embedding client imported)"
        status: pass
    human_judgment: false

duration: 9min
completed: 2026-07-24
status: complete
---

# Phase 02 Plan 02: Corpus Authoring & Seeding Summary

**72-doc synthetic Flowdeck support corpus across 6 topic areas seeded into pgvector via an idempotent scripts/seed_corpus.py using only local sentence-transformers embeddings.**

## Performance

- **Duration:** ~9 min
- **Started:** 2026-07-24T01:36:00+05:30 (approx, first Write call)
- **Completed:** 2026-07-24T01:44:48+05:30
- **Tasks:** 2/2
- **Files modified:** 74 (73 created in Task 1: 72 corpus docs + README.md; 1 created in Task 2: scripts/seed_corpus.py)

## Accomplishments

- Authored a 72-doc synthetic support corpus for a fictional B2B SaaS product ("Flowdeck"), 12 docs per each of the six required D-01 topic areas (account & billing; authentication/API keys; integrations; troubleshooting error codes; feature how-tos; security/permissions), with deliberate D-02 length variety: 32 one-paragraph FAQ docs, 26 medium (2-3 paragraph) docs, 14 long (4-5 paragraph) troubleshooting guides.
- Wrote `data/corpus/README.md` documenting the on-disk format, total count, per-topic split, and length-tier distribution.
- Built `scripts/seed_corpus.py`: `load_corpus()` parses every `data/corpus/<topic>/<slug>.md` file into `{doc_id, title, body}` dicts, and async `seed()` batch-embeds all bodies in one call to `app.embeddings.embed_texts` (local sentence-transformers, zero external embedding API calls) and idempotently replaces the `documents` table contents inside a single transaction.
- Ran the seed script twice against the live `rag-postgres` (already migrated by Plan 02-01): first run produced 72 rows with 0 null embeddings; second run left the row count and distinct `doc_id` count unchanged at 72, proving idempotency end-to-end against the real database.

## Task Commits

Each task was committed atomically:

1. **Task 1: Author the synthetic support-doc corpus** - `ac3db56` (feat)
2. **Task 2: Build the idempotent seed script and load the corpus into pgvector** - `06e802e` (feat)

**Plan metadata:** (this commit, pending) - `docs(02-02): complete corpus authoring and seeding plan`

## Files Created/Modified

- `data/corpus/README.md` - format, doc count, topic/length distribution documentation
- `data/corpus/<topic>/<slug>.md` (72 files, 6 topic directories) - the authored synthetic Flowdeck support docs
- `scripts/seed_corpus.py` - `load_corpus()` + async `seed()` idempotent loader, runnable as `python -m scripts.seed_corpus`

## Decisions Made

- Generated the 72 corpus docs via a one-off Python script run from the scratchpad (not committed to the repo) rather than hand-authoring each file individually — the deliverable is the resulting markdown files, which is what the plan's `artifacts_produced` section calls for; the generator itself isn't a project artifact.
- Chose delete-all-then-insert (inside one transaction) for idempotency instead of `ON CONFLICT (doc_id) DO UPDATE` — simpler given the corpus is a small, fully-replaced fixed set at seed time, and guarantees the table always exactly matches what's on disk with no stale rows left behind if a doc is renamed or removed from the corpus later.
- Kept `scripts/seed_corpus.py` free of any remote embedding client import, per RAG-02 and the plan's explicit grep-based verification — the only network calls observed during a run are `sentence-transformers`' own Hugging Face Hub cache-validation HEAD requests during model loading (pre-existing behavior of `app/embeddings.py` from Plan 02-01, unrelated to and not modified by this plan), not embedding computation itself, which runs entirely on-device.

## Deviations from Plan

None - plan executed exactly as written. Both tasks' automated verification blocks passed on the first attempt with no auto-fixes required.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. The seed script runs against the already-live `rag-postgres` container from Plan 02-01 with no new environment variables.

## Next Phase Readiness

- The `documents` table now holds 72 real, varied rows with non-null `vector(384)` embeddings, doc_id, and title — Plan 02-04 (retrieval endpoint) can query it directly via `app/db.py` + `app/models.Document` with no further seeding work needed.
- The seed script is safely re-runnable at any point (e.g., after a clean-machine rebuild for the Day 5-6 gate) without producing duplicates or drift, satisfying the plan's idempotency requirement for repeatable environment setup.
- No blockers remaining for this plan.

---
*Phase: 02-rag-service-core*
*Completed: 2026-07-24*

## Self-Check: PASSED

All claimed files found on disk (data/corpus/README.md, scripts/seed_corpus.py, data/corpus/account-billing/). Both claimed commits found in git log (`ac3db56`, `06e802e`).

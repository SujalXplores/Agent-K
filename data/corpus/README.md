# Support Doc Corpus

Synthetic support-doc corpus for **Flowdeck**, a fictional generic B2B
project/workflow-management SaaS product, authored for Agent K's RAG
service (RAG-02). All content is invented — zero real customer data,
zero PII, zero third-party/scraped material — matching the project's
locked "synthetic corpus only" constraint (see `.claude/CLAUDE.md`).

## Format

One markdown file per doc, at `data/corpus/<topic>/<slug>.md`:

- The filename slug (without `.md`) is the doc's stable `doc_id`.
- The first line is a level-1 heading (`# Title`) — the doc's `title`.
- Every remaining line (after the blank line following the heading) is
  the doc's `body`, one or more paragraphs separated by a blank line.

`scripts/seed_corpus.py`'s `load_corpus()` parses exactly this shape:
first line strips the leading `# ` to become `title`, the rest
(trimmed) becomes `body`, and the directory name becomes the doc's
topic grouping (not currently a separate DB column — topic is implicit
in the corpus layout, `doc_id`/`title`/`body` are what's persisted per
the `documents` table schema from Plan 02-01).

## Total Doc Count

**72 docs** (within the 50-200 range required by RAG-02 / Plan 02-02's
`must_haves`).

## Topic Coverage (D-01)

All six required topic areas are covered, 12 docs each:

| Topic directory | Topic area (D-01) | Doc count |
|---|---|---|
| `account-billing/` | Account & billing | 12 |
| `authentication-api-keys/` | Authentication / API keys | 12 |
| `integrations/` | Integrations | 12 |
| `troubleshooting-error-codes/` | Troubleshooting error codes | 12 |
| `feature-how-tos/` | Feature how-tos | 12 |
| `security-permissions/` | Security / permissions | 12 |

## Length Distribution (D-02)

Length is measured in paragraph count per doc (the seed script does
not chunk — each doc is embedded whole, per D-03):

| Tier | Paragraphs | Doc count | Description |
|---|---|---|---|
| Short | 1 | 32 | One-paragraph FAQ-style answers |
| Medium | 2-3 | 26 | Multi-paragraph explanations with nuance/caveats |
| Long | 4-5 | 14 | Full troubleshooting guides with numbered root-cause / resolution steps |

This deliberate variety (not every doc the same size) is load-bearing
for Phase 3's retrieval-latency and prompt-regression failure
scenarios, which need visibly non-trivial retrieval/generation
behavior to demo convincingly — uniform tiny docs would make the
pgvector retrieval step look trivial regardless of whether it's
actually working correctly.

## Per-Topic Breakdown

Every topic directory contains a mix of all three length tiers (not
grouped by tier), so topic coverage and length variety are orthogonal:

| Topic | Short | Medium | Long |
|---|---|---|---|
| account-billing | 6 | 4 | 2 |
| authentication-api-keys | 5 | 5 | 2 |
| integrations | 5 | 5 | 2 |
| troubleshooting-error-codes | 5 | 4 | 3 |
| feature-how-tos | 6 | 4 | 2 |
| security-permissions | 4 | 5 | 3 |

## Authoring Method

Hand-authored per-doc content, generated into files via a one-off
Python script (not committed to this repo — the deliverable is the
resulting `.md` files, not the generator). Content is grounded in a
single consistent fictional product ("Flowdeck") so cross-references
between docs (e.g. a troubleshooting guide pointing back to a setup
guide by slug) are coherent, which also supports a believable retrieval
demo.

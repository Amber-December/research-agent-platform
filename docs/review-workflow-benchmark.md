# Literature Review Workflow Benchmark

This note records the `/review` practices adopted from the local reference project
`Auto-claude-code-research-in-sleep` and the corresponding platform implementation.

## Reference Strengths

| Reference practice | Why it matters | Platform implementation |
|---|---|---|
| Search protocol before retrieval | Prevents sending the user's full instruction as one noisy query | `bib/RESEARCH_BRIEF.md` must contain 4-6 `Q1: ...` query variants |
| Local-library-first retrieval | Uses the researcher's owned PDFs and notes before broad discovery | Relevant, extractable files under `*/uploads/` enter the admitted evidence set |
| Layered multi-source search | One provider outage does not invalidate the whole review | OpenAlex, Semantic Scholar, and arXiv run per query; configured WoS/CNKI are added automatically |
| Alias expansion and multiple angles | Recovers terminology differences across disciplines and languages | Core topic, canonical English term, aliases, recent-review query, and foundational query |
| DOI/arXiv/title de-duplication | Avoids counting preprint and formal versions as independent support | Identifier-first merge with normalized-title fallback |
| Relevance filtering | Stops keyword-adjacent papers entering synthesis | Phrase/two-term relevance rule plus scored admission threshold |
| Foundational/recent and formal/preprint split | Produces a field structure instead of a search-result summary | Required sections and synthesis instructions in the workflow registry |
| Paper-level extraction | Makes method, setting, result, and limitation comparable | Required paper evidence table before narrative synthesis |
| Mechanical evidence audit | Detects missing and invented citations cheaply | Stable `[Pxxx]` IDs, local path citations, `CITATION_AUDIT.json`, and `REVIEW_COVERAGE.json` |
| Fail-closed evidence gate | Avoids generating confident gaps from sparse or failed retrieval | At least six traceable external or relevant local sources are required for formal synthesis |

## Current `/review` Contract

1. Clean the user's objective to a core topic.
2. Generate a bounded review protocol and 4-6 multilingual queries.
3. Extract topic-relevant local uploads and query all available scholarly providers.
4. Merge duplicates, score relevance, assign stable IDs, and write retrieval-quality artifacts.
5. Stop when fewer than six traceable sources are admitted.
6. Synthesize admitted papers by technical axis, not retrieval order.
7. Build claim-level evidence and gap maps with stable source pointers.
8. Audit unknown IDs, local-path use, traceability, and reference coverage.

## Deliberate Differences

- The platform does not require the user to enter source or search-count parameters; it selects conservative defaults.
- Missing providers are reported rather than silently treated as successful coverage.
- Local files count toward the gate only when text extraction succeeds and the content or filename matches the review protocol.
- Provider failures and sparse retrieval are coverage limitations, never evidence of a research gap.
- All artifacts remain inside `agent-workspace/<user_id>/<session_id>/bib/`; earlier same-session review outputs are retained under `bib/archive/` before a new review starts.

## Remaining Limits

- OpenAlex, Semantic Scholar, and arXiv mostly provide metadata and abstracts; definitive claims still require full-text verification.
- Citation-ID checks establish source existence and reference closure, not semantic entailment of every claim.
- Database coverage depends on configured provider access. WoS and CNKI remain unavailable until credentials or endpoints are configured.

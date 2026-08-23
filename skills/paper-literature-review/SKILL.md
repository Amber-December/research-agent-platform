---
name: paper-literature-review
description: Produce evidence-grounded thematic synthesis from an admitted corpus or retrieval package.
---

# Paper Literature Review

Use `CorpusPlan → DedupedCorpus → EvidenceMatrix → Taxonomy → SectionPlan → Draft → Review → Revision → FinalCheck`. Record scope, cutoff, source provenance, inclusion rule, and acceptance condition at each transition.

1. State review type, question, scope, corpus, audience, venue, and retrieval limitations before synthesis.
2. Position the review against supplied prior surveys. Build an operational taxonomy or synthesis matrix by concepts, mechanisms, methods, evidence, or controversy—not retrieval order.
3. Plan section and paragraph jobs before prose. Each substantive paragraph follows: controlling synthesis claim → comparison of at least two sources → limitation, disagreement, or missing evidence → bounded takeaway.
4. Keep `claim_id`, evidence IDs, stable citation keys, support grade (`strong`, `partial`, `background`, `limiting`, `unsupported`), locator, condition, and author-decision status for central claims.
5. Use only admitted evidence. Preserve consensus, contradiction, weak evidence, and unknown as distinct results. Weaken, source, or mark an unsupported claim as `[AUTHOR INPUT NEEDED]`; never use generic background to fill a target length.
6. Keep stable citation identity separate from display numbering. Every externally checkable statement about the admitted corpus, study conditions, results, chronology, or source count needs a paragraph-local stable citation ID; an item appearing only in the References section does not close the body claim. Audit four layers separately: ID resolution, claim coverage, admitted-corpus use, and semantic support grade.
7. Claim saturation only after two successive search rounds introduce no new mechanism, evidence type, or contradiction; a user-specified coverage requirement overrides saturation.

Platform retrieval labels, provider status, access fields, missing PDF URLs, and download status are operational metadata, not study findings or bibliographic facts. Never convert them into claims such as “no full text exists,” “no public PDF is available,” or “the work is unpublished”; write only “not supplied in the admitted package” when that boundary matters.

The admitted record fields are exhaustive. Do not infer event counts, site counts,
climate classifications, study dates, residence times, maintenance history,
QA/QC procedures, or study labels from domain knowledge or remembered abstracts.
Do not invent titles, authors, venues, DOIs, URLs, or publication years. If the
record does not contain a field, state that it was not supplied in the admitted
package. Keep `[AUTHOR INPUT NEEDED]` out of the reader-facing review; use it
only in supporting planning or audit artifacts.

For a frozen user corpus, do not retrieve or introduce outside references. For normal review mode, use the platform retrieval contract and disclose provider or full-text limitations.

## Review-specific style learning

Maintain a **source manifest** for the corpus and any venue-style evidence: stable ID, source URL/file, document type, access level, date, inclusion decision and allowed use. A target journal's official guidance outranks an exemplar; an abstract-only source may inform an abstract move but cannot define full-article length or section style. Mark missing official guidance as provisional rather than generic compliance.

- **English review prose:** make the topic sentence a synthesis claim, then compare sources by mechanism, setting, data, method or contradiction. Use named conditions and calibrated verbs; remove generic statements that a topic is important, rapidly growing, or promising unless the corpus directly supports the claim.
- **Chinese review prose:** state the classification principle before enumerating work, use explicit contrast and scope relations, maintain translated terminology, and distinguish literature conclusions from the author's synthesis.
- In either language, a paragraph that only lists papers, repeatedly uses formulaic transitions, or turns a correlation into consensus must be rewritten around a comparison and a boundary.
- **Environmental and engineering synthesis:** before comparing performance, name the reported basis—concentration, mass load, removal, retention, or another metric—and retain the unit, site, period, hydrologic condition, and available QA/QC information. If the admitted corpus does not report flow, blanks, calibration, or a common measurement basis, state that limitation rather than treating unlike results as directly comparable.

## Review method and synthesis controls from verified full texts

- A **systematic review** must expose only the search, screening, coding, appraisal and synthesis steps that actually occurred. If a supplied package contains only a frozen corpus, say so and use a narrative/thematic contract rather than simulating a PRISMA review.
- A **narrative review** should organize the body around mechanisms, conditions, applications or controversies. It should end each major theme by stating what is established, what remains uncertain, and what research or practice question follows.
- Do not treat a study-characteristics table, evidence matrix or citation audit as prose sections of a normal review article. Keep them as linked artifacts unless a target venue and review type require their inclusion.
- When a recommendation follows from synthesis, name the evidence condition and intended actor; do not derive universal policy advice from a single setting or indirect evidence.

## Primary manuscript versus audit package

The primary deliverable is a reader-ready review article. The review manuscript is not a retrieval log, an evidence matrix, or a platform demonstration.

- **Narrative/thematic review:** `Title → Abstract → Keywords → Introduction → Review Scope and Approach → thematic body sections → Discussion → Conclusion → References`. The scope-and-approach section truthfully states the corpus boundary and any actual search approach, but must not fabricate database dates, screening counts, PRISMA flow, risk-of-bias assessment, or full-text appraisal.
- **Systematic review/meta-analysis:** use `Title → Abstract → Keywords → Introduction → Methods → Results → Discussion → Conclusion → References`, plus PRISMA-consistent search, eligibility, selection, appraisal, synthesis and certainty reporting only when those steps actually occurred and are represented in the admitted evidence package.
- **Chinese review:** use the equivalent article headings `摘要、关键词、引言、综述范围与方法（或方法）、主题综合（或结果）、讨论、结论、参考文献`; use the target journal's requirements when verified.

Keep the evidence matrix, source manifest, retrieval quality report, study-characteristics table, citation audit, provider/download status and unresolved-evidence list as separate artifacts. Do not place a `Paper Evidence Table`, `Evidence and Citation Audit`, provider status, or download status in the primary manuscript. A study-characteristics table belongs in the main text only when the review type, target venue and evidence support it.

## Deliverable quality

Deliver the review manuscript together with separate taxonomy, synthesis matrix, citation audit, retrieval limitation, source manifest, and unresolved evidence. Generic field knowledge can frame a gap, but cannot replace an admitted citation or support a claim about the reviewed corpus.

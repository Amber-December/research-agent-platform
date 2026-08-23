---
name: paper-final-check
description: Define deterministic and semantic submission-readiness checks for a manuscript and its revision record.
---

# Paper Final Check

Run deterministic checks before semantic checks.

1. Resolve every citation key or number to one bibliography record and audit four distinct outcomes: ID resolution, paragraph-level coverage of externally checkable claims, admitted-corpus use, and semantic support (`strong`, `partial`, `background`, or `limiting`). A References entry without body use does not count as citation closure.
2. Trace quantitative claims, table cells, figure values, equations, and quoted material to supplied evidence.
3. Check captions, labels, numbering, cross-references, abstract/body/results/discussion/conclusion consistency, anonymization, declarations, required sections, and output format.
4. Apply the correct document contract: article section and venue rules for journal papers; native hierarchy, chapter purpose, and author-supplied institutional rules for theses; no generic article-section requirement for a chapter-polishing task.
5. Verify that rebuttal promises correspond to actual manuscript changes and ledger entries.
6. Return `PASS`, `REVISE`, or `BLOCK` with deterministic, location-specific corrective actions. Do not claim visual layout verification unless visual evidence was actually supplied.

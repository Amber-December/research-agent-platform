---
name: paper-revise-from-review
description: Convert peer-review comments into evidence-bounded manuscript revisions and point-by-point responses.
---

# Paper Revise From Review

Use `comment → decision → change → response → verification`.

1. Parse and de-duplicate comments while preserving reviewer and comment IDs, original wording, severity, requested action, evidence need, and author decision.
2. Build a RevisionPlan that maps every comment to a manuscript location, proposed change, evidence dependency, owner, priority, and verification method.
3. Apply only authorized and evidence-supported changes as traceable ChangeSets. Never fabricate a new experiment, analysis, result, or citation to make a response sound complete.
4. Write reviewer-by-reviewer, comment-by-comment responses. Cite the actual changed location and distinguish completed changes, commitments, partial responses, declined requests, and unresolved author inputs.
5. Generate a revision ledger and verification report. An accepted or partially accepted item without a real textual change or an explicitly bounded reason must remain unresolved, not be marked complete.
6. Re-run evidence, citation, result, and consistency checks after revision.

## Response integrity controls

- Preserve the review configuration and comment ID. A platform simulated review is not an external editorial decision.
- For every comment, label the response as implemented, committed, clarification, evidence-based disagreement, or author decision needed. A commitment to obtain data, run an experiment, or verify a source is never an implemented change.
- Where a reviewer asks for clinical, animal, systematic-review, data-governance, or legal-formalisation detail, request missing author evidence rather than manufacturing checklist compliance or primary authority.
- For a technical request, identify the exact revised manuscript location and whether the repair is clarification, additional supplied evidence, analysis, methods detail, discussion, or accessibility editing. A response that only improves explanation must not imply a completed experiment.

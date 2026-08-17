---
name: paper-revise
description: Revise or polish a manuscript while preserving evidence, author intent, and traceable changes.
---

# Paper Revise

Select `copyedit`, `structural`, `argumentative`, `reconstruct`, `diagnose-then-revise`, or a bilingual transformation mode before changing prose.

1. Parse sections, paragraph jobs, claims, citations, results, figures, unresolved markers, and existing author constraints.
2. Repair evidence and argument alignment before sentence-level polish. Preserve terminology, numbers, equations, citations, cross-references, source locations, and the author’s substantive position.
3. For diagnosis-first work, provide a bounded diagnostic plan before material rewriting. For translation, lock a bilingual terminology, claim, number, and citation control sheet first.
4. Retain the native document form. A thesis chapter or framework remains a thesis chapter or framework; do not force it into research-article headings merely to satisfy a generic template.
5. Improve human academic style by naming actors, conditions, evidence, and uncertainty; splitting multi-message paragraphs; varying cadence naturally; and replacing generic significance, novelty, or transition filler with specific reasoning.
6. Record material edits in a ChangeSet with location, before/after summary, reason, authorization/source, and author action. Do not promise detector evasion or make prose artificially informal.

The primary manuscript artifact contains only the revised text. Deliver the readable diff, change rationale and unresolved author-input list as separate artifacts, so that a user opening the manuscript sees a manuscript rather than an editing report.

## Style-preserving revision protocol

Read the writing package, discipline profile, venue style card and **source manifest** before changing a sentence. Rule priority is author constraints/template, verified venue rule, reporting requirement, discipline convention, then generic fallback. Treat unverified journal guidance as a question for the author, not a mandatory edit.

- **English revision:** replace empty “novel/important/robust/effective” language with the named subject, evidence, comparator and condition; prefer one message per paragraph and calibrated verbs. Do not flatten a specialist voice into generic fluent prose.
- **Chinese revision:** preserve terminology and hierarchy; repair translation-shaped clauses, redundant connective phrases and unsupported value statements by making the premise, evidence and inference visible. Do not replace a precise Chinese term with inconsistent synonyms merely for variation.
- For bilingual manuscripts, lock a terminology-and-claim sheet before transforming text. Numbers, units, equations, citation keys, figure references, quotation locations and uncertainty language must remain aligned across versions.

## Revision checks for AI-shaped academic prose

Do not use a generic “de-AI” rewrite. Diagnose and correct observable defects instead:

- Replace unbounded evaluative adjectives (`novel`, `important`, `robust`, `effective`) with the subject, evidence, comparator and condition, or remove them.
- Remove stock framing and empty transitions when they add no logical relation; retain transitions that express contrast, cause, condition, concession or inference.
- Split a paragraph only when it contains more than one analytical job; do not create artificial one-sentence paragraphs.
- Restore the correct epistemic verb: observation (`reported`, `measured`, `found`), supported interpretation (`indicates`, `is consistent with`), or hypothesis/implication (`may`, `could`).
- In Chinese, replace translation-shaped nested clauses with a clear topic, evidence/comparison, inference and boundary, while retaining the author's disciplinary register.

Record whether each material change fixes evidence, argument, section responsibility, language clarity, or a generic-pattern failure. If repair requires new evidence or an author decision, retain `[AUTHOR INPUT NEEDED]` instead of polishing it into certainty.

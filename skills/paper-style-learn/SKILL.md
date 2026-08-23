---
name: paper-style-learn
description: Derive transferable field, venue, and author writing guidance without copying exemplar prose.
---

# Paper Style Learn

Derive a FieldWritingGuide from uploaded exemplars, a built-in discipline profile, or both.

1. Identify document type, field, venue, language, comparable sections, and requested heading mode.
2. Compare rhetorical sequence, section jobs, claim progression, evidence placement, citation distribution, terminology, figure use, limitations, and discussion patterns.
3. Separate stable cross-source patterns from sample-specific choices. Learn structure and strategy only: never copy sentences, claims, examples, or terminology from exemplars.
4. Express findings as executable rules with applicability boundaries, source IDs, style source (`user_exemplars`, `built_in_profile`, or `hybrid`), and uncertainty.
5. For a named venue apply requirements in this order: user template, current official author guidance, publisher policy, reporting guideline, built-in profile, discipline fallback. If official guidance is unavailable, label the rule `needs-refresh`; do not claim compliance.
6. Create a review-writing subset whenever the target is a literature review or related-work section.

An index such as SCI, SSCI, CSCD, CSSCI, or EI describes indexing, not a formatting template.

## Source Manifest and rule strength

Write or update a **source manifest** before calling a rule reusable. For every style source record source ID/URL or user file, document type, full-text versus abstract-only access, retrieval date, target venue/article type, and applicability boundary.

- Rank rules as: user template > verified official guideline > publisher or reporting policy > multi-exemplar full-text pattern > discipline profile > generic fallback.
- A named journal without an official source remains `needs_author_confirmation`; never state that its formatting, page, reference, or disclosure rule has been verified.

The runtime also loads `resources/publication/exemplars/curated-patterns-v1.json`.
These are distilled rhetorical moves from a small, traceable calibration corpus
(for example, synthesis by comparable conditions in reviews and evidence-led
claim calibration in research articles). They are writing guidance, not copied
sentences and not venue compliance. Promote a pattern to a venue-specific rule
only after at least three same-genre full-text exemplars and the current
official author guidance have been recorded in the source manifest.
- High citation count is a discovery signal only. Learn venue style from 3–10 comparable, lawful full-text exemplars where available; abstracts can teach only abstract-level rhetorical moves.
- Extract argument order, section responsibility, paragraph jobs, reporting fields, citation density/form, figure narration, terminology and limits. Never retain distinctive sentences, examples, or claims as a style rule.

## Verified cross-disciplinary style corpus

The runtime also loads `resources/publication/style-corpus/learning-matrix-v1.json`. Its rules are derived from locally downloaded, lawfully accessible full texts selected from the cross-disciplinary corpus manifest. Apply those rules as an additional calibration layer, not as a substitute for the author evidence, target venue rules, or disciplinary judgment.

It also loads `resources/publication/style-corpus/local-library-learning-matrix-v1.json`, distilled from the user-provided local literature library. This adds abstract compression, multi-scale argument architecture, data-resource provenance, AI evaluation-chain, policy-risk, and Chinese review/social-science controls. The PDFs remain local learning materials; only the derived rules and source labels are versioned.

- Record the source IDs behind every promoted rule, its document type, field, language, access status, and applicability boundary.
- Keep a distinction between **downloaded and read**, **metadata verified but restricted**, and **unverified discovery candidates**. Only the first category can contribute full-article structure or language rules.
- A cross-disciplinary pattern is reusable only when it describes a rhetorical move, evidence relation, or language control. Never retain distinctive prose, examples, numerical claims, or topic-specific terminology as reusable text.
- For target-journal learning, add current official author guidance plus at least three comparable lawful full texts before calling a rule venue-specific.

## Bilingual academic-expression guide

- **English:** use concrete actors, controlled verbs and evidence-led topic sentences. Prefer `shows`, `indicates`, `is associated with`, `may`, or `could` according to support strength. Replace generic significance, novelty, smooth-transition, and capability phrases with the object, condition, comparison and observed consequence.
- **Chinese:** preserve fixed terms and abbreviations; make definition → evidence/comparison → inference → boundary explicit. Avoid translation-shaped long sentences, repeated “具有重要意义/值得关注”, empty “本文认为”, and ornamental connectors that do not express a reasoning relation.
- In both languages, vary syntax only when it clarifies logic. The goal is not detector evasion: retain author meaning, numbers, quotations, citations, uncertainty and disciplinary conventions.

## Output contract

Return a style card with: routing context; source manifest; verified rules; provisional rules; rejected sample-specific patterns; section and paragraph implications; bilingual expression notes; and author-confirmation items. A generic profile may guide prose but cannot certify venue compliance.

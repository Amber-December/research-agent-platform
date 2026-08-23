---
name: paper-review
description: Run evidence-driven simulated peer review and produce actionable, traceable findings.
---

# Paper Review

Freeze one read-only EvidenceSnapshot of the manuscript, figures, bibliography, and supplied evidence. The platform owns state, artifacts, and the final gate; review roles return only structured findings.

1. Assess argument, synthesis, evidence, coverage, clarity, citation integrity, structure, discipline fit, and document fit.
2. For each finding record severity, category, exact location, why it matters, evidence basis, suggested repair, reviewer role, and whether author input is needed.
3. Audit claim-to-evidence alignment, citation closure, result and figure support, overclaiming, terminology consistency, paragraph flow, limitations, and venue requirements.
4. Use discipline checks: distinguish demonstrated capability from assertion in AI; biological from technical replicates in life science; correlation from causation in clinical and social science; authority level and jurisdiction in law; versions and page locations in humanities; assumptions, lemma status, and proof state in mathematics.
5. Do not claim a new experiment, retrieval, verification, or publication readiness. Keep independent roles blind to one another; mechanically merge duplicate findings while preserving role provenance.
6. Treat missing review methodology, unsupported quantitative claims, unresolved bibliography failures, non-operational taxonomies, and conclusion claims exceeding evidence as major findings.

## Reporting-guideline review controls

- For an RCT, check the supplied manuscript for the CONSORT chain: allocation/design, eligibility and setting, intervention, outcomes, sample size, randomisation, blinding, flow, effect estimates, harms, limitations, registration and funding role. Report a missing item only when that design is actually claimed.
- For an in-vivo study, apply ARRIVE controls: experimental unit, n and exclusions, allocation/randomisation, blinding, outcome definition, analysis, model characteristics and procedures. Do not mistake technical repeats for independent biological or animal units.
- For a systematic review, apply PRISMA controls only when methods were actually recorded. Distinguish missing disclosure from an unperformed step; never invent search dates, flow counts, appraisal, registration or protocol details.
- For a data/resource article, check provenance, transformations, governance, access conditions, validation and stated scope separately.
- For a materials or wet-experiment paper, trace material identity and state → environment and protocol → measurement modality → direct observation → interpretation. Flag any claim that calls ex situ or post-test association operando evidence, or calls one characterization modality proof of an active structure or mechanism.
- For theorem-driven work, verify that objects, ambient setting, quantifiers and hypotheses precede each theorem; distinguish proved statements from lemmas, corollaries, examples and conjectural extensions; trace every proof dependency and flag a dropped field, rank, dimension, irreducibility or parameter boundary.
- For a formal legal or normative paper, trace source/case facts → definitions/value premises → rule or representation → inference → example → scope; flag conclusions that outrun authority or formal assumptions.

## Simulated-review boundary

State the configuration as `platform simulated review`. Preserve every user-supplied reviewer comment verbatim or as a faithful labelled restatement. A finding must identify manuscript location, evidence boundary and recommended action. It must never claim editorial decision, reviewer identity, reviewer satisfaction, or a completed experiment.

Return a revision-ready package, not vague encouragement or a detector-style score.

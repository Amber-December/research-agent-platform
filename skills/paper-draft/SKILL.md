---
name: paper-draft
description: Draft a manuscript or review article from a frozen writing package, section plan, and evidence map.
---

# Paper Draft

Follow `Outline → SectionPlan → ParagraphContract → SectionDraft → QualityGate`.

1. Resolve language, field, venue, heading mode, and style provenance from the writing package and FieldWritingGuide.
2. Build a section blueprint: purpose, controlling claims, evidence IDs, results, citations, figures, paragraph jobs, transitions, and missing inputs.
3. Draft from evidence outward. Preserve supplied numbers, methods, equations, figure identities, quotations, citations, and claim boundaries exactly. Do not invent a result, source, sample, legal authority, archival page, or proof.
4. Every substantive paragraph has one controlling claim, nearby evidence/citations, a reasoning relation, a stated condition or boundary, and a closing takeaway or transition. If required evidence is absent, use `[AUTHOR INPUT NEEDED]` at the exact point.
5. Use calibrated language: `demonstrate` only for direct support, `indicate` or `suggest` for partial support, and `may` or `could` for hypotheses and implications.
6. Respect section jobs: introductions establish a bounded gap; reviews compare rather than list papers; results report observations without unsupported mechanisms; discussions interpret and limit; conclusions add no new evidence.
7. In Chinese, maintain fixed translation and abbreviation choices and use explicit premise–comparison–reason–result–limitation relations. In English, use concrete actors, verbs, and claim-first paragraphs; avoid generic importance or novelty rhetoric.
8. Before delivery run reverse outlining, citation/support checks, terminology/numbering checks, and cross-section consistency checks. Expand missing argument or evidence work, never filler.

## Argument, section, and language controls

Build an argument spine before prose: bounded problem → unresolved bottleneck → article or review action → decisive evidence → implication → boundary. Map each requested section to one job: Abstract compresses the story; Introduction establishes a bounded gap; Related Work synthesizes mechanisms rather than chronology; Methods makes work reproducible; Results reports observations; Discussion interprets without new results; Conclusion adds no evidence.

Maintain a **source manifest** and style-card status in the writing package. Apply user templates and verified venue rules first, then reporting guidelines, discipline profiles and generic academic fallback. A generic rule never overrides an author-provided constraint or claims journal compliance.

Use the curated exemplar patterns loaded by the runtime as a final rhetorical
calibration layer. They constrain paragraph jobs, comparison dimensions and
claim strength; they must never be used to imitate wording or to invent missing
evidence.

Use verified cross-disciplinary style-corpus rules as a second calibration layer.
They provide four controls: a review must distinguish real methods from unperformed
steps; an abstract must compress a complete argument with the correct tense; a
results paragraph must separate observation from interpretation; and a recommendation
must name its evidence, responsible actor and applicability condition. They never
authorize copied prose or unsupported content.

When the local-library calibration layer applies, additionally: make abstracts complete miniature arguments; preserve one contribution across article, section and paragraph scale; make resource/data provenance and validation explicit; tie AI claims to the exact evaluation chain; and in Chinese reviews or social-science papers make the concept/mechanism/design/comparison/boundary sequence visible. These are rhetorical controls, never a license to import facts or wording from source papers.

- **English:** name the actor, system, condition and comparator; use a claim-first topic sentence followed by evidence, reasoning and a bounded takeaway. Remove generic importance, novelty, capability and transition filler.
- **Chinese:** keep technical terms and Chinese–English abbreviations stable; use explicit premise, comparison, reason, result and limitation relations; avoid translation-shaped long sentences and unsupported evaluative slogans.
- For both languages, do not imitate source sentences. “Human” academic prose means precise choices grounded in evidence, not casualness or detector evasion.

### Section-level language checks

- **Abstract:** retain only problem, objective, approach, decisive supplied result or planned work, and bounded implication. Remove literature review, generic importance claims and ungrounded superlatives.
- **Introduction:** move from field context to a specific unresolved problem, then the article's precise action. Do not preview outcomes the evidence does not establish.
- **Methods:** describe the actual design, materials, sources, analytic steps and decision rules. Avoid phrases such as “standard methods” unless the named standard is supplied.
- **Results / thematic synthesis:** attach each observed result or cross-source comparison to its condition and nearby evidence. Do not make the discussion's causal explanation appear as an observation.
- **Discussion / conclusion:** explain significance through a named relation to evidence, limitation and scope. A recommendation must identify the actor, condition and support for action.
- **Materials / wet experiment:** state material or sample identity, processing history, measurement environment, protocol and modality before the observation. Mark evidence as operando, in situ, ex situ, post-test or computational; then distinguish the observation from the structural assignment and the proposed mechanism.
- **Theorem-driven writing:** state objects, ambient setting, quantifiers and hypotheses before the result; label each theorem, lemma, corollary, example and conjectural extension by its proof status. Give the dependency chain rather than prose that merely resembles a proof, and retain the field, rank, dimension, irreducibility and parameter boundaries that limit the conclusion.

## Section-specific stop rules

Do not use Introduction to preview unsupported outcomes; do not use Results to invent mechanisms; do not use Discussion to add new measurements; do not use Conclusion to make a broader claim than the evidence permits. For non-IMRAD forms, including law, humanities, mathematics and thesis chapters, follow the native document contract rather than a generic article skeleton.

## Thesis-plan and thesis-polishing modes

Before drafting a thesis deliverable, identify whether the source is an existing prose section or only a proposal/research plan.

- For an **existing prose section**, return the revised prose as the primary deliverable. Keep diagnosis, ChangeSet and unresolved inputs in separate artifacts; never wrap the revised prose in a planning report.
- For a **validation case that asks `/write` to draft a thesis abstract from a research plan**, write a proposed-study abstract: research background/problem → objective → planned material, case or data → planned methods/path → expected contribution or application boundary. This is an input/output writing-quality case, not a new user-facing command or workflow. Use prospective wording where the study is not complete. Never convert planned work into completed results or a concluded finding.
- Return `摘要` and `关键词` for a Chinese abstract by default. Add `Abstract` and `Key words` only when bilingual output is requested or required by a verified institutional rule.

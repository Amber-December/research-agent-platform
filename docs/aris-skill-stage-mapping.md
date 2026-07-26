# ARIS Skill Stage Mapping

Generated from `src/research_agent_platform/graphs/workflows.py`.

## /plan - Research Planning Workflow

Turn a selected idea or research objective into a claim-driven experiment and execution plan.

### Research Blueprint (`blueprint`)

- Artifact: `plan/RESEARCH_BLUEPRINT.md`
- Kind: `plan`
- HITL: `False`
- ARIS skills:
  - `skills/skills-codex/research-pipeline/SKILL.md`
  - `skills/skills-codex/research-refine-pipeline/SKILL.md`
  - `skills/skills-codex/research-refine/SKILL.md`
  - `skills/skills-codex/system-profile/SKILL.md`

### Experiment Plan (`experiment_plan`)

- Artifact: `plan/EXPERIMENT_PLAN.md`
- Kind: `plan`
- HITL: `False`
- ARIS skills:
  - `skills/skills-codex/experiment-plan/SKILL.md`
  - `skills/skills-codex/experiment-bridge/SKILL.md`
  - `skills/skills-codex/ablation-planner/SKILL.md`
  - `skills/skills-codex/experiment-audit/SKILL.md`
  - `skills/skills-codex/monitor-experiment/SKILL.md`
  - `skills/skills-codex/training-check/SKILL.md`

### Execution Checklist (`execution_checklist`)

- Artifact: `plan/EXECUTION_CHECKLIST.md`
- Kind: `plan`
- HITL: `False`
- ARIS skills:
  - `skills/skills-codex/research-pipeline/SKILL.md`
  - `skills/skills-codex/experiment-bridge/SKILL.md`
  - `skills/skills-codex/experiment-plan/SKILL.md`
  - `skills/skills-codex/experiment-queue/SKILL.md`
  - `skills/skills-codex/monitor-experiment/SKILL.md`
  - `skills/skills-codex/research-wiki/SKILL.md`


## /idea - Idea Discovery Workflow

Generate, challenge, verify, and select research ideas using literature evidence.

### Idea Candidates (`idea_candidates`)

- Artifact: `idea/IDEA_CANDIDATES.md`
- Kind: `report`
- HITL: `True`
- ARIS skills:
  - `skills/skills-codex/idea-discovery/SKILL.md`
  - `skills/skills-codex/prior-art-search/SKILL.md`
  - `skills/skills-codex/openalex/SKILL.md`
  - `skills/skills-codex/semantic-scholar/SKILL.md`
  - `skills/skills-codex/arxiv/SKILL.md`
  - `skills/skills-codex/deepxiv/SKILL.md`
  - `skills/skills-codex/comm-lit-review/SKILL.md`
  - `skills/skills-codex/novelty-check/SKILL.md`

### Idea Verification (`idea_verification`)

- Artifact: `idea/IDEA_VERIFICATION.md`
- Kind: `report`
- HITL: `False`
- ARIS skills:
  - `skills/skills-codex/novelty-check/SKILL.md`
  - `skills/skills-codex/prior-art-search/SKILL.md`
  - `skills/skills-codex/kill-argument/SKILL.md`
  - `skills/skills-codex/research-review/SKILL.md`
  - `skills/skills-codex/idea-discovery-robot/SKILL.md`

### Final Idea (`final_idea`)

- Artifact: `idea/FINAL_IDEA.md`
- Kind: `report`
- HITL: `False`
- ARIS skills:
  - `skills/skills-codex/research-refine/SKILL.md`
  - `skills/skills-codex/invention-structuring/SKILL.md`
  - `skills/skills-codex/claims-drafting/SKILL.md`
  - `skills/skills-codex/research-review/SKILL.md`


## /code - Experiment Bridge Workflow

Turn an approved idea into implementation, validation, and handoff materials.

### Implementation Plan (`implementation_plan`)

- Artifact: `code/IMPLEMENTATION_PLAN.md`
- Kind: `plan`
- HITL: `True`
- ARIS skills:
  - `skills/skills-codex/experiment-bridge/SKILL.md`
  - `skills/skills-codex/run-experiment/SKILL.md`
  - `skills/skills-codex/experiment-queue/SKILL.md`
  - `skills/skills-codex/serverless-modal/SKILL.md`
  - `skills/skills-codex/vast-gpu/SKILL.md`
  - `skills/skills-codex/qzcli/SKILL.md`
  - `skills/skills-codex/meta-apply/SKILL.md`
  - `skills/skills-codex/system-profile/SKILL.md`

### Launch Runbook (`launch_runbook`)

- Artifact: `code/LAUNCH_RUNBOOK.md`
- Kind: `plan`
- HITL: `False`
- ARIS skills:
  - `skills/skills-codex/run-experiment/SKILL.md`
  - `skills/skills-codex/experiment-queue/SKILL.md`
  - `skills/skills-codex/monitor-experiment/SKILL.md`
  - `skills/skills-codex/training-check/SKILL.md`
  - `skills/skills-codex/serverless-modal/SKILL.md`
  - `skills/skills-codex/vast-gpu/SKILL.md`
  - `skills/skills-codex/feishu-notify/SKILL.md`

### Local Collaboration Guide (`local_collaboration`)

- Artifact: `code/LOCAL_COLLAB.md`
- Kind: `note`
- HITL: `False`
- ARIS skills:
  - `skills/skills-codex/research-pipeline/SKILL.md`
  - `skills/skills-codex/research-wiki/SKILL.md`
  - `skills/skills-codex/wiki-enrich/SKILL.md`
  - `skills/skills-codex/monitor-experiment/SKILL.md`
  - `skills/skills-codex/system-profile/SKILL.md`


## /fig - Figure Planning Workflow

Design figure inventory and visual briefs.

### Figure Inventory (`figure_inventory`)

- Artifact: `figures/FIGURE_INVENTORY.md`
- Kind: `report`
- HITL: `False`
- ARIS skills:
  - `skills/skills-codex/paper-figure/SKILL.md`
  - `skills/skills-codex/figure-spec/SKILL.md`
  - `skills/skills-codex/figure-description/SKILL.md`
  - `skills/skills-codex/mermaid-diagram/SKILL.md`
  - `skills/skills-codex/paper-illustration-image2/SKILL.md`

### Figure Briefs (`figure_briefs`)

- Artifact: `figures/FIGURE_BRIEFS.md`
- Kind: `plan`
- HITL: `False`
- ARIS skills:
  - `skills/skills-codex/paper-figure/SKILL.md`
  - `skills/skills-codex/figure-spec/SKILL.md`
  - `skills/skills-codex/figure-description/SKILL.md`
  - `skills/skills-codex/paper-illustration/SKILL.md`
  - `skills/skills-codex/paper-illustration-image2/SKILL.md`
  - `skills/skills-codex/render-html/SKILL.md`


## /write - Paper Writing Workflow

Draft paper planning, evidence mapping, and submission-ready narrative assets.

### Paper Plan (`paper_plan`)

- Artifact: `paper/PAPER_PLAN.md`
- Kind: `plan`
- HITL: `True`
- ARIS skills:
  - `skills/skills-codex/paper-plan/SKILL.md`
  - `skills/skills-codex/paper-writing/SKILL.md`
  - `skills/skills-codex/paper-write/SKILL.md`
  - `skills/skills-codex/writing-systems-papers/SKILL.md`
  - `skills/skills-codex/paper-claim-audit/SKILL.md`
  - `skills/skills-codex/citation-audit/SKILL.md`
  - `skills/skills-codex/result-to-claim/SKILL.md`

### Narrative Report (`narrative_report`)

- Artifact: `paper/NARRATIVE_REPORT.md`
- Kind: `report`
- HITL: `False`
- ARIS skills:
  - `skills/skills-codex/claims-drafting/SKILL.md`
  - `skills/skills-codex/result-to-claim/SKILL.md`
  - `skills/skills-codex/analyze-results/SKILL.md`
  - `skills/skills-codex/paper-claim-audit/SKILL.md`
  - `skills/skills-codex/research-review/SKILL.md`
  - `skills/skills-codex/citation-audit/SKILL.md`

### Draft Sections (`draft_sections`)

- Artifact: `paper/PAPER_DRAFT.md`
- Kind: `report`
- HITL: `False`
- ARIS skills:
  - `skills/skills-codex/paper-writing/SKILL.md`
  - `skills/skills-codex/paper-write/SKILL.md`
  - `skills/skills-codex/writing-systems-papers/SKILL.md`
  - `skills/skills-codex/paper-claim-audit/SKILL.md`
  - `skills/skills-codex/citation-audit/SKILL.md`
  - `skills/skills-codex/overleaf-sync/SKILL.md`
  - `skills/skills-codex/paper-compile/SKILL.md`
  - `skills/skills-codex/claims-drafting/SKILL.md`


## /review - Literature Review Workflow

Search, organize, and synthesize literature evidence for idea discovery and research planning.

### Research Brief (`research_brief`)

- Artifact: `bib/RESEARCH_BRIEF.md`
- Kind: `report`
- HITL: `False`
- ARIS skills:
  - `skills/skills-codex/research-lit/SKILL.md`
  - `skills/skills-codex/prior-art-search/SKILL.md`
  - `skills/skills-codex/openalex/SKILL.md`
  - `skills/skills-codex/semantic-scholar/SKILL.md`
  - `skills/skills-codex/arxiv/SKILL.md`
  - `skills/skills-codex/deepxiv/SKILL.md`
  - `skills/skills-codex/comm-lit-review/SKILL.md`

### Literature Synthesis (`literature_synthesis`)

- Artifact: `bib/LITERATURE_REVIEW.md`
- Kind: `report`
- HITL: `False`
- ARIS skills:
  - `skills/skills-codex/research-lit/SKILL.md`
  - `skills/skills-codex/comm-lit-review/SKILL.md`
  - `skills/skills-codex/research-review/SKILL.md`
  - `skills/skills-codex/citation-audit/SKILL.md`

### Evidence Map (`evidence_map`)

- Artifact: `bib/EVIDENCE_MAP.md`
- Kind: `report`
- HITL: `False`
- ARIS skills:
  - `skills/skills-codex/research-review/SKILL.md`
  - `skills/skills-codex/citation-audit/SKILL.md`
  - `skills/skills-codex/result-to-claim/SKILL.md`

### Research Gaps (`research_gaps`)

- Artifact: `bib/RESEARCH_GAPS.md`
- Kind: `report`
- HITL: `False`
- ARIS skills:
  - `skills/skills-codex/research-lit/SKILL.md`
  - `skills/skills-codex/novelty-check/SKILL.md`
  - `skills/skills-codex/kill-argument/SKILL.md`
  - `skills/skills-codex/research-review/SKILL.md`


## /rebuttal - Review Response and Rebuttal Workflow

Triage peer-review comments, draft rebuttals, and produce a concrete revision plan.

### Review Triage (`review_triage`)

- Artifact: `rebuttal/REVIEW_TRIAGE.md`
- Kind: `review`
- HITL: `True`
- ARIS skills:
  - `skills/skills-codex/auto-review-loop/SKILL.md`
  - `skills/skills-codex/research-review/SKILL.md`
  - `skills/skills-codex/rebuttal/SKILL.md`
  - `skills/skills-codex/kill-argument/SKILL.md`
  - `skills/skills-codex/integrity-forensics/SKILL.md`
  - `skills/skills-codex/experiment-audit/SKILL.md`
  - `skills/skills-codex/paper-claim-audit/SKILL.md`
  - `skills/skills-codex/citation-audit/SKILL.md`

### Rebuttal Draft (`rebuttal_draft`)

- Artifact: `rebuttal/REBUTTAL_DRAFT.md`
- Kind: `review`
- HITL: `False`
- ARIS skills:
  - `skills/skills-codex/rebuttal/SKILL.md`
  - `skills/skills-codex/kill-argument/SKILL.md`
  - `skills/skills-codex/claims-drafting/SKILL.md`
  - `skills/skills-codex/research-review/SKILL.md`
  - `skills/skills-codex/paper-claim-audit/SKILL.md`

### Revision Plan (`revision_plan`)

- Artifact: `rebuttal/REVISION_PLAN.md`
- Kind: `plan`
- HITL: `False`
- ARIS skills:
  - `skills/skills-codex/auto-review-loop/SKILL.md`
  - `skills/skills-codex/resubmit-pipeline/SKILL.md`
  - `skills/skills-codex/ablation-planner/SKILL.md`
  - `skills/skills-codex/experiment-audit/SKILL.md`
  - `skills/skills-codex/citation-audit/SKILL.md`
  - `skills/skills-codex/paper-claim-audit/SKILL.md`
  - `skills/skills-codex/result-to-claim/SKILL.md`


## /present - Presentation Workflow

Turn workspace evidence into an approved, image-rendered research deck.

### Slides Outline (`slides_outline`)

- Artifact: `presentation/SLIDES_OUTLINE.md`
- Kind: `slides`
- HITL: `True`
- ARIS skills:
  - `skills/skills-codex/paper-slides/SKILL.md`
  - `skills/skills-codex/paper-talk/SKILL.md`
  - `skills/skills-codex/paper-poster/SKILL.md`
  - `skills/skills-codex/paper-poster-html/SKILL.md`
  - `skills/skills-codex/slides-polish/SKILL.md`
  - `skills/skills-codex/scientific-slides/SKILL.md`

### Slide Content (`slide_content`)

- Artifact: `presentation/SLIDE_CONTENT.md`
- Kind: `slides`
- HITL: `False`
- ARIS skills:
  - `skills/skills-codex/paper-slides/SKILL.md`
  - `skills/skills-codex/paper-talk/SKILL.md`
  - `skills/skills-codex/slides-polish/SKILL.md`
  - `skills/skills-codex/result-to-claim/SKILL.md`
  - `skills/skills-codex/paper-claim-audit/SKILL.md`
  - `skills/skills-codex/scientific-slides/SKILL.md`

### Speaker Notes (`speaker_notes`)

- Artifact: `presentation/SPEAKER_NOTES.md`
- Kind: `slides`
- HITL: `False`
- ARIS skills:
  - `skills/skills-codex/paper-talk/SKILL.md`
  - `skills/skills-codex/paper-slides/SKILL.md`
  - `skills/skills-codex/interview-cheatsheet/SKILL.md`
  - `skills/skills-codex/slides-polish/SKILL.md`

### Q and A Brief (`qa_brief`)

- Artifact: `presentation/QA_BRIEF.md`
- Kind: `note`
- HITL: `False`
- ARIS skills:
  - `skills/skills-codex/interview-cheatsheet/SKILL.md`
  - `skills/skills-codex/kill-argument/SKILL.md`
  - `skills/skills-codex/research-review/SKILL.md`
  - `skills/skills-codex/paper-claim-audit/SKILL.md`
  - `skills/skills-codex/result-to-claim/SKILL.md`


## /wiki - Research Wiki Workflow

Consolidate reusable memory and workspace notes.

### Knowledge Digest (`knowledge_digest`)

- Artifact: `wiki/KNOWLEDGE_DIGEST.md`
- Kind: `wiki`
- HITL: `False`
- ARIS skills:
  - `skills/skills-codex/research-wiki/SKILL.md`
  - `skills/skills-codex/wiki-enrich/SKILL.md`
  - `skills/skills-codex/research-review/SKILL.md`
  - `skills/skills-codex/result-to-claim/SKILL.md`

### Memory Update (`memory_update`)

- Artifact: `wiki/MEMORY_UPDATE.md`
- Kind: `wiki`
- HITL: `False`
- ARIS skills:
  - `skills/skills-codex/research-wiki/SKILL.md`
  - `skills/skills-codex/wiki-enrich/SKILL.md`
  - `skills/skills-codex/research-pipeline/SKILL.md`

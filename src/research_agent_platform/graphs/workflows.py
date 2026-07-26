from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class StageDefinition:
    name: str
    title: str
    instruction: str
    artifact_path: str
    artifact_kind: str
    required_sections: list[str]
    skill_paths: list[str] = field(default_factory=list)
    hitl: bool = False
    checkpoint_title: str = ""


@dataclass(frozen=True)
class WorkflowDefinition:
    command: str
    title: str
    description: str
    stage_definitions: list[StageDefinition]


def _skills(*names: str) -> list[str]:
    return [f"skills/skills-codex/{name}/SKILL.md" for name in names]


def workflow_registry() -> dict[str, WorkflowDefinition]:
    return {
        "/plan": WorkflowDefinition(
            command="/plan",
            title="Research Planning Workflow",
            description="Turn a selected idea or research objective into a claim-driven experiment and execution plan.",
            stage_definitions=[
                StageDefinition(
                    name="blueprint",
                    title="Research Blueprint",
                    instruction=(
                        "Read the selected idea and literature evidence available in the session workspace. If no prior /idea "
                        "artifact exists, treat the user's objective as the selected direction. Define the problem, hypotheses, "
                        "intended contribution, claim-to-evidence requirements, assumptions, dependencies, and failure criteria. "
                        "Do not generate alternative research topics or repeat a broad literature review."
                    ),
                    artifact_path="plan/RESEARCH_BLUEPRINT.md",
                    artifact_kind="plan",
                    required_sections=[
                        "Objective",
                        "Selected Direction",
                        "Research Hypotheses",
                        "Claim to Evidence Requirements",
                        "Dependencies and Assumptions",
                        "Failure Criteria",
                    ],
                    skill_paths=_skills(
                        "research-pipeline",
                        "research-refine-pipeline",
                        "research-refine",
                        "system-profile",
                    ),
                ),
                StageDefinition(
                    name="experiment_plan",
                    title="Experiment Plan",
                    instruction=(
                        "Convert the research blueprint into a claim-driven experiment design. Specify datasets, baselines, "
                        "metrics, controls, sanity checks, ablations, resource budget, launch order, and stop conditions. Reuse "
                        "the literature evidence produced by /review when available; clearly mark missing evidence instead of "
                        "inventing citations or results."
                    ),
                    artifact_path="plan/EXPERIMENT_PLAN.md",
                    artifact_kind="plan",
                    required_sections=[
                        "Claims Under Test",
                        "Datasets and Inputs",
                        "Baselines",
                        "Metrics",
                        "Must-Run Experiments",
                        "Ablations and Sanity Checks",
                        "Budget and Resources",
                        "Launch Order and Stop Conditions",
                    ],
                    skill_paths=_skills(
                        "experiment-plan",
                        "experiment-bridge",
                        "ablation-planner",
                        "experiment-audit",
                        "monitor-experiment",
                        "training-check",
                    ),
                ),
                StageDefinition(
                    name="execution_checklist",
                    title="Execution Checklist",
                    instruction=(
                        "Translate the blueprint and experiment plan into an operational checklist with milestones, deliverables, "
                        "owners, dependencies, result-capture requirements, necessary approval gates, and immediate next actions."
                    ),
                    artifact_path="plan/EXECUTION_CHECKLIST.md",
                    artifact_kind="plan",
                    required_sections=[
                        "Deliverables",
                        "Per-Stage Checklist",
                        "Approval Matrix",
                        "Immediate Next Actions",
                    ],
                    skill_paths=_skills(
                        "research-pipeline",
                        "experiment-bridge",
                        "experiment-plan",
                        "experiment-queue",
                        "monitor-experiment",
                        "research-wiki",
                    ),
                ),
            ],
        ),
        "/idea": WorkflowDefinition(
            command="/idea",
            title="Idea Discovery Workflow",
            description="Generate, challenge, verify, and select research ideas using literature evidence.",
            stage_definitions=[
                StageDefinition(
                    name="idea_candidates",
                    title="Idea Candidates",
                    instruction=(
                        "Use the user's objective and any /review evidence in the session to generate three distinct research "
                        "ideas. When no literature review exists, perform only the targeted novelty search supplied in context. "
                        "For each idea state the problem, mechanism, novelty thesis, expected contribution, feasibility, and main "
                        "risk. Do not write an experiment plan. Under Decision Required, write None when one candidate is clearly "
                        "recommended; list alternatives only when the user must choose between genuinely different directions."
                    ),
                    artifact_path="idea/IDEA_CANDIDATES.md",
                    artifact_kind="report",
                    required_sections=[
                        "Problem Frame",
                        "Candidate Ideas",
                        "Comparative Assessment",
                        "Recommended Candidate",
                        "Risks and Unknowns",
                        "Decision Required",
                    ],
                    skill_paths=_skills(
                        "idea-discovery",
                        "prior-art-search",
                        "openalex",
                        "semantic-scholar",
                        "arxiv",
                        "deepxiv",
                        "comm-lit-review",
                        "novelty-check",
                    ),
                    hitl=True,
                    checkpoint_title="Topic Selection Approval",
                ),
                StageDefinition(
                    name="idea_verification",
                    title="Idea Verification",
                    instruction=(
                        "Act as an independent critic of the recommended or user-selected candidate. Test the novelty claim "
                        "against the supplied literature, identify the closest prior work, search for disconfirming evidence, "
                        "evaluate feasibility and falsifiability, and state what remains uncertain. Do not expand this into a "
                        "full experiment plan."
                    ),
                    artifact_path="idea/IDEA_VERIFICATION.md",
                    artifact_kind="report",
                    required_sections=[
                        "Candidate Under Review",
                        "Closest Prior Work",
                        "Novelty Stress Test",
                        "Feasibility Stress Test",
                        "Disconfirming Evidence",
                        "Unresolved Questions",
                        "Verification Verdict",
                    ],
                    skill_paths=_skills(
                        "novelty-check",
                        "prior-art-search",
                        "kill-argument",
                        "research-review",
                        "idea-discovery-robot",
                    ),
                ),
                StageDefinition(
                    name="final_idea",
                    title="Final Idea",
                    instruction=(
                        "Consolidate the chosen candidate and verification findings into a concise final research idea that can "
                        "be handed to /plan. Preserve evidence caveats, define the problem anchor, method thesis, dominant "
                        "contribution, falsifiable prediction, scope boundary, and unresolved risks."
                    ),
                    artifact_path="idea/FINAL_IDEA.md",
                    artifact_kind="report",
                    required_sections=[
                        "Problem Anchor",
                        "Method Thesis",
                        "Dominant Contribution",
                        "Falsifiable Prediction",
                        "Evidence Basis",
                        "Scope Boundary",
                        "Open Risks",
                        "Handoff to Plan",
                    ],
                    skill_paths=_skills(
                        "research-refine",
                        "invention-structuring",
                        "claims-drafting",
                        "research-review",
                    ),
                ),
            ],
        ),
        "/code": WorkflowDefinition(
            command="/code",
            title="Experiment Bridge Workflow",
            description="Turn an approved idea into implementation, validation, and handoff materials.",
            stage_definitions=[
                StageDefinition(
                    name="implementation_plan",
                    title="Implementation Plan",
                    instruction="Turn the approved idea into a concrete implementation brief: what to change, what to keep, which files to edit, how to configure the environment, which scripts to run, what data to touch, and how to validate success locally before any broader launch. Include explicit assumptions, dependencies, and a failure fallback. Use Decision Required only when multiple launch choices need the user; otherwise write None and continue automatically.",
                    artifact_path="code/IMPLEMENTATION_PLAN.md",
                    artifact_kind="plan",
                    required_sections=[
                        "Objective and Scope",
                        "Repo Inputs",
                        "Files to Create or Modify",
                        "Execution Plan",
                        "Validation Plan",
                        "Launch Risks",
                        "Decision Required",
                    ],
                    skill_paths=_skills(
                        "experiment-bridge",
                        "run-experiment",
                        "experiment-queue",
                        "serverless-modal",
                        "vast-gpu",
                        "qzcli",
                        "meta-apply",
                        "system-profile",
                    ),
                    hitl=True,
                    checkpoint_title="Experiment Launch Approval",
                ),
                StageDefinition(
                    name="launch_runbook",
                    title="Launch Runbook",
                    instruction="Write the exact runbook for running the implementation end to end: commands, order, environment variables, logs, expected outputs, rollback points, retry rules, and how to capture results for later review. Make it usable by a human operator without extra context.",
                    artifact_path="code/LAUNCH_RUNBOOK.md",
                    artifact_kind="plan",
                    required_sections=[
                        "Prerequisites",
                        "Execution Commands",
                        "Logging and Outputs",
                        "Result Capture",
                        "Failure Handling",
                        "Post-Run Review",
                    ],
                    skill_paths=_skills(
                        "run-experiment",
                        "experiment-queue",
                        "monitor-experiment",
                        "training-check",
                        "serverless-modal",
                        "vast-gpu",
                        "feishu-notify",
                    ),
                ),
                StageDefinition(
                    name="local_collaboration",
                    title="Local Collaboration Guide",
                    instruction="Describe how the human and local tools should collaborate on code changes, file handoffs, logs, checkpoints, and experiment results. Make the file flow explicit so local testing and follow-up edits are straightforward.",
                    artifact_path="code/LOCAL_COLLAB.md",
                    artifact_kind="note",
                    required_sections=[
                        "Workspace Layout",
                        "Human Tasks",
                        "Agent Tasks",
                        "Expected File Handoffs",
                        "Verification Checklist",
                        "How to Resume",
                    ],
                    skill_paths=_skills(
                        "research-pipeline",
                        "research-wiki",
                        "wiki-enrich",
                        "monitor-experiment",
                        "system-profile",
                    ),
                ),
            ],
        ),
        "/fig": WorkflowDefinition(
            command="/fig",
            title="Figure Planning Workflow",
            description="Design figure inventory and visual briefs.",
            stage_definitions=[
                StageDefinition(
                    name="figure_inventory",
                    title="Figure Inventory",
                    instruction="List the essential figures, tables, and diagrams required for the current research story, with rationale and data dependencies.",
                    artifact_path="figures/FIGURE_INVENTORY.md",
                    artifact_kind="report",
                    required_sections=[
                        "Required Figures",
                        "Data Dependencies",
                        "Narrative Purpose",
                        "Priority Order",
                    ],
                    skill_paths=_skills(
                        "paper-figure",
                        "figure-spec",
                        "figure-description",
                        "mermaid-diagram",
                        "paper-illustration-image2",
                    ),
                ),
                StageDefinition(
                    name="figure_briefs",
                    title="Figure Briefs",
                    instruction="Write detailed briefs for each high-priority figure so a human or downstream tool can implement them cleanly.",
                    artifact_path="figures/FIGURE_BRIEFS.md",
                    artifact_kind="plan",
                    required_sections=[
                        "Per-Figure Brief",
                        "Data Fields",
                        "Design Notes",
                        "Caption Drafts",
                    ],
                    skill_paths=_skills(
                        "paper-figure",
                        "figure-spec",
                        "figure-description",
                        "paper-illustration",
                        "paper-illustration-image2",
                        "render-html",
                    ),
                ),
            ],
        ),
        "/write": WorkflowDefinition(
            command="/write",
            title="Paper Writing Workflow",
            description="Draft paper planning, evidence mapping, and submission-ready narrative assets.",
            stage_definitions=[
                StageDefinition(
                    name="paper_plan",
                    title="Paper Plan",
                    instruction="Produce a paper plan that can be executed immediately: target venue, core contribution, outline, claim-to-evidence map, missing evidence, figure/table needs, and a writing order that follows the strongest available facts. Put unresolved venue or story alternatives under Decision Required; otherwise write None and continue automatically.",
                    artifact_path="paper/PAPER_PLAN.md",
                    artifact_kind="plan",
                    required_sections=[
                        "Target Story",
                        "Submission Target",
                        "Section Outline",
                        "Claim to Evidence Map",
                        "Writing Risks",
                        "Questions for Human Review",
                        "Decision Required",
                    ],
                    skill_paths=_skills(
                        "paper-plan",
                        "paper-writing",
                        "paper-write",
                        "writing-systems-papers",
                        "paper-claim-audit",
                        "citation-audit",
                        "result-to-claim",
                    ),
                    hitl=True,
                    checkpoint_title="Writing Outline Approval",
                ),
                StageDefinition(
                    name="narrative_report",
                    title="Narrative Report",
                    instruction="Write a narrative handoff document that a coauthor can use directly: problem, method, evidence, what is still missing, limitations, and how the current work should be framed honestly.",
                    artifact_path="paper/NARRATIVE_REPORT.md",
                    artifact_kind="report",
                    required_sections=[
                        "Problem Statement",
                        "Core Claim",
                        "Method Summary",
                        "Key Results",
                        "Limitations",
                        "Open Gaps",
                    ],
                    skill_paths=_skills(
                        "claims-drafting",
                        "result-to-claim",
                        "analyze-results",
                        "paper-claim-audit",
                        "research-review",
                        "citation-audit",
                    ),
                ),
                StageDefinition(
                    name="draft_sections",
                    title="Draft Sections",
                    instruction="Write a first-pass paper draft aligned with the approved outline and available evidence. Make claims traceable, keep placeholders honest, and include enough structure that a human can continue editing without re-deriving the story.",
                    artifact_path="paper/PAPER_DRAFT.md",
                    artifact_kind="report",
                    required_sections=[
                        "Title",
                        "Abstract",
                        "Introduction",
                        "Related Work",
                        "Method",
                        "Experiments",
                        "Limitations",
                        "Conclusion",
                        "References",
                        "Next Revision Steps",
                    ],
                    skill_paths=_skills(
                        "paper-writing",
                        "paper-write",
                        "writing-systems-papers",
                        "paper-claim-audit",
                        "citation-audit",
                        "overleaf-sync",
                        "paper-compile",
                        "claims-drafting",
                    ),
                ),
            ],
        ),
        "/review": WorkflowDefinition(
            command="/review",
            title="Literature Review Workflow",
            description="Search, organize, and synthesize literature evidence for idea discovery and research planning.",
            stage_definitions=[
                StageDefinition(
                    name="research_brief",
                    title="Research Brief",
                    instruction=(
                        "Turn the user's request into a bounded literature-review brief. Define the research question, scope, "
                        "concept groups, search terms, source coverage, time range, and inclusion/exclusion criteria. Use the "
                        "scholarly search bundle supplied in context as the first retrieval pass and clearly record provider gaps."
                    ),
                    artifact_path="bib/RESEARCH_BRIEF.md",
                    artifact_kind="report",
                    required_sections=[
                        "Research Question",
                        "Scope",
                        "Concept Groups",
                        "Search Strategy",
                        "Source Coverage",
                        "Inclusion and Exclusion Criteria",
                        "Retrieval Limitations",
                    ],
                    skill_paths=_skills(
                        "research-lit",
                        "prior-art-search",
                        "openalex",
                        "semantic-scholar",
                        "arxiv",
                        "deepxiv",
                        "comm-lit-review",
                    ),
                ),
                StageDefinition(
                    name="literature_synthesis",
                    title="Literature Synthesis",
                    instruction=(
                        "Synthesize the retrieved and workspace literature into a structured review. Compare research families, "
                        "methods, datasets, baselines, metrics, findings, contradictions, and limitations. Keep citations "
                        "traceable to the supplied records and distinguish evidence from interpretation."
                    ),
                    artifact_path="bib/LITERATURE_REVIEW.md",
                    artifact_kind="report",
                    required_sections=[
                        "Executive Summary",
                        "Research Landscape",
                        "Methods and Datasets",
                        "Baselines and Metrics",
                        "Key Findings",
                        "Contradictions and Limitations",
                        "References",
                    ],
                    skill_paths=_skills(
                        "research-lit",
                        "comm-lit-review",
                        "research-review",
                        "citation-audit",
                    ),
                ),
                StageDefinition(
                    name="evidence_map",
                    title="Evidence Map",
                    instruction=(
                        "Convert the literature synthesis into an evidence map for downstream /idea and /plan workflows. For each "
                        "important claim or open question, list supporting evidence, opposing or weak evidence, methods, datasets, "
                        "baselines, metrics, confidence, and source pointers."
                    ),
                    artifact_path="bib/EVIDENCE_MAP.md",
                    artifact_kind="report",
                    required_sections=[
                        "Claim Evidence Matrix",
                        "Methods",
                        "Datasets",
                        "Baselines",
                        "Metrics",
                        "Contradictory Evidence",
                        "Confidence and Source Pointers",
                    ],
                    skill_paths=_skills(
                        "research-review",
                        "citation-audit",
                        "result-to-claim",
                    ),
                ),
                StageDefinition(
                    name="research_gaps",
                    title="Research Gaps",
                    instruction=(
                        "Identify defensible research gaps, unresolved disputes, missing comparisons, under-tested assumptions, "
                        "and practical opportunities from the evidence map. Separate well-supported gaps from speculative "
                        "opportunities and provide explicit handoff guidance for /idea and /plan."
                    ),
                    artifact_path="bib/RESEARCH_GAPS.md",
                    artifact_kind="report",
                    required_sections=[
                        "Supported Research Gaps",
                        "Unresolved Disputes",
                        "Missing Evidence",
                        "Speculative Opportunities",
                        "Handoff to Idea",
                        "Handoff to Plan",
                    ],
                    skill_paths=_skills(
                        "research-lit",
                        "novelty-check",
                        "kill-argument",
                        "research-review",
                    ),
                ),
            ],
        ),
        "/rebuttal": WorkflowDefinition(
            command="/rebuttal",
            title="Review Response and Rebuttal Workflow",
            description="Triage peer-review comments, draft rebuttals, and produce a concrete revision plan.",
            stage_definitions=[
                StageDefinition(
                    name="review_triage",
                    title="Review Triage",
                    instruction="Parse the peer reviews into concrete blockers, major concerns, minor issues, evidence gaps, and the minimum change set required to respond well. Identify which points need new experiments, wording changes, or direct rebuttal. Use Decision Required only for mutually exclusive response strategies that the user must select; otherwise write None.",
                    artifact_path="rebuttal/REVIEW_TRIAGE.md",
                    artifact_kind="review",
                    required_sections=[
                        "Review Summary",
                        "Critical Blockers",
                        "Major Concerns",
                        "Minor Concerns",
                        "Minimum Fixes",
                        "Evidence Gaps",
                        "Response Strategy",
                        "Questions for Human Review",
                        "Decision Required",
                    ],
                    skill_paths=_skills(
                        "auto-review-loop",
                        "research-review",
                        "rebuttal",
                        "kill-argument",
                        "integrity-forensics",
                        "experiment-audit",
                        "paper-claim-audit",
                        "citation-audit",
                    ),
                    hitl=True,
                    checkpoint_title="Rebuttal Direction Approval",
                ),
                StageDefinition(
                    name="rebuttal_draft",
                    title="Rebuttal Draft",
                    instruction="Write a reviewer-by-reviewer rebuttal draft that is direct, evidence-based, and honest about open issues. Separate accepted issues, partial agreement, and rebuttal points so the response is easy to review and revise.",
                    artifact_path="rebuttal/REBUTTAL_DRAFT.md",
                    artifact_kind="review",
                    required_sections=[
                        "Reviewer Summary",
                        "Opening Summary",
                        "Point-by-Point Responses",
                        "Accepted Changes",
                        "Committed Changes",
                        "Unresolved Limits",
                    ],
                    skill_paths=_skills(
                        "rebuttal",
                        "kill-argument",
                        "claims-drafting",
                        "research-review",
                        "paper-claim-audit",
                    ),
                ),
                StageDefinition(
                    name="revision_plan",
                    title="Revision Plan",
                    instruction="Turn the triage and rebuttal into a concrete revision execution plan with ordered tasks, owners, dependencies, and evidence needed to close the loop.",
                    artifact_path="rebuttal/REVISION_PLAN.md",
                    artifact_kind="plan",
                    required_sections=[
                        "Revision Tasks",
                        "Owners",
                        "Dependencies",
                        "Priority",
                        "Artifact Updates",
                        "Verification Checklist",
                    ],
                    skill_paths=_skills(
                        "auto-review-loop",
                        "resubmit-pipeline",
                        "ablation-planner",
                        "experiment-audit",
                        "citation-audit",
                        "paper-claim-audit",
                        "result-to-claim",
                    ),
                ),
            ],
        ),
        "/present": WorkflowDefinition(
            command="/present",
            title="Presentation Workflow",
            description="Turn workspace evidence into an approved, image-rendered research deck.",
            stage_definitions=[
                StageDefinition(
                    name="slides_outline",
                    title="Slides Outline",
                    instruction=(
                        "Read only the frozen presentation SourceSet supplied in the context. Detect whether this is a stage report "
                        "or a paper talk, extract the problem, method, progress, evidence, limitations, and next steps, "
                        "then prepare a slide-by-slide story and page-level rendering plan. Every slide must specify Page Type, "
                        "Render Mode, Layout Hint, one claim, and source files. Use image2_full for cover, section, explanation, "
                        "synthesis, and conclusion pages; Image-2 will create the complete page and nothing may be overlaid later. "
                        "Use evidence only for a separate original-figure or original-table page and provide exactly one primary "
                        "asset_id whenever possible. Never assign a paper figure or table to the cover. Never mix Image-2 artwork "
                        "and an original evidence asset on the same page. Aim for roughly 60-75% image2_full pages and 25-40% "
                        "evidence pages, adapting to the material. Under Decision Required, write None unless two or more genuine "
                        "narrative or design alternatives require the user to choose."
                    ),
                    artifact_path="presentation/SLIDES_OUTLINE.md",
                    artifact_kind="slides",
                    required_sections=[
                        "Talk Arc",
                        "Slide List",
                        "Key Evidence per Slide",
                        "Open Design Questions",
                        "Decision Required",
                    ],
                    skill_paths=_skills(
                        "paper-slides",
                        "paper-talk",
                        "paper-poster",
                        "paper-poster-html",
                        "slides-polish",
                        "scientific-slides",
                    ),
                    hitl=True,
                    checkpoint_title="Presentation Outline Approval",
                ),
                StageDefinition(
                    name="slide_content",
                    title="Slide Content",
                    instruction=(
                        "Expand the approved outline into exact page-level content. Use one H2 heading per slide in "
                        "the form 'Slide N: Title'. Under each slide include Page Type, Render Mode, Layout Hint, Main Message, "
                        "On-Slide Text, Visual, Source Files, and Asset IDs. Render Mode must be exactly image2_full or evidence. "
                        "For image2_full, Asset IDs must be None because the generated image is the complete final slide. "
                        "For evidence, provide a valid original asset_id and describe a restrained full-page evidence layout; "
                        "do not request Image-2. Keep text concise, preserve exact numbers, and never invent evidence."
                    ),
                    artifact_path="presentation/SLIDE_CONTENT.md",
                    artifact_kind="slides",
                    required_sections=[
                        "Slide N: Title",
                        "Page Type",
                        "Render Mode",
                        "Layout Hint",
                        "Main Message",
                        "On-Slide Text",
                        "Visual",
                        "Source Files",
                        "Asset IDs",
                    ],
                    skill_paths=_skills(
                        "paper-slides",
                        "paper-talk",
                        "slides-polish",
                        "result-to-claim",
                        "paper-claim-audit",
                        "scientific-slides",
                    ),
                ),
                StageDefinition(
                    name="speaker_notes",
                    title="Speaker Notes",
                    instruction=(
                        "Write presenter-ready speaker notes that exactly follow SLIDE_CONTENT.md. Under Per-Slide "
                        "Notes, create one 'Slide N: Title' section per main slide and provide a natural spoken script "
                        "that can be delivered directly, not just keywords or internal production instructions. Add a "
                        "suggested duration and a concise transition for every slide. Keep claims and numbers grounded "
                        "in the selected sources; do not invent author metadata or results."
                    ),
                    artifact_path="presentation/SPEAKER_NOTES.md",
                    artifact_kind="slides",
                    required_sections=[
                        "Per-Slide Notes",
                        "Timing",
                        "Transitions",
                        "Backup Slides",
                    ],
                    skill_paths=_skills(
                        "paper-talk",
                        "paper-slides",
                        "interview-cheatsheet",
                        "slides-polish",
                    ),
                ),
                StageDefinition(
                    name="qa_brief",
                    title="Q and A Brief",
                    instruction="Prepare anticipated questions, concise answers, and follow-up evidence pointers.",
                    artifact_path="presentation/QA_BRIEF.md",
                    artifact_kind="note",
                    required_sections=[
                        "Likely Questions",
                        "Recommended Answers",
                        "Evidence Pointers",
                    ],
                    skill_paths=_skills(
                        "interview-cheatsheet",
                        "kill-argument",
                        "research-review",
                        "paper-claim-audit",
                        "result-to-claim",
                    ),
                ),
            ],
        ),
        "/wiki": WorkflowDefinition(
            command="/wiki",
            title="Research Wiki Workflow",
            description="Consolidate reusable memory and workspace notes.",
            stage_definitions=[
                StageDefinition(
                    name="knowledge_digest",
                    title="Knowledge Digest",
                    instruction="Summarize the reusable knowledge from the current request into a concise memory note, including claims, evidence, failures, and next-use cues.",
                    artifact_path="wiki/KNOWLEDGE_DIGEST.md",
                    artifact_kind="wiki",
                    required_sections=[
                        "Reusable Knowledge",
                        "Claims and Evidence",
                        "Failures to Remember",
                        "Reuse Cues",
                    ],
                    skill_paths=_skills(
                        "research-wiki",
                        "wiki-enrich",
                        "research-review",
                        "result-to-claim",
                    ),
                ),
                StageDefinition(
                    name="memory_update",
                    title="Memory Update",
                    instruction="Write a concise update describing how this material should be stored in the local research wiki and how it should be reused in future tasks.",
                    artifact_path="wiki/MEMORY_UPDATE.md",
                    artifact_kind="wiki",
                    required_sections=[
                        "Suggested Nodes",
                        "Suggested Links",
                        "Future Retrieval Prompts",
                    ],
                    skill_paths=_skills(
                        "research-wiki",
                        "wiki-enrich",
                        "research-pipeline",
                    ),
                ),
            ],
        ),
    }

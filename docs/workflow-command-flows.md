# Research command flows

This document describes the current command boundaries and implementation paths. `/review`, `/idea`, and `/plan` can run independently, but they form a natural evidence-to-execution handoff when used in one session.

## Shared runtime

```mermaid
flowchart TD
    A["User command or natural-language request"] --> B["Intent router"]
    B --> C["Create TaskRun"]
    C --> D["Initialize agent-workspace/local/session_id"]
    D --> E["Start LangGraph StateGraph"]
    E --> F["Execute workflow stage"]
    F --> G["Write artifact and manifest"]
    G --> H["Incremental Seafile sync when enabled"]
    H --> I{"Genuine user decision required?"}
    I -->|No| J["Continue automatically"]
    I -->|Yes| K["Write checkpoint and interrupt"]
    K --> L{"Approve or revise"}
    L -->|Approve| J
    L -->|Revise| F
    J --> M["Finalize, write Wiki record, sync workspace"]
```

The local UI uses `user_id=local`. Cloud sync mirrors the same boundary to `SEAFILE_REMOTE_ROOT/local/<session_id>/` and exposes folder preview/download links through `cloud_workspace` in API responses.

## `/review`: literature evidence

```mermaid
flowchart TD
    A["/review + research question"] --> B["Scholar multi-provider retrieval"]
    B --> B1["bib/LITERATURE_SEARCH.md and JSON"]
    B1 --> C["Research Brief"]
    C --> C1["bib/RESEARCH_BRIEF.md"]
    C1 --> D["Literature Synthesis"]
    D --> D1["bib/LITERATURE_REVIEW.md"]
    D1 --> E["Evidence Map"]
    E --> E1["bib/EVIDENCE_MAP.md"]
    E1 --> F["Research Gaps"]
    F --> F1["bib/RESEARCH_GAPS.md"]
    F1 --> G["Handoff evidence to /idea and /plan"]
```

`/review` means literature review. It searches OpenAlex, Semantic Scholar, and arXiv by default; Web of Science and CNKI are enabled by configuration. It does not process peer-review comments.

## `/idea`: candidate selection

```mermaid
flowchart TD
    A["/idea + research direction"] --> B["Read prior review evidence when available"]
    B --> C["Targeted novelty retrieval when needed"]
    C --> D["Idea Candidates"]
    D --> D1["idea/IDEA_CANDIDATES.md"]
    D1 --> E{"Multiple genuine directions require selection?"}
    E -->|Yes| F["Topic Selection Approval"]
    F -->|Revise| D
    F -->|Approve| G["Idea Verification"]
    E -->|No| G
    G --> G1["idea/IDEA_VERIFICATION.md"]
    G1 --> H["Final Idea"]
    H --> H1["idea/FINAL_IDEA.md"]
    H1 --> I["idea/docs/research_contract.md"]
    I --> J["Handoff selected direction to /plan"]
```

`/idea` generates and validates directions. It may perform a targeted novelty search, but it does not write an experiment plan.

## `/plan`: experiment and execution design

```mermaid
flowchart TD
    A["/plan + objective"] --> B{"Prior FINAL_IDEA exists?"}
    B -->|Yes| C["Use selected idea, contract, and review evidence"]
    B -->|No| D["Treat user objective as selected direction"]
    C --> E["Research Blueprint"]
    D --> E
    E --> E1["plan/RESEARCH_BLUEPRINT.md"]
    E1 --> F["Experiment Plan"]
    F --> F1["plan/EXPERIMENT_PLAN.md"]
    F1 --> G["Execution Checklist"]
    G --> G1["plan/EXECUTION_CHECKLIST.md"]
    G1 --> H["Handoff to /code"]
```

`/plan` owns hypotheses, claim-to-evidence requirements, datasets, baselines, metrics, ablations, sanity checks, resources, launch order, stop conditions, milestones, and the execution checklist.

## `/rebuttal`: peer-review response

```mermaid
flowchart TD
    A["/rebuttal + reviewer comments"] --> B["Review Triage"]
    B --> B1["rebuttal/REVIEW_TRIAGE.md"]
    B1 --> C{"Mutually exclusive response strategies?"}
    C -->|Yes| D["Rebuttal Direction Approval"]
    D -->|Revise| B
    D -->|Approve| E["Rebuttal Draft"]
    C -->|No| E
    E --> E1["rebuttal/REBUTTAL_DRAFT.md"]
    E1 --> F["Revision Plan"]
    F --> F1["rebuttal/REVISION_PLAN.md"]
```

The former peer-review behavior of `/review` now belongs to `/rebuttal`. `/auto-review-loop` and `/review-response` route to `/rebuttal` for compatibility.

## `/present`: deck production

```mermaid
flowchart TD
    A["/present + reporting objective"] --> B["Resolve paper/stage mode and source scope"]
    B --> C["Freeze SourceSet and extract original assets"]
    C --> D["presentation/SLIDES_OUTLINE.md"]
    D --> E{"Genuine narrative/design choice?"}
    E -->|Yes| F["Presentation Outline Approval"]
    F -->|Revise| D
    F -->|Approve| G["Slide Content"]
    E -->|No| G
    G --> H["Speaker Notes and Q&A"]
    H --> I{"Page render mode"}
    I -->|image2_full| J["gpt-image-2 creates complete standalone slide"]
    I -->|evidence| K["Original figure/table gets standalone evidence page"]
    J --> L["Assemble PPTX with native speaker notes"]
    K --> L
    L --> M["PAPER_TALK.pptx or STAGE_REPORT.pptx"]
```

Image-2 pages and original-evidence pages remain separate. Original figures and tables are never overlaid on Image-2 narrative pages.

## Cloud lifecycle

```mermaid
flowchart LR
    A["Workspace initialized"] --> B["Create remote session directories"]
    C["Artifact or checkpoint written"] --> D["Compare file signatures"]
    E["User uploads files"] --> D
    B --> D
    D -->|Changed| F["Upload with Seafile upload-link"]
    D -->|Unchanged| G["Skip"]
    F --> H["Create or reuse folder share link"]
    G --> H
    H --> I["Return preview/download URL"]
```

Cloud sync failures are recorded in `ChatSession.cloud_workspace.error` and the task progress log. They do not fail the research workflow.

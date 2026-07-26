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

## `/write`: evidence-grounded paper production

```mermaid
flowchart TD
    A["/write + uploaded or workspace materials"] --> B["Freeze writing SourceSet"]
    B --> B1["Content/PAPER_SOURCE_SELECTION.json"]
    B --> C["Extract stable source/page/provenance records"]
    C --> C1["paper/PAPER_EVIDENCE_MAP.json"]
    C1 --> D["Paper Plan and paragraph jobs"]
    D --> E{"Genuine venue/story choice?"}
    E -->|Yes| F["Writing Outline Approval"]
    F -->|Revise| D
    F -->|Approve| G["Narrative report and complete first draft"]
    E -->|No| G
    G --> H["Independent paper self-review with stable issue IDs"]
    H --> I["Evidence-preserving complete revision"]
    I --> J["Citation and delivery gates"]
    J --> K["DOCX / PDF / TeX exports from PAPER_REVISED.md"]
```

The deterministic gates validate source presence, required sections, citation-key resolution, evidence-ID resolution, placeholders, and compile status. They do not claim that citations semantically support each sentence; author verification remains required.

## `/rebuttal`: peer-review response

```mermaid
flowchart TD
    A["/rebuttal + completed paper + reviewer comments"] --> B{"Both input classes available?"}
    B -->|No| C["Fail with explicit missing-input message"]
    B -->|Yes| D["Freeze paper/review SourceSet"]
    D --> D1["rebuttal/REBUTTAL_INPUTS.md"]
    D --> D2["Content/REBUTTAL_SOURCE_SELECTION.json"]
    D1 --> E["Map every comment to paper section, claim, figure, table, and evidence"]
    E --> E1["rebuttal/REVIEW_TO_PAPER_MAP.md"]
    E1 --> F["Response Strategy"]
    F --> F1["rebuttal/RESPONSE_STRATEGY.md"]
    F1 --> G{"Mutually exclusive unresolved strategies?"}
    G -->|Yes| H["Rebuttal Strategy Decision"]
    H -->|Revise| F
    H -->|Approve| I["Point-by-point Rebuttal Draft"]
    G -->|No| I
    I --> I1["rebuttal/REBUTTAL_DRAFT.md"]
    I1 --> J["Section-level Revision Plan"]
    J --> J1["rebuttal/REVISION_PLAN.md"]
    J1 --> K["Apply supported edits to complete revised manuscript"]
    K --> K1["paper/PAPER_REVISED_AFTER_REVIEW.md"]
    K1 --> L["Per-comment revision ledger"]
    L --> L1["rebuttal/REVISION_LEDGER.md"]
    L1 --> M["Deterministic comment-ID closure gate"]
    M --> M1["rebuttal/REBUTTAL_CLOSURE_REPORT.json"]
```

`/rebuttal` does not search for literature and does not infer a manuscript from the objective. Input priority is explicit `--paper`/`--review` paths, then the latest matching upload batch, then the newest final-paper material under `paper/` and review material under `rebuttal/uploads/`. The SourceSet is frozen at task start. A checkpoint appears only when evidence cannot resolve two or more genuinely mutually exclusive response strategies. `/auto-review-loop` and `/review-response` route to `/rebuttal` for compatibility.

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

For Tsinghua Seafile, the local configuration tool exchanges a hidden password prompt for an API token and stores only the token in `.env`. The `/chat` sync icon or `POST /api/sessions/{session_id}/sync` then uploads the current session and refreshes its folder share links.

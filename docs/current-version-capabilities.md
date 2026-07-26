# Current version capabilities and technical implementation

## Runtime and workspace

- **Session isolation:** every local session uses `agent-workspace/local/<session_id>/`; `ArtifactStore` enforces the standard top-level directories and rejects path traversal.
- **Workflow execution:** `LangGraphWorkflowRuntime` compiles one persistent `StateGraph` per command. `TaskRun` and `ChatSession` are stored as JSON; graph checkpoints are persisted separately for restart recovery.
- **Human decisions:** only stages marked `hitl=True` can pause. The generated `Decision Required` section must contain at least two concrete options, unless the user explicitly requested review before continuing.
- **Research memory:** every completed task is summarized into the local research Wiki and prior-task artifacts are selectively injected into later prompts.

## Research commands

- **`/review`:** uses `ScholarSearchService` to query OpenAlex, Semantic Scholar, arXiv, optional Web of Science, and adapter-based CNKI. It writes a scoped brief, synthesis, evidence map, and research-gap report under `bib/`.
- **`/idea`:** uses literature and novelty skills to generate candidates, performs an independent critic stage, and writes `FINAL_IDEA.md` plus a research contract. It uses targeted retrieval when evidence is missing and does not produce experiment plans.
- **`/plan`:** consumes `FINAL_IDEA`, the research contract, and review evidence when available. Three stages produce a research blueprint, claim-driven experiment plan, and execution checklist.
- **`/rebuttal`:** requires a completed paper plus reviewer comments, freezes a typed dual-source input set, extracts both documents, maps every comment to manuscript sections/claims/figures/tables/evidence, pauses only for genuinely mutually exclusive response strategies, then drafts traceable point-by-point responses and a section-level revision plan.
- **`/code`:** produces an implementation plan, launch runbook, and local collaboration handoff for executing experiments.
- **`/fig`:** produces a figure inventory and implementation briefs, then calls `gpt-image-2` for final image delivery with prompt and metadata traceability.
- **`/write`:** produces a paper plan, narrative report, and full Markdown draft. Delivery post-processing exports requested DOCX, PDF, and LaTeX formats using native document libraries and optional local TeX compilation.
- **`/present`:** freezes an attachment/selected/session/workspace SourceSet, extracts original figures and tables, creates page-level `image2_full` or `evidence` contracts, renders complete narrative pages with `gpt-image-2`, independently lays out original evidence pages, and assembles PPTX with native speaker notes.
- **`/wiki`:** produces a reusable knowledge digest and memory-update proposal, then records the completed task in the local Wiki.

## Files and APIs

- **Drag-and-drop uploads:** `POST /api/session/files` sanitizes names, enforces file count/size limits, classifies files into workspace directories, records upload batches, and lets `/present` and `/rebuttal` freeze task-specific source sets. Reviewer-comment filenames are recognized and routed to `rebuttal/uploads/` before generic paper classification.
- **OpenAI-compatible surface:** `/v1/chat/completions` and `/v1/responses` route messages through the same research workflows.
- **Local artifacts:** `/workspace-files/...` serves generated files; task APIs return artifact paths, status, progress, checkpoints, and cloud workspace metadata.
- **Presentation traceability:** source selection, extracted assets, page specs, Image-2 prompts, render metadata, and structured speaker notes are stored under `Content/`.
- **Rebuttal traceability:** `Content/REBUTTAL_SOURCE_SELECTION.json` records the frozen paper and review files; `rebuttal/REVIEW_TO_PAPER_MAP.md` carries stable reviewer/comment IDs into response strategy, rebuttal drafting, and revision planning.

## Seafile cloud workspace

- **Protocol:** the connector uses Seafile REST API endpoints rather than the optional Python SDK or a required local CLI installation.
- **Authentication:** API token is preferred; username/password token exchange is a fallback for instances that permit it. Secrets are loaded only from `.env`.
- **Remote structure:** local `agent-workspace/<user_id>/<session_id>/` maps to `SEAFILE_REMOTE_ROOT/<user_id>/<session_id>/` inside one Seafile library.
- **Incremental sync:** `Content/CLOUD_SYNC.json` records size and modification-time signatures. Each sync uploads only changed files through a Seafile upload link.
- **Lifecycle hooks:** synchronization runs after workspace initialization, user uploads, each workflow stage, checkpoint creation, and final delivery.
- **Links and failure handling:** the connector creates or reuses a folder share link and returns it as preview/download URLs. Authentication or network errors are visible in task/session state but do not fail the scientific workflow.

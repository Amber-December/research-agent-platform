# Current version capabilities and technical implementation

## Runtime and workspace

- **Session isolation:** every local session uses `agent-workspace/local/<session_id>/`; `ArtifactStore` enforces the standard top-level directories and rejects path traversal.
- **Workflow execution:** `LangGraphWorkflowRuntime` compiles one persistent `StateGraph` per command. `TaskRun` and `ChatSession` are stored as JSON; graph checkpoints are persisted separately for restart recovery.
- **Human decisions:** only stages marked `hitl=True` can pause. The generated `Decision Required` section must contain at least two concrete options, unless the user explicitly requested review before continuing.
- **Research memory:** every completed task is summarized into the local research Wiki and prior-task artifacts are selectively injected into later prompts.

## Research commands

- **`/review`:** uses `ScholarSearchService` to query OpenAlex, Semantic Scholar, arXiv, optional Web of Science, and adapter-based CNKI. Formal synthesis requires at least 10 admitted and traceable sources. Explicit public PDF URLs are downloaded into `bib/papers/` with per-paper status in `bib/LITERATURE_DOWNLOADS.json`; inaccessible or paywalled records remain metadata-only.
- **`/idea`:** uses literature and novelty skills to generate candidates, performs an independent critic stage, and writes `FINAL_IDEA.md` plus a research contract. It uses targeted retrieval when evidence is missing, does not produce experiment plans, and does not stop for routine approval.
- **`/plan`:** consumes `FINAL_IDEA`, the research contract, and review evidence when available. Three stages produce a research blueprint, claim-driven experiment plan, and execution checklist.
- **`/rebuttal`:** requires a completed paper plus reviewer comments, freezes a typed dual-source input set, maps stable comment IDs to manuscript evidence, pauses only for genuinely mutually exclusive strategies, drafts point-by-point responses, produces a revised manuscript and per-comment revision ledger, and runs a deterministic closure gate.
- **`/code`:** produces an implementation plan, launch runbook, and local collaboration handoff for executing experiments.
- **`/fig`:** produces a figure inventory and implementation briefs, then calls `gpt-image-2` for final image delivery with prompt and metadata traceability.
- **`/write`:** freezes a typed writing SourceSet, extracts stable evidence IDs and source/page provenance, builds a paragraph/claim plan, writes a complete draft, independently self-reviews it, produces an evidence-preserving revision, then runs citation-key and delivery gates before exporting DOCX, PDF, and LaTeX from the revised manuscript.
- **`/present`:** freezes an attachment/selected/session/workspace SourceSet, extracts original figures and tables, creates page-level `image2_full` or `evidence` contracts, renders complete narrative pages with `gpt-image-2`, independently lays out original evidence pages, and assembles PPTX with native speaker notes.
- **`/wiki`:** produces a reusable knowledge digest and memory-update proposal, then records the completed task in the local Wiki.

## Files and APIs

- **Drag-and-drop uploads:** `POST /api/session/files` sanitizes names, enforces file count/size limits, classifies files into workspace directories, records upload batches, and lets `/present` and `/rebuttal` freeze task-specific source sets. Reviewer-comment filenames are recognized and routed to `rebuttal/uploads/` before generic paper classification.
- **OpenAI-compatible surface:** `/v1/chat/completions` and `/v1/responses` route messages through the same research workflows.
- **Local artifacts:** `/workspace-files/...` serves generated files; task APIs return artifact paths, status, progress, checkpoints, and cloud workspace metadata.
- **Presentation traceability:** source selection, extracted assets, page specs, Image-2 prompts, render metadata, and structured speaker notes are stored under `Content/`.
- **Rebuttal traceability:** `Content/REBUTTAL_SOURCE_SELECTION.json` records the frozen paper and review files; `rebuttal/REVIEW_TO_PAPER_MAP.md` carries stable reviewer/comment IDs into response strategy, rebuttal drafting, and revision planning.
- **Paper traceability:** `Content/PAPER_SOURCE_SELECTION.json`, `Content/PAPER_VENUE_PROFILE.json`, and `paper/PAPER_EVIDENCE_MAP.json` separate input selection, article/venue requirements, and extracted evidence. `paper/CITATION_AUDIT.json` and `paper/PAPER_DELIVERY_REPORT.json` report deterministic checks without claiming semantic correctness.

## Seafile cloud workspace

- **Protocol:** the connector uses Seafile REST API endpoints rather than the optional Python SDK or a required local CLI installation.
- **Authentication:** API token is preferred; username/password token exchange is a fallback for instances that permit it. Secrets are loaded only from `.env`.
- **Safe Tsinghua setup:** `tools/configure_tsinghua_seafile.py` reads the password through a hidden terminal prompt, exchanges it for an API token, and persists only the token in the Git-ignored `.env`.
- **Remote structure:** local `agent-workspace/<user_id>/<session_id>/` maps to `SEAFILE_REMOTE_ROOT/<user_id>/<session_id>/` inside one Seafile library.
- **Incremental sync:** `Content/CLOUD_SYNC.json` records size and modification-time signatures. Each sync uploads only changed files through a Seafile upload link.
- **Lifecycle hooks:** synchronization runs after workspace initialization, user uploads, each workflow stage, checkpoint creation, and final delivery.
- **Links and failure handling:** the connector creates or reuses a folder share link and returns it as preview/download URLs. Authentication or network errors are visible in task/session state but do not fail the scientific workflow.
- **Manual refresh:** the chat sync icon calls `POST /api/sessions/{session_id}/sync` to upload current changes and refresh the folder links on demand.

## Streaming task progress

- `/api/agent/chat` creates a routed workflow task and returns its `task_id` immediately; the API background worker executes the LangGraph task.
- `GET /api/tasks/{task_id}/events` emits SSE `snapshot`, `progress`, and `done` events. The event payload contains only operationally auditable progress, not hidden model chain-of-thought.
- Ordinary questions from `/chat` use a lightweight `/chat` task and the same SSE endpoint; OpenAI-compatible `/v1/*` calls remain synchronous.
- The UI reconnects through the task status endpoint when SSE is unavailable, so a dropped browser connection does not lose the task.
- Cloud sync is a one-way incremental mirror. It requires `CLOUD_SYNC_ENABLED=true`, `SEAFILE_BASE_URL`, and either `SEAFILE_API_TOKEN` or username/password in the local ignored `.env`; the service must be restarted after configuration.

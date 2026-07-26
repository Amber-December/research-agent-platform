# research-agent-platform

Research agent platform aligned to the PRD and tech spec, grounded by ARIS skill documents from `Auto-claude-code-research-in-sleep`.

## Layout

- `router/`
- `state/`
- `graphs/`
- `connectors/`
- `memory/`
- `artifacts/`
- `ui/`

## Run

```bash
uv sync --no-editable --project J:\Desktop\科研agent\research-agent-platform
uv run --project J:\Desktop\科研agent\research-agent-platform uvicorn --app-dir src research_agent_platform.api:app --host 127.0.0.1 --port 8000
```

## OpenAI-compatible API

- `GET /v1/models`
- `POST /v1/chat/completions`
- `POST /v1/responses`

## Local chat and HITL

- Open `http://127.0.0.1:8000/chat`
- The page talks to the local research-agent workflow, not a plain echo proxy
- Human checkpoints can be approved or revised in the page
- Research materials can be dragged onto the chat page or selected with the file picker. Uploads are stored under the current session workspace without starting a workflow.
- Files are written under `agent-workspace/<user_id>/<session_id>/` and exposed at `/workspace-files/...`
- Local UI sessions use `agent-workspace/local/<session_id>/`; deployed clients can pass `metadata.user_id` for per-user isolation.
- See `docs/workspace-layout.md` for the ARIS-style workspace layout

## Research workflow commands

- `/review` searches and synthesizes literature. It writes a research brief, literature review, evidence map, and research gaps under `bib/`.
- `/idea` generates candidate ideas, stress-tests novelty and feasibility, and writes the selected direction under `idea/FINAL_IDEA.md`. It may use targeted literature search but does not create the experiment plan.
- `/plan` turns `FINAL_IDEA` or a directly supplied research objective into `plan/RESEARCH_BLUEPRINT.md`, `plan/EXPERIMENT_PLAN.md`, and `plan/EXECUTION_CHECKLIST.md`.
- `/rebuttal` owns peer-review triage, rebuttal drafting, and revision planning under `rebuttal/`.
- `/code`, `/fig`, `/write`, `/present`, and `/wiki` continue implementation planning, figure production, paper drafting, presentation generation, and persistent research memory.

Each command can run independently. When prior `/review` or `/idea` tasks exist in the same session, downstream commands prioritize their evidence map, research gaps, final idea, and research contract as handoff context.

## Presentation workflow

- Presentation type and source scope are independent. Use `--type paper|stage` and `--source attachments|selected|session|workspace` when explicit control is needed.
- In automatic source mode, an explicit file/directory reference wins; otherwise the latest upload batch is used. The workflow searches the workspace only when requested or when no uploaded material exists.
- `/present --type paper --source attachments 论文汇报` uses only the latest uploaded PDF, Word, spreadsheet, image, or presentation batch.
- `/present --type stage --source workspace 阶段汇报` retrieves a limited, ranked set of relevant files from plans, figures, logs, notes, paper fragments, code, and other standard workspace directories.
- `/present --source selected \`paper/draft.pdf\` \`figures/result.png\`` freezes only the named files or directories as the task SourceSet.
- The workflow writes `presentation/SLIDES_OUTLINE.md`; it pauses only when the outline contains a genuine user choice that requires approval.
- Source selection and extracted assets are recorded in `Content/PRESENTATION_SOURCE_SELECTION.json`, `Content/PRESENTATION_SOURCE_INDEX.md`, and `Content/PRESENTATION_ASSETS.json`.
- PDF/Word/PPT images are extracted as original media. Reliable CSV/XLSX/Word tables become editable PowerPoint tables; PDF publication tables are retained as high-resolution original crops.
- `gpt-image-2` renders complete standalone narrative pages under `presentation/generated/`; original figures and tables are independently laid out on evidence pages and never mixed with Image-2 pages.
- `presentation/SPEAKER_NOTES.md` contains the generated talk script. The workflow embeds per-slide narration, timing, and transitions into native PowerPoint speaker notes and records the mapping in `Content/SPEAKER_NOTES.json`.
- `Content/SLIDE_SPECS.json` records the render policy and source asset used by each page; the final deck with speaker notes is written as `presentation/STAGE_REPORT.pptx` or `presentation/PAPER_TALK.pptx`.
- Choose a built-in template with `模板: stage-report` or `模板: paper-talk`. `PRESENTATION_TEMPLATE=auto` selects one from the requested mode.

## File uploads

- `POST /api/session/files` accepts multipart uploads with `files`, optional `session_id`, optional `user_id`, and `target`.
- Each upload response contains an `upload_batch_id`; `/present` uses the latest batch when source scope is automatic or `attachments`.
- `target=auto` routes images to `figures/uploads/`, paper documents to `paper/uploads/`, presentations to `presentation/uploads/`, bibliography files to `bib/uploads/`, code to `code/uploads/`, and other files to `Content/uploads/`.
- A standard directory name can be passed as `target` to override automatic classification.
- Upload limits are configured with `UPLOAD_MAX_FILES` and `UPLOAD_MAX_FILE_MB`.

## Optional Seafile cloud workspace

- Set `CLOUD_SYNC_ENABLED=true` to mirror `agent-workspace/<user_id>/<session_id>/` to `SEAFILE_REMOTE_ROOT/<user_id>/<session_id>/`.
- The Agent creates the remote session directory when the workspace is initialized, then uploads changed files after every workflow stage, checkpoint, final delivery, and user upload.
- `Content/CLOUD_SYNC.json` stores local file signatures so unchanged files are skipped on later syncs.
- Configure an existing library with `SEAFILE_REPO_ID`, or let the connector find/create `SEAFILE_REPO_NAME` when the account permits it.
- Prefer `SEAFILE_API_TOKEN`. `SEAFILE_USERNAME` and `SEAFILE_PASSWORD` are only a fallback for instances that support `/api2/auth-token/`; institutional single sign-on may require an API token or app-specific password.
- When `SEAFILE_SHARE_LINKS=true`, API responses expose `cloud_workspace.preview_url` and `cloud_workspace.download_url`. The chat UI shows these links in the cloud workspace section.
- Never commit `.env` or send the account password in chat. Real credentials remain in the local `.env`, which is excluded by `.gitignore`.

## Deploy

```bash
uv sync --no-editable --project J:\Desktop\科研agent\research-agent-platform
uv run --project J:\Desktop\科研agent\research-agent-platform uvicorn --app-dir src research_agent_platform.api:app --host 0.0.0.0 --port 8000
```

## OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(api_key="dummy", base_url="http://YOUR_HOST:8000/v1")
```

## Configure ARIS grounding

Set `ARIS_REPO_ROOT` in `.env` if the ARIS repo is not at the default sibling path.

## Literature providers

- `OpenAlex`, `Semantic Scholar`, and `arXiv` are enabled by default.
- `Web of Science` is enabled when `WOS_API_KEY` is set. The default endpoint is the Clarivate Starter API.
- `CNKI` is supported through an institutional or relay endpoint configured by `CNKI_SEARCH_ENDPOINT`.
- `CNKI` is intentionally adapter-based here; I did not add scraping because that is fragile and usually non-compliant.

## Upstream model

- If your relay exposes many model ids, set `UPSTREAM_MODEL` explicitly.
- If `UPSTREAM_MODEL` is empty, the platform now prefers chat-capable models such as `gpt-5.4-mini` instead of taking the first returned model blindly.
- `/fig` uses `IMAGE_MODEL`, which defaults to `gpt-image-2`.

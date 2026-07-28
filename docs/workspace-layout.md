# Workspace Layout
Each online user session gets an isolated artifact workspace.

## Root

```text
agent-workspace/
  <user_id>/
    <session_id>/
```

`user_id` comes from request metadata when available. Local UI sessions and API requests without an explicit user use `local`.

## Session Workspace

```text
<session_id>/
  bib/
  plan/
  idea/
  code/
  figures/
  paper/
  presentation/
  rebuttal/
  wiki/
  Content/
    MANIFEST.md
  logs/
```

## Directory Meaning

- `bib/`: reference materials, bibliography files, citation exports, and PDF/HTML/PSD reference snapshots.
- `plan/`: research plans, final proposals, experiment plans, execution checklists.
- `idea/`: literature landscape, idea reports, novelty notes, research contracts.
- `code/`: implementation plans, runbooks, local collaboration notes, scripts.
- `figures/`: figure inventory, figure briefs, generated images, figure metadata.
- `paper/`: frozen evidence map, paper plans, narrative report, first draft, self-review, evidence-preserving revised manuscripts, citation/delivery reports, LaTeX, Word, PDF, and compile logs.
- `presentation/`: slide outlines, page content, speaker-note scripts, QA briefs, generated slide pages, and PPTX exports with native per-slide notes.
- `rebuttal/`: uploaded reviewer comments, frozen input manifest, review-to-paper map, response strategy, rebuttal draft, revision plan, per-comment revision ledger, and closure report.
- `wiki/`: reusable memory notes, knowledge digests, and `wiki/agent-notes/<task_id>.md` task records. There is no separate project-level research-artifact wiki.
- `Content/`: session context, source indexes, human checkpoints, generation prompts, traceability metadata, and the artifact manifest used for stage reporting.
- `logs/`: runtime logs and diagnostics.

The directory names above are the complete standard workspace contract. Workflow tasks share the same session root so later stages can directly consume earlier materials.

All model-generated research files must stay inside this session root. `.agent-state/` is reserved for backend execution state only; the project root and any legacy `research-wiki/` directory are not valid destinations for session artifacts.

When cloud delivery is configured, initialization and every artifact write trigger an incremental mirror of this entire session root. A completed workflow response must expose the session's cloud preview/download URL; deployments with `CLOUD_DELIVERY_REQUIRED=true` treat a missing link as a delivery failure rather than silently returning only a local path.

## Presentation Modes

- Stage report prioritizes `plan/`, `code/`, `figures/`, `Content/`, and `logs/`, then supplements them with paper and review materials.
- Paper talk prioritizes final products under `paper/`, then uses figures, rebuttal notes, bibliography, plans, and context as supporting evidence.
- Both modes generate `presentation/SLIDES_OUTLINE.md` first. A human checkpoint is created only for a genuine unresolved choice; otherwise page generation and PPTX assembly continue automatically.

## Qingxiaoda Metadata

OpenAI-compatible requests should pass stable user/session identifiers when possible:

```json
{
  "model": "research-agent-platform",
  "messages": [{"role": "user", "content": "/present 鍋氶樁娈垫眹鎶?}],
  "metadata": {
    "user_id": "qingxiaoda-user-123",
    "session_id": "qingxiaoda-session-456"
  }
}
```

The service still works without metadata; those artifacts go under `local/<session_id>/`. Backend deployments can continue passing a real `user_id` to isolate different users.

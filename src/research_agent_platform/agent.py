from __future__ import annotations

import asyncio
import json
import re
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

from .connectors import ScholarSearchService, SeafileWorkspaceSync
from .artifacts.store import ArtifactStore
from .config import config
from .document_exports import (
    detect_write_formats,
    markdown_to_docx_bytes,
    markdown_to_latex,
    markdown_to_pdf_bytes,
)
from .graphs.runtime import LangGraphWorkflowRuntime
from .graphs.workflows import StageDefinition, WorkflowDefinition, workflow_registry
from .memory.wiki import WikiService
from .models import ApprovalCheckpoint, ChatSession, CloudWorkspaceState, MessageRecord, TaskRun, utc_now
from .presentation import (
    SlideRender,
    assemble_mixed_deck,
    build_slide_prompt,
    collect_workspace_evidence,
    compose_slide_preview,
    crop_slide_image,
    enforce_presentation_page_mix,
    extract_presentation_assets,
    parse_slide_content,
    parse_speaker_notes,
    presentation_design_spec_to_json,
    presentation_assets_from_json,
    presentation_assets_to_json,
    reconcile_slide_specs,
    resolve_presentation_source_config,
    select_slide_asset,
    select_presentation_template,
    slide_specs_to_json,
    speaker_notes_to_json,
    template_manifest,
)
from .rebuttal import (
    RebuttalInputError,
    rebuttal_inputs_markdown,
    resolve_rebuttal_source_config,
)
from .router.intent import RouteDecision, is_approval_message, is_stop_message, route_message
from .state.store import StateStore
from .upstream import generate_image, generate_text


class ResearchAgentService:
    def __init__(self) -> None:
        self.store = StateStore(config.state_root, config.artifact_root)
        self.artifacts = ArtifactStore(config.artifact_root)
        self.wiki = WikiService(config.wiki_root, config.aris_repo_root)
        self.scholar = ScholarSearchService(
            config.scholar_request_timeout_seconds,
            wos_api_base_url=config.wos_api_base_url,
            wos_api_key=config.wos_api_key,
            wos_default_db=config.wos_default_db,
            cnki_search_endpoint=config.cnki_search_endpoint,
            cnki_search_method=config.cnki_search_method,
            cnki_api_key=config.cnki_api_key,
            cnki_auth_header=config.cnki_auth_header,
            cnki_auth_scheme=config.cnki_auth_scheme,
        )
        self.cloud = SeafileWorkspaceSync(
            enabled=config.cloud_sync_enabled,
            base_url=config.seafile_base_url,
            api_token=config.seafile_api_token,
            username=config.seafile_username,
            password=config.seafile_password,
            repo_id=config.seafile_repo_id,
            repo_name=config.seafile_repo_name,
            remote_root=config.seafile_remote_root,
            create_share_links=config.seafile_share_links,
            share_password=config.seafile_share_password,
            timeout_seconds=config.request_timeout_seconds,
        )
        self._cloud_sync_jobs: dict[str, asyncio.Task] = {}
        self._cloud_sync_pending: set[str] = set()
        self.workflows = workflow_registry()
        self.runtime = LangGraphWorkflowRuntime(self, self.workflows)

    async def chat(self, session_id: str | None, message: str, user_id: str | None = None) -> dict:
        session = self.store.get_or_create_session(session_id, user_id or "local")
        workspace_root = self.artifacts.session_root(
            user_id=session.user_id,
            session_id=session.session_id,
        )
        session.workspace_root = str(workspace_root.resolve())
        if config.cloud_sync_enabled and session.cloud_workspace.status != "synced":
            await self.sync_session_workspace(session)
        session.history.append(MessageRecord(role="user", content=message))
        self.store.save_session(session)

        active_task = self.store.load_task(session.active_task_id) if session.active_task_id else None
        if active_task and active_task.status == "waiting_human":
            reply = await self._handle_waiting_task(session, active_task, message)
        else:
            direct_reply = self._direct_chat_response("".join(message.lower().split()))
            if direct_reply is not None:
                reply = await self._chat_reply(session)
            else:
                route = await route_message(message)
                if route is None:
                    reply = await self._chat_reply(session)
                else:
                    reply = await self._start_task(session, message, route)

        latest_session = self.store.load_session(session.session_id) or session
        latest_session.history.append(MessageRecord(role="assistant", content=reply["text"]))
        self.store.save_session(latest_session)
        return {"session_id": latest_session.session_id, **reply}

    async def approve_task(self, task_id: str, feedback: str = "") -> dict:
        task = self.store.load_task(task_id)
        if not task:
            raise ValueError(f"Unknown task: {task_id}")
        session = self.store.load_session(task.session_id)
        if not session:
            raise ValueError(f"Unknown session: {task.session_id}")
        result = await self._resume_after_approval(session, task, approved=True, feedback=feedback)
        latest_session = self.store.load_session(session.session_id) or session
        latest_session.history.append(MessageRecord(role="assistant", content=result["text"]))
        self.store.save_session(latest_session)
        return {"session_id": latest_session.session_id, **result}

    async def reject_task(self, task_id: str, feedback: str) -> dict:
        task = self.store.load_task(task_id)
        if not task:
            raise ValueError(f"Unknown task: {task_id}")
        session = self.store.load_session(task.session_id)
        if not session:
            raise ValueError(f"Unknown session: {task.session_id}")
        result = await self._resume_after_approval(session, task, approved=False, feedback=feedback)
        latest_session = self.store.load_session(session.session_id) or session
        latest_session.history.append(MessageRecord(role="assistant", content=result["text"]))
        self.store.save_session(latest_session)
        return {"session_id": latest_session.session_id, **result}

    async def continue_task(self, task_id: str) -> dict:
        task = self.store.load_task(task_id)
        if not task:
            raise ValueError(f"Unknown task: {task_id}")
        session = self.store.load_session(task.session_id)
        if not session:
            raise ValueError(f"Unknown session: {task.session_id}")
        workflow = self.workflows[task.command]
        result = await self.runtime.continue_task(task, workflow)
        latest_session = self.store.load_session(session.session_id) or session
        latest_session.history.append(MessageRecord(role="assistant", content=result["text"]))
        self.store.save_session(latest_session)
        return {"session_id": latest_session.session_id, **result}

    def mark_task_scheduled(self, task_id: str, action: str) -> TaskRun:
        task = self.store.load_task(task_id)
        if not task:
            raise ValueError(f"Unknown task: {task_id}")
        task.status = "running"
        task.error = ""
        task.summary = "审批已接收，正在后台继续生成。" if action == "approve" else "修改意见已接收，正在后台重新生成。"
        self._log_progress(task, task.summary)
        self.store.save_task(task)
        return task

    def record_task_failure(self, task_id: str, error: BaseException) -> None:
        task = self.store.load_task(task_id)
        if not task:
            return
        if isinstance(error, asyncio.CancelledError):
            task.status = "running"
            task.error = ""
            task.summary = "服务停止时后台任务被中断，将在服务启动后从断点恢复。"
            self._log_progress(task, task.summary)
            self.store.save_task(task)
            return
        detail = str(error).strip() or error.__class__.__name__
        task.status = "failed"
        task.error = detail
        task.summary = f"任务执行失败：{detail}"
        self._log_progress(task, task.summary)
        self.store.save_task(task)
        session = self.store.load_session(task.session_id)
        if session and session.active_task_id == task.task_id:
            session.active_task_id = None
            self.store.save_session(session)

    def get_task(self, task_id: str) -> TaskRun | None:
        return self.store.load_task(task_id)

    def list_tasks(self, session_id: str | None = None) -> list[TaskRun]:
        return self.store.list_tasks(session_id)

    async def _chat_reply(self, session: ChatSession) -> dict:
        latest_message = session.history[-1].content if session.history else ""
        direct_reply = self._direct_chat_response(latest_message)
        if direct_reply:
            return {
                "text": direct_reply,
                "task_id": "",
                "status": "idle",
                "command": "",
                "workflow_title": "",
                "artifact_root": "",
                "artifacts": [],
                "progress": [],
                "checkpoint": None,
            }
        history = session.history[-8:]
        system_prompt = (
            "You are Research Agent Platform, a research workflow assistant rather than a generic AI chatbot. "
            "Reply in Chinese when the user writes Chinese. Keep answers concise, useful, and concrete. "
            "If the user asks who you are, explicitly say you are a 科研智能体 / Research Agent for literature review, "
            "idea discovery, experiment planning, paper drafting, rebuttal, and research memory. Mention commands such as "
            "/review, /idea, /plan, /code, /write, /rebuttal, /fig, /present, and /wiki when relevant. "
            "Do not describe yourself as a generic assistant. Do not create a workflow task unless the user explicitly requests one."
        )
        content = await generate_text(
            system_prompt=system_prompt,
            user_prompt="\n".join(f"{item.role}: {item.content}" for item in history),
            temperature=0.2,
        )
        return {
            "text": content
            or (
                "我是科研智能体 Research Agent，不是通用助手。"
                "我可以处理文献梳理、选题、实验规划、论文写作、审稿回复和研究记忆，也支持 "
                "/review、/idea、/plan、/code、/write、/rebuttal、/fig、/present、/wiki 等工作流。"
            ),
            "task_id": "",
            "status": "idle",
            "command": "",
            "workflow_title": "",
            "artifact_root": "",
            "artifacts": [],
            "progress": [],
            "checkpoint": None,
        }

    def _direct_chat_response(self, message: str) -> str | None:
        normalized = "".join(message.lower().split())
        if self._is_identity_question(normalized):
            return (
                "我是科研智能体 Research Agent，不是通用聊天助手。\n\n"
                "我主要用于文献梳理、选题发现、实验规划、代码实现协同、论文写作、审稿回复和研究记忆管理。\n\n"
                "你可以直接提问，也可以用 /review、/idea、/plan、/code、/write、/rebuttal、/fig、/present、/wiki 启动对应科研流程。"
                "进入多阶段任务后，我会显示路由结果、阶段进度、待审批 checkpoint 和产物文件路径。"
            )
        if self._is_capability_question(normalized):
            return (
                "我更适合科研工作流，不是泛用闲聊机器人。\n\n"
                "常见用法是：/review 做文献调研，/idea 做选题，/plan 做实验方案，/code 做实现与实验执行，"
                "/write 产出论文草稿，/rebuttal 处理审稿意见，/wiki 回看本地研究记忆。"
            )
        return None

    def _is_identity_question(self, normalized_message: str) -> bool:
        if not normalized_message:
            return False
        keywords = (
            "你是谁",
            "你是干什么的",
            "介绍一下你自己",
            "自我介绍",
            "whoareyou",
            "whatareyou",
            "introduceyourself",
        )
        return any(keyword in normalized_message for keyword in keywords)

    def _is_capability_question(self, normalized_message: str) -> bool:
        if not normalized_message:
            return False
        keywords = (
            "你会什么",
            "你能做什么",
            "可以做什么",
            "怎么用你",
            "whatcanyoudo",
            "howtouseyou",
        )
        return any(keyword in normalized_message for keyword in keywords)

    async def _handle_waiting_task(self, session: ChatSession, task: TaskRun, message: str) -> dict:
        if is_stop_message(message):
            task.status = "failed"
            task.error = "Stopped by user during human checkpoint."
            session.active_task_id = None
            self.store.save_task(task)
            return self._build_reply(
                task,
                text=f"任务 `{task.task_id}` 已停止。已有产物保留在 `{task.artifact_root}`。",
            )

        if is_approval_message(message):
            return await self._resume_after_approval(session, task, approved=True, feedback="")

        return await self._resume_after_approval(session, task, approved=False, feedback=message)

    async def _start_task(self, session: ChatSession, message: str, route: RouteDecision) -> dict:
        workflow = self.workflows[route.command]
        task = TaskRun(
            session_id=session.session_id,
            user_id=session.user_id,
            command=workflow.command,
            objective=self._strip_command(message, workflow.command, route.command),
            route_source=route.source,
            workflow_title=workflow.title,
        )
        task_root = self.artifacts.task_root(
            task.task_id,
            user_id=task.user_id,
            session_id=task.session_id,
        )
        task.artifact_root = str(task_root.resolve())
        await self.sync_session_workspace(session, task=task)
        if task.command == "/present":
            task.presentation_source = resolve_presentation_source_config(
                task.objective,
                task_root,
                session.upload_batches,
                source_limit=config.presentation_source_limit,
            )
        if task.command == "/rebuttal":
            try:
                task.rebuttal_source = resolve_rebuttal_source_config(
                    task.objective,
                    task_root,
                    session.upload_batches,
                )
            except RebuttalInputError as exc:
                task.status = "failed"
                task.error = str(exc)
                task.summary = str(exc)
                self._log_progress(task, f"Rebuttal input validation failed: {exc}")
                session.active_task_id = None
                self.store.save_task(task)
                self.store.save_session(session)
                return self._build_reply(task, text=str(exc))
        self._log_progress(task, f"已路由到 {route.command} | 来源: {route.source} | 原因: {route.reason}")
        session.active_task_id = task.task_id
        self.store.save_task(task)
        self.store.save_session(session)
        return await self.runtime.start_task(task, workflow)

    async def _resume_after_approval(
        self, session: ChatSession, task: TaskRun, *, approved: bool, feedback: str
    ) -> dict:
        workflow = self.workflows[task.command]
        if self.runtime.has_graph_state(task.task_id):
            return await self.runtime.resume_task(
                task,
                workflow,
                approved=approved,
                feedback=feedback,
            )

        if not task.approvals:
            raise ValueError(f"Task {task.task_id} has no pending checkpoint.")
        checkpoint = task.approvals[-1]

        if approved:
            checkpoint.status = "approved"
            checkpoint.feedback = feedback
            checkpoint.resolved_at = checkpoint.resolved_at or checkpoint.created_at
            task.status = "running"
            self._log_progress(task, f"已批准 checkpoint: {checkpoint.title}")
            task.current_stage_index = checkpoint.stage_index + 1
            if task.current_stage_index < len(workflow.stage_definitions):
                task.current_stage_name = workflow.stage_definitions[task.current_stage_index].name
            else:
                task.current_stage_name = ""
            self.store.save_task(task)
            return await self._run_task(task, workflow, revision_feedback=feedback)

        checkpoint.status = "rejected"
        checkpoint.feedback = feedback
        checkpoint.resolved_at = checkpoint.resolved_at or checkpoint.created_at
        task.status = "running"
        self._log_progress(task, f"已打回 checkpoint: {checkpoint.title} | 反馈: {feedback}")
        self.store.save_task(task)
        return await self._rerun_checkpoint_stage(task, workflow, feedback)

    async def _rerun_checkpoint_stage(
        self, task: TaskRun, workflow: WorkflowDefinition, feedback: str
    ) -> dict:
        stage_index = task.approvals[-1].stage_index
        stage = workflow.stage_definitions[stage_index]
        self._log_progress(task, f"正在根据反馈重生成阶段: {stage.title}")
        artifact = await self._execute_stage(task, workflow, stage, feedback)
        task.artifacts.append(artifact)
        checkpoint = self._make_checkpoint(task, stage, feedback)
        task.approvals.append(checkpoint)
        task.status = "waiting_human"
        task.current_stage_index = stage_index
        task.current_stage_name = stage.name
        task.summary = f"{stage.title} regenerated with human feedback."
        self._log_progress(task, f"阶段已重生成: {stage.title}")
        self.store.save_task(task)
        await self.sync_task_workspace(task)
        return self._build_reply(
            task,
            text=f"{stage.title} 已根据反馈重生成。请检查更新后的产物，确认后继续，或再次打回。",
            checkpoint=checkpoint,
        )

    async def _run_task(self, task: TaskRun, workflow: WorkflowDefinition, revision_feedback: str) -> dict:
        starting_index = task.current_stage_index
        for stage_index in range(task.current_stage_index, len(workflow.stage_definitions)):
            stage = workflow.stage_definitions[stage_index]
            task.current_stage_index = stage_index
            task.current_stage_name = stage.name
            self._log_progress(task, f"阶段开始: {stage.title}")
            self.store.save_task(task)
            artifact = await self._execute_stage(
                task,
                workflow,
                stage,
                revision_feedback if stage_index == starting_index else "",
            )
            task.artifacts.append(artifact)
            self._log_progress(task, f"阶段完成: {stage.title} -> {artifact.relative_path}")
            await self.sync_task_workspace(task)
            if self._stage_requires_checkpoint(task, stage):
                checkpoint = self._make_checkpoint(task, stage, revision_feedback)
                task.approvals.append(checkpoint)
                task.status = "waiting_human"
                task.summary = f"Waiting for human approval at {stage.title}."
                self._log_progress(task, f"等待人工审批: {checkpoint.title}")
                self.store.save_task(task)
                return self._build_reply(
                    task,
                    text=f"{stage.title} 已完成，正在等待你的审核。你可以批准继续，或填写修改意见后打回本阶段。",
                    checkpoint=checkpoint,
                )

        if task.command == "/idea":
            await self._write_research_contract(task)
        if task.command == "/fig":
            task.artifacts.extend(await self._write_figure_delivery_artifacts(task))
        if task.command == "/write":
            task.artifacts.extend(await self._write_delivery_artifacts(task))
        if task.command == "/present":
            await self._write_presentation_delivery_artifacts(task)
        wiki_note = self.wiki.record_task(task)
        task.notes.append(f"Wiki note: {wiki_note}")
        if workflow.stage_definitions:
            task.current_stage_name = workflow.stage_definitions[-1].name
        task.status = "completed"
        task.summary = f"{workflow.title} completed with {len(task.artifacts)} artifacts."
        self._log_progress(task, f"工作流完成: {workflow.title}")
        self.store.save_task(task)
        await self.sync_task_workspace(task)
        session = self.store.load_session(task.session_id)
        if session:
            session.active_task_id = None
            self.store.save_session(session)
        return self._build_reply(
            task,
            text=f"{workflow.title} 已完成。产物保存在 `{task.artifact_root}`，并已写入本地研究 wiki 记录 `{wiki_note}`。",
        )

    async def _execute_stage(
        self, task: TaskRun, workflow: WorkflowDefinition, stage: StageDefinition, revision_feedback: str
    ):
        support_artifacts, support_context = await self._prepare_stage_support(task, stage)
        for artifact in support_artifacts:
            task.artifacts.append(artifact)
        if task.command == "/rebuttal" and stage.name == "rebuttal_intake":
            if task.rebuttal_source is None:
                raise RebuttalInputError("/rebuttal input SourceSet is missing.")
            content = rebuttal_inputs_markdown(task.rebuttal_source)
            artifact = self._write_text(
                task,
                stage.artifact_path,
                content,
                kind=stage.artifact_kind,
                description=f"{workflow.title} / {stage.title}",
            )
            self.artifacts._write_manifest_for_root(Path(task.artifact_root))
            return artifact
        prompt = self._build_stage_prompt(task, workflow, stage, revision_feedback)
        if support_context:
            prompt["user"] = support_context + "\n" + prompt["user"]
        content = await generate_text(
            system_prompt=prompt["system"],
            user_prompt=prompt["user"],
            temperature=0.35,
        )
        if not content.strip():
            raise RuntimeError(f"Empty content from upstream for stage {stage.name}")
        artifact = self._write_text(
            task,
            stage.artifact_path,
            content,
            kind=stage.artifact_kind,
            description=f"{workflow.title} / {stage.title}",
        )
        self.artifacts._write_manifest_for_root(Path(task.artifact_root))
        return artifact

    def _stage_requires_checkpoint(self, task: TaskRun, stage: StageDefinition) -> bool:
        if not config.enable_hitl or not stage.hitl:
            return False
        objective = task.objective.lower()
        explicit_review = (
            r"(?:先|生成后).{0,8}(?:确认|审核|给我看)",
            r"(?:确认|审核).{0,8}(?:后再|再继续|再生成)",
            r"\b(?:review|approve|approval)\s+(?:first|before continuing)\b",
        )
        if any(re.search(pattern, objective, re.I) for pattern in explicit_review):
            return True
        artifact_path = Path(task.artifact_root) / stage.artifact_path
        if not artifact_path.exists():
            return False
        content = artifact_path.read_text(encoding="utf-8", errors="ignore")
        section = re.search(
            r"(?:^|\n)#{1,6}\s*(?:Decision Required|需要用户决策|待用户选择)\s*\n"
            r"(.*?)(?=\n#{1,6}\s|\Z)",
            content,
            re.I | re.S,
        )
        if not section:
            return False
        decision = section.group(1).strip()
        decision_plain = re.sub(r"[`*_]", "", decision).strip()
        if re.match(r"(?is)^none(?:\s|[.!。]|$)", decision_plain):
            return False
        normalized = re.sub(r"[`*_\s.。:：-]", "", decision).lower()
        if normalized in {"", "none", "no", "n/a", "na", "无", "无需", "不需要"}:
            return False
        choices = re.findall(
            r"(?m)^\s*(?:[-*+]\s+|\d+[.)]\s+|(?:option|方案|选项)\s*[A-Z一二三四五六七八九十\d]+\s*[:：.-])\S+.*$",
            decision,
            re.I,
        )
        named_options = set(
            match.lower()
            for match in re.findall(
                r"(?:option|方案|选项)\s*([A-Z一二三四五六七八九十\d]+)",
                decision,
                re.I,
            )
        )
        return len(choices) >= 2 or len(named_options) >= 2

    async def _prepare_stage_support(self, task: TaskRun, stage: StageDefinition) -> tuple[list, str]:
        support_artifacts: list = []
        support_context_parts: list[str] = []
        if task.command == "/present":
            presentation_artifacts, presentation_context = self._prepare_presentation_support(task)
            support_artifacts.extend(presentation_artifacts)
            if presentation_context:
                support_context_parts.append(presentation_context)
            return support_artifacts, "\n\n".join(support_context_parts)
        if task.command == "/rebuttal":
            rebuttal_artifacts, rebuttal_context = self._prepare_rebuttal_support(task)
            support_artifacts.extend(rebuttal_artifacts)
            if rebuttal_context:
                support_context_parts.append(rebuttal_context)
            return support_artifacts, "\n\n".join(support_context_parts)
        if task.command not in {"/review", "/idea"}:
            return support_artifacts, "\n\n".join(support_context_parts)
        if task.command == "/idea":
            evidence_paths = (
                Path(task.artifact_root) / "bib" / "EVIDENCE_MAP.md",
                Path(task.artifact_root) / "bib" / "LITERATURE_REVIEW.md",
            )
            existing_evidence = next((path for path in evidence_paths if path.exists()), None)
            if existing_evidence:
                support_context_parts.append(self._file_excerpt(str(existing_evidence), 5000))
                return support_artifacts, "\n\n".join(support_context_parts)
        query = self._search_query_for_task(task.objective)
        if not query:
            return support_artifacts, "\n\n".join(support_context_parts)
        md_path = Path(task.artifact_root) / "bib" / "LITERATURE_SEARCH.md"
        json_path = Path(task.artifact_root) / "bib" / "LITERATURE_SEARCH.json"
        if md_path.exists() and json_path.exists():
            support_context_parts.append(self._file_excerpt(str(md_path), 5000))
            return support_artifacts, "\n\n".join(support_context_parts)
        bundle = await self.scholar.search_bundle(query, per_source_limit=config.scholar_results_per_source)
        md_artifact = self._write_text(
            task,
            "bib/LITERATURE_SEARCH.md",
            bundle.to_markdown(),
            kind="note",
            description="Aggregated scholarly search results for the task.",
        )
        json_artifact = self._write_text(
            task,
            "bib/LITERATURE_SEARCH.json",
            bundle.to_json(),
            kind="note",
            description="Structured scholarly search results for the task.",
        )
        support_artifacts.extend([md_artifact, json_artifact])
        support_context_parts.append(bundle.prompt_excerpt())
        return support_artifacts, "\n\n".join(support_context_parts)

    def _prepare_presentation_support(self, task: TaskRun) -> tuple[list, str]:
        workspace_root = Path(task.artifact_root)
        source_config = task.presentation_source or resolve_presentation_source_config(
            task.objective,
            workspace_root,
            source_limit=config.presentation_source_limit,
        )
        if task.presentation_source is None:
            task.presentation_source = source_config
            self.store.save_task(task)
        mode = source_config.presentation_type
        template = select_presentation_template(task.objective, mode, config.presentation_template)
        evidence = collect_workspace_evidence(
            workspace_root,
            mode,
            source_refs=source_config.source_refs,
        )
        selection_path = workspace_root / "Content" / "PRESENTATION_SOURCE_SELECTION.json"
        previous_selection: dict = {}
        if selection_path.exists():
            try:
                previous_selection = json.loads(selection_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                previous_selection = {}
        assets_path = workspace_root / "Content" / "PRESENTATION_ASSETS.json"
        if assets_path.exists() and previous_selection.get("task_id") == task.task_id:
            assets = presentation_assets_from_json(assets_path.read_text(encoding="utf-8"))
        else:
            assets = extract_presentation_assets(
                workspace_root,
                source_config.source_refs,
                f"figures/extracted/presentation/{task.task_id}",
            )
        source_index_path = workspace_root / "Content" / "PRESENTATION_SOURCE_INDEX.md"
        source_index = (
            "# Presentation Source Index\n\n"
            f"- Mode: `{mode}`\n"
            f"- Template: `{template.name}`\n"
            f"- Requested scope: `{source_config.requested_scope}`\n"
            f"- Resolved scope: `{source_config.resolved_scope}`\n"
            f"- Upload batch: `{source_config.upload_batch_id or 'none'}`\n"
            f"- Selection reason: {source_config.selection_reason}\n"
            f"- Files selected: {len(evidence.files)}\n"
            f"- Original assets extracted: {len(assets)}\n\n"
            "## Selected Source Files\n"
            + ("\n".join(f"- `{path}`" for path in evidence.files) or "- None")
            + "\n"
        )
        source_selection = {
            "task_id": task.task_id,
            **source_config.model_dump(),
            "selected_files": list(evidence.files),
            "asset_count": len(assets),
        }
        artifacts: list = []
        if not source_index_path.exists() or source_index_path.read_text(encoding="utf-8", errors="ignore") != source_index:
            artifacts.append(
                self._write_text(
                    task,
                    "Content/PRESENTATION_SOURCE_INDEX.md",
                    source_index,
                    kind="note",
                    description="Workspace evidence index used by the presentation workflow.",
                )
            )
        selection_json = json.dumps(source_selection, ensure_ascii=False, indent=2)
        if not selection_path.exists() or selection_path.read_text(encoding="utf-8", errors="ignore") != selection_json:
            artifacts.append(
                self._write_text(
                    task,
                    "Content/PRESENTATION_SOURCE_SELECTION.json",
                    selection_json,
                    kind="note",
                    description="Frozen source boundary for the presentation workflow.",
                )
            )
        assets_json = presentation_assets_to_json(assets)
        if not assets_path.exists() or assets_path.read_text(encoding="utf-8", errors="ignore") != assets_json:
            artifacts.append(
                self._write_text(
                    task,
                    "Content/PRESENTATION_ASSETS.json",
                    assets_json,
                    kind="note",
                    description="Original image and table assets extracted from the frozen SourceSet.",
                )
            )
        asset_context = "\n".join(
            f"- {asset.asset_id} | {asset.kind} | {asset.source_path}"
            + (f" | page {asset.page}" if asset.page else "")
            + (f" | {asset.caption}" if asset.caption else "")
            for asset in assets[:80]
        )
        context = (
            "Presentation requirements:\n"
            f"- Detected mode: {mode}\n"
            f"- Selected template: {template.name}\n"
            f"- Frozen source scope: {source_config.resolved_scope}\n"
            f"- Selection reason: {source_config.selection_reason}\n"
            "- Use only the evidence below for claims and numbers.\n"
            "- Prefer matching original image/table asset_ids over regenerated data visuals.\n"
            "- Stage mode prioritizes plan, progress, results, risks, decisions, and next steps.\n"
            "- Paper mode treats final artifacts in paper/ as authoritative and follows a complete paper-talk arc.\n\n"
            f"Available original assets:\n{asset_context or '- None'}\n\n"
            f"Selected evidence:\n{evidence.text or 'No readable selected evidence found; rely only on the user objective.'}"
        )
        return artifacts, context

    def _prepare_rebuttal_support(self, task: TaskRun) -> tuple[list, str]:
        workspace_root = Path(task.artifact_root)
        source_config = task.rebuttal_source
        if source_config is None:
            session = self.store.load_session(task.session_id)
            source_config = resolve_rebuttal_source_config(
                task.objective,
                workspace_root,
                session.upload_batches if session else (),
            )
            task.rebuttal_source = source_config
            self.store.save_task(task)

        paper_evidence = collect_workspace_evidence(
            workspace_root,
            "paper",
            limit=18000,
            source_refs=source_config.paper_refs,
        )
        review_evidence = collect_workspace_evidence(
            workspace_root,
            "stage",
            limit=18000,
            source_refs=source_config.review_refs,
        )
        selection = {
            "task_id": task.task_id,
            **source_config.model_dump(),
            "paper_files_read": list(paper_evidence.files),
            "review_files_read": list(review_evidence.files),
        }
        selection_json = json.dumps(selection, ensure_ascii=False, indent=2)
        selection_path = workspace_root / "Content" / "REBUTTAL_SOURCE_SELECTION.json"
        artifacts: list = []
        if (
            not selection_path.exists()
            or selection_path.read_text(encoding="utf-8", errors="ignore") != selection_json
        ):
            artifacts.append(
                self._write_text(
                    task,
                    "Content/REBUTTAL_SOURCE_SELECTION.json",
                    selection_json,
                    kind="note",
                    description="Frozen completed-paper and reviewer-comment sources for /rebuttal.",
                )
            )

        context = (
            "Rebuttal SourceSet contract:\n"
            "- The completed paper and reviewer comments below are both required and have been frozen for this task.\n"
            "- Analyze reviewer comments against the actual paper. Do not answer from the task objective alone.\n"
            "- Preserve reviewer-by-reviewer and comment-by-comment traceability.\n"
            "- Every proposed response must point to a paper section, claim, figure, table, evidence item, or an explicit gap.\n"
            "- Distinguish current paper text, proposed response language, promised revision, and new experiment needs.\n\n"
            "Completed paper sources:\n"
            + "\n".join(f"- `{path}`" for path in source_config.paper_refs)
            + "\n\nCompleted paper content:\n"
            + (paper_evidence.text or "No readable paper text could be extracted from the frozen files.")
            + "\n\nReviewer-comment sources:\n"
            + "\n".join(f"- `{path}`" for path in source_config.review_refs)
            + "\n\nReviewer comments:\n"
            + (review_evidence.text or "No readable reviewer text could be extracted from the frozen files.")
        )
        return artifacts, context

    async def _write_research_contract(self, task: TaskRun) -> None:
        template_path = Path(config.aris_repo_root) / "templates" / "RESEARCH_CONTRACT_TEMPLATE.md"
        template = template_path.read_text(encoding="utf-8") if template_path.exists() else "# Research Contract"
        candidates = self._artifact_excerpt(task, "idea/IDEA_CANDIDATES.md")
        verification = self._artifact_excerpt(task, "idea/IDEA_VERIFICATION.md")
        final_idea = self._artifact_excerpt(task, "idea/FINAL_IDEA.md")
        user_prompt = (
            "Using the template and the idea artifacts below, fill a focused research contract for handoff to /plan. "
            "Do not invent an experiment plan; preserve unresolved evidence and planning needs.\n"
            "Return markdown only.\n\n"
            f"Template:\n{template}\n\n"
            f"IDEA_CANDIDATES excerpt:\n{candidates}\n\n"
            f"IDEA_VERIFICATION excerpt:\n{verification}\n\n"
            f"FINAL_IDEA excerpt:\n{final_idea}\n"
        )
        content = await generate_text(
            system_prompt="You create focused research contracts for continuation and session recovery.",
            user_prompt=user_prompt,
            temperature=0.2,
        )
        artifact = self._write_text(
            task,
            "idea/docs/research_contract.md",
            content,
            kind="contract",
            description="Focused research contract for the selected idea.",
        )
        task.artifacts.append(artifact)
        self.store.save_task(task)

    async def _write_figure_delivery_artifacts(self, task: TaskRun) -> list:
        briefs = self._artifact_text(task, "figures/FIGURE_BRIEFS.md")
        inventory = self._artifact_excerpt(task, "figures/FIGURE_INVENTORY.md")
        if not briefs and not inventory:
            return []

        prompt = await self._build_figure_render_prompt(task, inventory, briefs)
        prompt_artifact = self._write_text(
            task,
            "figures/generated/FIGURE_RENDER_PROMPT.md",
            prompt,
            kind="note",
            description="Render prompt used for gpt-image-2 figure generation.",
        )
        self._log_progress(task, f"开始调用 {config.image_model} 生成图像")
        size = self._select_figure_image_size(task.objective, briefs)
        image = await generate_image(
            prompt=prompt,
            model=config.image_model,
            size=size,
            quality="low",
            output_format="png",
        )
        image_artifact = self._write_bytes(
            task,
            "figures/generated/FIGURE_01.png",
            image.image_bytes,
            kind="image",
            description=f"Primary generated research figure via {image.model}.",
        )
        metadata = {
            "model": image.model,
            "size": image.size,
            "quality": image.quality,
            "output_format": image.output_format,
            "mime_type": image.mime_type,
            "revised_prompt": image.revised_prompt,
        }
        metadata_artifact = self._write_text(
            task,
            "figures/generated/FIGURE_01_METADATA.json",
            json.dumps(metadata, ensure_ascii=False, indent=2),
            kind="note",
            description="Metadata for the generated figure artifact.",
        )
        self._log_progress(task, f"图像已生成: {image_artifact.relative_path}")
        self.store.save_task(task)
        return [prompt_artifact, image_artifact, metadata_artifact]

    async def _write_presentation_delivery_artifacts(self, task: TaskRun) -> list:
        content = self._artifact_text(task, "presentation/SLIDE_CONTENT.md")
        content_slides = parse_slide_content(content, max_slides=config.presentation_max_slides)
        outline = self._artifact_text(task, "presentation/SLIDES_OUTLINE.md")
        outline_slides = parse_slide_content(outline, max_slides=config.presentation_max_slides)
        slides = reconcile_slide_specs(
            content_slides,
            outline_slides,
            max_slides=config.presentation_max_slides,
        )
        slides = enforce_presentation_page_mix(slides)
        if not slides:
            raise RuntimeError("SLIDE_CONTENT.md does not contain any parseable 'Slide N: Title' sections.")

        workspace_root = Path(task.artifact_root)
        source_config = task.presentation_source or resolve_presentation_source_config(
            task.objective,
            workspace_root,
            source_limit=config.presentation_source_limit,
        )
        mode = source_config.presentation_type
        template = select_presentation_template(task.objective, mode, config.presentation_template)
        assets_path = workspace_root / "Content" / "PRESENTATION_ASSETS.json"
        assets = (
            presentation_assets_from_json(assets_path.read_text(encoding="utf-8"))
            if assets_path.exists()
            else extract_presentation_assets(
                workspace_root,
                source_config.source_refs,
                f"figures/extracted/presentation/{task.task_id}",
            )
        )
        artifacts: list = []
        task.current_stage_name = "presentation_delivery"
        self._log_progress(task, "阶段开始: PPT 页面生成与组装")
        template_artifact = self._write_text(
            task,
            "Content/PRESENTATION_TEMPLATE.json",
            json.dumps(template_manifest(template, mode), ensure_ascii=False, indent=2),
            kind="note",
            description="Selected presentation mode and Image-2 visual template.",
        )
        artifacts.append(template_artifact)
        task.artifacts.append(template_artifact)
        design_spec_artifact = self._write_text(
            task,
            "Content/PRESENTATION_DESIGN_SPEC.json",
            presentation_design_spec_to_json(slides),
            kind="note",
            description="Final page-level presentation render contract.",
        )
        artifacts.append(design_spec_artifact)
        task.artifacts.append(design_spec_artifact)
        self.store.save_task(task)

        renders: list[SlideRender] = []
        used_asset_ids: set[str] = set()
        for slide in slides:
            asset = select_slide_asset(slide, assets, used_asset_ids)
            if not slide.render_mode_explicit:
                if asset is not None:
                    slide = replace(
                        slide,
                        page_type="evidence",
                        render_mode="evidence",
                    )
                elif slide.render_mode == "evidence":
                    slide = replace(
                        slide,
                        page_type="narrative",
                        render_mode="image2_full",
                    )
            if slide.render_mode == "evidence" and asset is None:
                raise RuntimeError(
                    f"Slide {slide.number} is planned as an evidence page but has no valid Asset ID. "
                    "Fix SLIDE_CONTENT.md instead of asking Image-2 to recreate the evidence."
                )
            if asset:
                used_asset_ids.add(asset.asset_id)
            preview_relative_path = f"presentation/slides/SLIDE_{slide.number:02d}.png"
            preview_path = workspace_root / preview_relative_path
            generated_path: Path | None = None
            image_metadata = {
                "model": "",
                "size": "",
                "quality": "",
                "revised_prompt": "",
            }
            if slide.render_mode == "image2_full":
                generated_relative_path = f"presentation/generated/SLIDE_{slide.number:02d}.png"
                generated_path = workspace_root / generated_relative_path
                prompt = build_slide_prompt(slide, template, mode)
                prompt_artifact = self._write_text(
                    task,
                    f"Content/presentation-prompts/SLIDE_{slide.number:02d}_PROMPT.md",
                    prompt,
                    kind="note",
                    description=f"Image-2 full-page render prompt for slide {slide.number}.",
                )
                artifacts.append(prompt_artifact)
                task.artifacts.append(prompt_artifact)
                same_task_page = any(
                    artifact.relative_path == generated_relative_path for artifact in task.artifacts
                )
                if same_task_page and generated_path.exists() and generated_path.stat().st_size > 0:
                    self._log_progress(task, f"复用已生成的完整页面: {generated_relative_path}")
                else:
                    self._log_progress(
                        task,
                        f"开始调用 {config.image_model} 生成完整PPT页面 {slide.number}/{len(slides)}",
                    )
                    self.store.save_task(task)
                    image = await generate_image(
                        prompt=prompt,
                        model="gpt-image-2",
                        size="1536x1024",
                        quality="medium",
                        output_format="png",
                    )
                    generated_artifact = self._write_bytes(
                        task,
                        generated_relative_path,
                        crop_slide_image(image.image_bytes),
                        kind="image",
                        description=f"Complete standalone Image-2 slide {slide.number}.",
                    )
                    artifacts.append(generated_artifact)
                    task.artifacts.append(generated_artifact)
                    generated_path = Path(generated_artifact.absolute_path)
                    image_metadata = {
                        "model": image.model,
                        "size": image.size,
                        "quality": image.quality,
                        "revised_prompt": image.revised_prompt,
                    }
            else:
                self._log_progress(
                    task,
                    f"使用原始资产排版独立证据页 {slide.number}/{len(slides)}: {asset.asset_id}",
                )
            preview_bytes = compose_slide_preview(
                generated_path,
                slide,
                preview_path,
                workspace_root,
                asset,
            )
            preview_artifact = self._write_bytes(
                task,
                preview_relative_path,
                preview_bytes,
                kind="image",
                description=f"Final preview for standalone slide {slide.number}.",
            )
            artifacts.append(preview_artifact)
            task.artifacts.append(preview_artifact)
            preview_path = Path(preview_artifact.absolute_path)
            metadata = {
                "slide": slide.number,
                "title": slide.title,
                "page_type": slide.page_type,
                "render_mode": slide.render_mode,
                "layout_hint": slide.layout_hint,
                **image_metadata,
                "source_files": list(slide.source_files),
                "asset_id": asset.asset_id if asset else "",
                "asset_kind": asset.kind if asset else "",
                "asset_source": asset.source_path if asset else "",
                "asset_page": asset.page if asset else None,
                "render_policy": (
                    "standalone-original-evidence-page"
                    if slide.render_mode == "evidence"
                    else "standalone-image2-page"
                ),
            }
            metadata_artifact = self._write_text(
                task,
                f"Content/presentation-prompts/SLIDE_{slide.number:02d}_METADATA.json",
                json.dumps(metadata, ensure_ascii=False, indent=2),
                kind="note",
                description=f"Traceability metadata for slide {slide.number}.",
            )
            artifacts.append(metadata_artifact)
            task.artifacts.append(metadata_artifact)
            renders.append(
                SlideRender(
                    slide=slide,
                    base_image=generated_path,
                    preview_image=preview_path,
                    asset=asset,
                )
            )
            self._log_progress(task, f"幻灯片已完成: {preview_relative_path}")
            self.store.save_task(task)

        specs_artifact = self._write_text(
            task,
            "Content/SLIDE_SPECS.json",
            slide_specs_to_json(renders),
            kind="note",
            description="Structured slide specifications and source-asset traceability.",
        )
        artifacts.append(specs_artifact)
        task.artifacts.append(specs_artifact)
        speaker_notes = parse_speaker_notes(
            self._artifact_text(task, "presentation/SPEAKER_NOTES.md"),
            (render.slide for render in renders),
        )
        notes_artifact = self._write_text(
            task,
            "Content/SPEAKER_NOTES.json",
            speaker_notes_to_json(speaker_notes),
            kind="note",
            description="Structured per-slide speaker notes embedded in the final PowerPoint.",
        )
        artifacts.append(notes_artifact)
        task.artifacts.append(notes_artifact)
        filename = "PAPER_TALK.pptx" if mode == "paper" else "STAGE_REPORT.pptx"
        deck = assemble_mixed_deck(
            renders,
            title=self._detect_title(content) or task.objective,
            speaker_notes=speaker_notes,
        )
        deck_artifact = self._write_bytes(
            task,
            f"presentation/{filename}",
            deck,
            kind="presentation",
            description=(
                f"Final {mode} presentation with standalone Image-2 pages, separate original-evidence pages, "
                "and native per-slide speaker notes."
            ),
        )
        artifacts.append(deck_artifact)
        task.artifacts.append(deck_artifact)
        self._log_progress(task, f"PPT 已组装: presentation/{filename}")
        self.store.save_task(task)
        return artifacts

    def _image_mime_type(self, path: Path) -> str:
        return {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }.get(path.suffix.lower(), "image/png")

    def _make_checkpoint(self, task: TaskRun, stage: StageDefinition, feedback: str) -> ApprovalCheckpoint:
        artifact = task.artifacts[-1] if task.artifacts else None
        prompt_lines = [
            f"Checkpoint: {stage.checkpoint_title or stage.title}",
            f"Task: {task.task_id}",
            f"Objective: {task.objective}",
        ]
        if artifact:
            prompt_lines.append(f"Review artifact: {artifact.absolute_path}")
        if feedback:
            prompt_lines.append(f"Latest feedback applied: {feedback}")
        prompt_lines.append("Approve to continue, or send revision feedback.")
        checkpoint = ApprovalCheckpoint(
            stage_name=stage.name,
            stage_index=task.current_stage_index,
            title=stage.checkpoint_title or stage.title,
            prompt="\n".join(prompt_lines),
        )
        checkpoint_artifact = self._write_text(
            task,
            f"Content/{stage.name}_checkpoint.md",
            checkpoint.prompt,
            kind="checkpoint",
            description=f"Human checkpoint for {stage.title}.",
        )
        task.artifacts.append(checkpoint_artifact)
        return checkpoint

    def _build_reply(
        self, task: TaskRun, *, text: str, checkpoint: ApprovalCheckpoint | None = None
    ) -> dict:
        latest_artifacts = [artifact.model_dump() for artifact in task.artifacts[-6:]]
        session = self.store.load_session(task.session_id)
        return {
            "text": text,
            "task_id": task.task_id,
            "status": task.status,
            "command": task.command,
            "workflow_title": task.workflow_title,
            "artifact_root": task.artifact_root,
            "artifacts": latest_artifacts,
            "progress": task.progress_log[-10:],
            "checkpoint": checkpoint.model_dump() if checkpoint else None,
            "cloud_workspace": session.cloud_workspace.model_dump() if session else {},
        }

    async def sync_session_workspace(
        self,
        session: ChatSession,
        *,
        task: TaskRun | None = None,
    ) -> CloudWorkspaceState:
        workspace_value = session.workspace_root or (task.artifact_root if task else "")
        if workspace_value:
            workspace_root = Path(workspace_value)
        else:
            workspace_root = self.artifacts.session_root(
                user_id=session.user_id,
                session_id=session.session_id,
            )
            session.workspace_root = str(workspace_root.resolve())
        result = await self.cloud.sync_workspace(
            workspace_root,
            user_id=session.user_id,
            session_id=session.session_id,
        )
        session.cloud_workspace = CloudWorkspaceState(
            provider="seafile",
            status=result.status,
            remote_path=result.remote_path,
            share_url=result.share_url,
            preview_url=result.preview_url,
            download_url=result.download_url,
            repo_id=result.repo_id,
            synced_files=result.synced_files,
            uploaded_files=result.uploaded_files,
            last_synced_at=utc_now() if result.status == "synced" else "",
            error=result.error,
        )
        self.store.save_session(session)
        if task:
            if result.status == "synced":
                self._log_progress(
                    task,
                    f"Cloud workspace synced: {result.uploaded_files} updated files -> {result.remote_path}",
                )
            elif result.status == "error":
                self._log_progress(task, f"Cloud sync warning: {result.error}")
            self.store.save_task(task)
        return session.cloud_workspace

    async def sync_task_workspace(self, task: TaskRun) -> CloudWorkspaceState:
        session = self.store.load_session(task.session_id)
        if session is None:
            return CloudWorkspaceState(
                status="error",
                error=f"Unknown session: {task.session_id}",
            )
        return await self.sync_session_workspace(session, task=task)

    def _log_progress(self, task: TaskRun, message: str) -> None:
        task.progress_log.append(message)

    def _write_text(self, task: TaskRun, relative_path: str, content: str, *, kind, description: str):
        artifact = self.artifacts.write_text(
            task.task_id,
            self._canonical_artifact_path(relative_path),
            content,
            kind=kind,
            description=description,
            task_root=task.artifact_root,
        )
        self._schedule_cloud_sync(task.session_id)
        return artifact

    def _write_bytes(self, task: TaskRun, relative_path: str, content: bytes, *, kind, description: str):
        artifact = self.artifacts.write_bytes(
            task.task_id,
            self._canonical_artifact_path(relative_path),
            content,
            kind=kind,
            description=description,
            task_root=task.artifact_root,
        )
        self._schedule_cloud_sync(task.session_id)
        return artifact

    def _schedule_cloud_sync(self, session_id: str) -> None:
        if not config.cloud_sync_enabled:
            return
        active = self._cloud_sync_jobs.get(session_id)
        if active and not active.done():
            self._cloud_sync_pending.add(session_id)
            return

        async def run_sync() -> None:
            try:
                while True:
                    self._cloud_sync_pending.discard(session_id)
                    session = self.store.load_session(session_id)
                    if session:
                        await self.sync_session_workspace(session)
                    if session_id not in self._cloud_sync_pending:
                        break
            finally:
                self._cloud_sync_jobs.pop(session_id, None)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        self._cloud_sync_jobs[session_id] = loop.create_task(run_sync())

    def _canonical_artifact_path(self, relative_path: str) -> str:
        normalized = relative_path.replace("\\", "/")
        replacements = {
            "plan-stage/": "plan/",
            "idea-stage/": "idea/",
            "refine-logs/": "plan/",
            "code-stage/": "code/",
            "fig-stage/": "figures/",
            "review-stage/": "bib/",
            "present/": "presentation/",
            "wiki-stage/": "wiki/",
            "hitl/": "Content/",
            "utils/": "Content/",
        }
        for old, new in replacements.items():
            if normalized.startswith(old):
                return new + normalized[len(old) :]
        return normalized

    def _build_stage_prompt(
        self, task: TaskRun, workflow: WorkflowDefinition, stage: StageDefinition, revision_feedback: str
    ) -> dict[str, str]:
        skill_context = self._skill_context(stage.skill_paths)
        prd_context = self._file_excerpt(config.prd_path, 5000)
        tech_context = self._file_excerpt(config.tech_spec_path, 5000)
        session_context = self._session_task_context(task)
        prior_artifacts = "\n\n".join(
            f"### {artifact.relative_path}\n{self._artifact_excerpt(task, artifact.relative_path)}"
            for artifact in task.artifacts[-4:]
        )
        write_output_hint = ""
        if task.command == "/write":
            write_output_hint = (
                "Requested delivery formats: "
                + ", ".join(detect_write_formats(task.objective))
                + ". Structure the draft so it can be exported cleanly.\n\n"
            )
        checkpoint_hint = ""
        if stage.hitl:
            checkpoint_hint = (
                "Checkpoint policy: do not request routine approval. Include a 'Decision Required' section. "
                "Write 'None' when the recommended path is clear. List at least two concrete, mutually exclusive options "
                "only when the user must choose before work can continue.\n\n"
            )
        user_prompt = (
            f"Workflow: {workflow.title}\n"
            f"Command: {task.command}\n"
            f"Objective: {task.objective}\n"
            f"Current stage: {stage.title}\n"
            f"Route source: {task.route_source}\n\n"
            + (
                "Applied ARIS skills:\n"
                + "\n".join(f"- {name}" for name in self._skill_names(stage.skill_paths))
                + "\n\n"
                if stage.skill_paths
                else ""
            )
            + write_output_hint
            + checkpoint_hint
            + f"Stage instruction:\n{stage.instruction}\n\n"
            + "Required sections:\n"
            + "\n".join(f"- {section}" for section in stage.required_sections)
            + "\n\n"
            + (f"Relevant prior session context:\n{session_context}\n\n" if session_context else "")
            + (f"Revision feedback to incorporate:\n{revision_feedback}\n\n" if revision_feedback else "")
            + (f"Recent artifacts:\n{prior_artifacts}\n\n" if prior_artifacts else "")
            + "Return only the markdown for the artifact file. Keep it concrete, honest, and execution-oriented."
        )
        system_prompt = (
            "You are the orchestration core of a research agent platform. "
            "You must follow the PRD and tech-spec constraints, use the ARIS skill patterns as execution guidance, "
            "and produce file-ready markdown artifacts. Separate assumptions from grounded facts, use human checkpoints only for genuine user decisions, "
            "and optimize for local collaboration with a human researcher. "
            "All work belongs to one <user_id>/<session_id>/ workspace and must stay under bib/, plan/, idea/, code/, "
            "figures/, paper/, presentation/, rebuttal/, wiki/, Content/, or logs/. Content/ is reserved for context, "
            "progress records, checkpoints, prompts, traceability metadata, and manifests.\n\n"
            f"PRD excerpt:\n{prd_context}\n\n"
            f"Tech spec excerpt:\n{tech_context}\n\n"
            f"Relevant ARIS guidance:\n{skill_context}\n"
        )
        return {"system": system_prompt, "user": user_prompt}

    async def _build_figure_render_prompt(self, task: TaskRun, inventory: str, briefs: str) -> str:
        system_prompt = (
            "You convert research figure plans into a single production-ready gpt-image-2 prompt. "
            "Return plain prompt text only, no markdown, no bullets. "
            "Prefer clean academic diagrams, short English labels, high readability, white background, and publication-friendly layout."
        )
        user_prompt = (
            f"Objective:\n{task.objective}\n\n"
            f"Figure inventory:\n{inventory}\n\n"
            f"Figure briefs:\n{briefs[:6000]}\n\n"
            "Choose the single highest-value figure to render first. "
            "Describe composition, visual hierarchy, color palette, labels, arrows, panel structure, and style constraints clearly enough for image generation."
        )
        content = await generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
        )
        prompt = content.strip().strip("`")
        if prompt:
            return prompt
        fallback = (
            f"Create a clean academic research figure for: {task.objective}. "
            "Use a white background, blue and slate accents, clear panel layout, thin arrows, short English labels, and publication-ready typography. "
            "Make it look like a polished systems or workflow diagram rather than marketing art."
        )
        return fallback

    def _session_task_context(self, task: TaskRun) -> str:
        prior_tasks = [item for item in self.store.list_tasks(task.session_id) if item.task_id != task.task_id]
        blocks: list[str] = []
        total_chars = 0
        for prior in prior_tasks[:3]:
            lines = [
                f"## Prior Task {prior.task_id}",
                f"Command: {prior.command}",
                f"Objective: {prior.objective}",
                f"Status: {prior.status}",
            ]
            if prior.summary:
                lines.append(f"Summary: {prior.summary}")
            artifacts = sorted(
                prior.artifacts,
                key=lambda artifact: self._handoff_artifact_priority(task.command, artifact.relative_path),
            )
            included = 0
            for artifact in artifacts:
                if artifact.kind in {"checkpoint", "manifest"}:
                    continue
                excerpt = self._artifact_excerpt(prior, artifact.relative_path)
                if not excerpt:
                    continue
                lines.append(f"### {artifact.relative_path}")
                lines.append(excerpt[:1600])
                included += 1
                if included >= 3:
                    break
            block = "\n".join(lines)
            total_chars += len(block)
            if total_chars > 7000:
                break
            blocks.append(block)
        return "\n\n".join(blocks)

    def _handoff_artifact_priority(self, command: str, relative_path: str) -> tuple[int, str]:
        preferred = {
            "/idea": (
                "bib/RESEARCH_GAPS.md",
                "bib/EVIDENCE_MAP.md",
                "bib/LITERATURE_REVIEW.md",
            ),
            "/plan": (
                "idea/FINAL_IDEA.md",
                "idea/docs/research_contract.md",
                "bib/EVIDENCE_MAP.md",
                "bib/RESEARCH_GAPS.md",
            ),
            "/code": (
                "plan/EXECUTION_CHECKLIST.md",
                "plan/EXPERIMENT_PLAN.md",
                "plan/RESEARCH_BLUEPRINT.md",
            ),
        }.get(command, ())
        try:
            return preferred.index(relative_path), relative_path
        except ValueError:
            return len(preferred) + 1, relative_path

    async def _write_delivery_artifacts(self, task: TaskRun) -> list:
        draft = self._artifact_text(task, "paper/PAPER_DRAFT.md")
        if not draft:
            return []
        formats = detect_write_formats(task.objective)
        artifacts = []
        title = self._detect_title(draft) or "Research Draft"
        if "tex" in formats:
            tex = markdown_to_latex(draft, title=title)
            artifacts.append(
                self._write_text(
                    task,
                    "paper/PAPER_DRAFT.tex",
                    tex,
                    kind="document",
                    description="LaTeX export generated from the paper draft.",
                )
            )
        if "docx" in formats:
            docx_bytes = markdown_to_docx_bytes(draft)
            artifacts.append(
                self._write_bytes(
                    task,
                    "paper/PAPER_DRAFT.docx",
                    docx_bytes,
                    kind="document",
                    description="Word export generated from the paper draft.",
                )
            )
        if "pdf" in formats:
            pdf_bytes = markdown_to_pdf_bytes(draft)
            artifacts.append(
                self._write_bytes(
                    task,
                    "paper/PAPER_DRAFT.pdf",
                    pdf_bytes,
                    kind="document",
                    description="PDF export generated from the paper draft.",
                )
            )
        artifacts.extend(await self._compile_paper_draft(task, draft))
        return artifacts

    async def _compile_paper_draft(self, task: TaskRun, draft: str) -> list:
        tex = markdown_to_latex(draft, title=self._detect_title(draft) or "Research Draft")
        build_dir = Path(task.artifact_root) / "paper" / ".compile"
        build_dir.mkdir(parents=True, exist_ok=True)
        source = build_dir / "PAPER_DRAFT.tex"
        source.write_text(tex, encoding="utf-8")
        compiler = self._resolve_tex_compiler()
        if not compiler:
            return [
                self._write_text(
                    task,
                    "paper/PAPER_COMPILE_STATUS.md",
                    "# Paper Compile Status\n\n- Status: failed\n- Reason: LaTeX compiler not available.\n",
                    kind="note",
                    description="Paper compile status report.",
                )
            ]
        outputs: list = []
        try:
            command = [
                compiler,
                "-interaction=nonstopmode",
                "-halt-on-error",
                "-output-directory",
                str(build_dir),
                str(source),
            ]
            first = subprocess.run(command, check=False, capture_output=True, text=True, timeout=240)
            second = subprocess.run(command, check=False, capture_output=True, text=True, timeout=240)
            log_text = "\n\n".join(
                [
                    "## First pass stdout",
                    first.stdout or "",
                    "## First pass stderr",
                    first.stderr or "",
                    "## Second pass stdout",
                    second.stdout or "",
                    "## Second pass stderr",
                    second.stderr or "",
                ]
            )
            outputs.append(
                self._write_text(
                    task,
                    "paper/PAPER_COMPILE_LOG.txt",
                    log_text,
                    kind="note",
                    description="LaTeX compilation log for the paper draft.",
                )
            )
            pdf_path = build_dir / "PAPER_DRAFT.pdf"
            if pdf_path.exists():
                outputs.append(
                    self._write_bytes(
                        task,
                        "paper/PAPER_DRAFT_COMPILED.pdf",
                        pdf_path.read_bytes(),
                        kind="document",
                        description=f"Compiled PDF generated via {Path(compiler).name}.",
                    )
                )
                outputs.append(
                    self._write_text(
                        task,
                        "paper/PAPER_COMPILE_STATUS.md",
                        "# Paper Compile Status\n\n- Status: success\n- Compiler: "
                        + Path(compiler).name
                        + "\n- Output: `paper/PAPER_DRAFT_COMPILED.pdf`\n",
                        kind="note",
                        description="Paper compile status report.",
                    )
                )
            else:
                outputs.append(
                    self._write_text(
                        task,
                        "paper/PAPER_COMPILE_STATUS.md",
                        "# Paper Compile Status\n\n- Status: failed\n- Reason: PDF not produced.\n",
                        kind="note",
                        description="Paper compile status report.",
                    )
                )
        except Exception as exc:
            outputs.append(
                self._write_text(
                    task,
                    "paper/PAPER_COMPILE_STATUS.md",
                    f"# Paper Compile Status\n\n- Status: failed\n- Reason: {exc.__class__.__name__}: {exc}\n",
                    kind="note",
                    description="Paper compile status report.",
                )
            )
        return outputs

    def _detect_title(self, markdown: str) -> str:
        lines = markdown.splitlines()
        for index, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()
            if stripped.lower() == "# title" and index + 2 < len(lines):
                candidate = lines[index + 2].strip("* ").strip()
                if candidate:
                    return candidate
        return ""

    def _skill_context(self, skill_paths: list[str]) -> str:
        contexts: list[str] = []
        aris_root = Path(config.aris_repo_root)
        total_chars = 0
        total_limit = 18000
        for relative in skill_paths:
            target = self._resolve_skill_path(aris_root, relative)
            if not target.exists():
                contexts.append(f"## {relative}\nMissing skill file.")
                continue
            excerpt = self._skill_excerpt(target, limit=2200)
            if not excerpt:
                continue
            block = f"## {relative}\n{excerpt}"
            total_chars += len(block)
            if total_chars > total_limit and contexts:
                contexts.append("## skill-budget\nAdditional ARIS skills were omitted after the prompt budget cap.")
                break
            contexts.append(block)
        return "\n\n".join(contexts) or "No skill context found."

    def _skill_names(self, skill_paths: list[str]) -> list[str]:
        names: list[str] = []
        for relative in skill_paths:
            names.append(Path(relative).parent.name)
        return names

    def _scholar_skill_names(self) -> set[str]:
        return {
            "research-lit",
            "prior-art-search",
            "openalex",
            "semantic-scholar",
            "arxiv",
            "deepxiv",
            "comm-lit-review",
            "novelty-check",
            "idea-discovery",
            "idea-creator",
            "idea-discovery-robot",
            "research-pipeline",
            "research-refine",
            "research-refine-pipeline",
            "paper-plan",
            "paper-writing",
            "paper-write",
            "claims-drafting",
            "research-review",
            "research-wiki",
            "wiki-enrich",
            "result-to-claim",
        }

    def _search_query_for_task(self, objective: str) -> str:
        cleaned = re.sub(r"^\s*/\w+\s*", "", objective).strip()
        return cleaned[:180] if cleaned else objective[:180]

    def _resolve_tex_compiler(self) -> str | None:
        for candidate in ("xelatex", "latexmk", "pdflatex"):
            resolved = shutil.which(candidate)
            if resolved:
                return resolved
        return None

    def _resolve_skill_path(self, aris_root: Path, relative_path: str) -> Path:
        direct = aris_root / relative_path
        if direct.exists():
            return direct
        normalized = relative_path.replace("/", "\\")
        if "skills\\skills-codex\\" in normalized:
            fallback = aris_root / normalized.replace("skills\\skills-codex\\", "skills\\")
            if fallback.exists():
                return fallback
        return direct

    def _skill_excerpt(self, path: Path, limit: int) -> str:
        text = path.read_text(encoding="utf-8", errors="ignore")
        frontmatter_match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
        metadata = ""
        body = text
        if frontmatter_match:
            metadata_block = frontmatter_match.group(1)
            body = frontmatter_match.group(2)
            name_match = re.search(r'^name:\s*"?(.*?)"?\s*$', metadata_block, re.M)
            desc_match = re.search(r'^description:\s*"?(.*?)"?\s*$', metadata_block, re.M)
            parts: list[str] = []
            if name_match:
                parts.append(f"Skill name: {name_match.group(1).strip()}")
            if desc_match:
                parts.append(f"Skill purpose: {desc_match.group(1).strip()}")
            metadata = "\n".join(parts)

        lines: list[str] = []
        for raw_line in body.splitlines():
            stripped = raw_line.rstrip()
            if not stripped:
                if lines and lines[-1] != "":
                    lines.append("")
                continue
            if stripped.startswith("```"):
                continue
            lines.append(stripped)
            if len("\n".join(lines)) >= limit:
                break

        body_excerpt = "\n".join(lines)[:limit].strip()
        combined = "\n".join(part for part in [metadata, body_excerpt] if part).strip()
        return combined[:limit]

    def _file_excerpt(self, path: str, limit: int) -> str:
        file_path = Path(path)
        if not file_path.exists():
            return ""
        return file_path.read_text(encoding="utf-8", errors="ignore")[:limit]

    def _artifact_excerpt(self, task: TaskRun, relative_path: str) -> str:
        target = self._artifact_path(task, relative_path)
        if not target.exists():
            return ""
        return target.read_text(encoding="utf-8", errors="ignore")[:4000]

    def _artifact_text(self, task: TaskRun, relative_path: str) -> str:
        target = self._artifact_path(task, relative_path)
        if not target.exists():
            return ""
        return target.read_text(encoding="utf-8", errors="ignore")

    def _artifact_path(self, task: TaskRun, relative_path: str) -> Path:
        root = Path(task.artifact_root)
        canonical = root / self._canonical_artifact_path(relative_path)
        if canonical.exists():
            return canonical
        return root / relative_path

    def _select_figure_image_size(self, objective: str, briefs: str) -> str:
        text = f"{objective}\n{briefs}".lower()
        portrait_keywords = ("poster", "vertical", "portrait", "竖", "海报")
        if any(keyword in text for keyword in portrait_keywords):
            return "1024x1536"
        square_keywords = ("icon", "logo", "square", "示意图标")
        if any(keyword in text for keyword in square_keywords):
            return "1024x1024"
        return "1536x1024"

    def _strip_command(self, message: str, command: str, alias: str | None = None) -> str:
        stripped = message.strip()
        tokens = [command]
        if alias and alias not in tokens:
            tokens.append(alias)
        for token in tokens:
            if stripped.startswith(token):
                return stripped[len(token) :].strip() or stripped
        return stripped

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .agent import ResearchAgentService
from .config import config
from .models import UploadBatchRecord
from .upstream import extract_text_from_message
from .upstream import list_models as upstream_list_models
from .uploads import (
    classify_upload,
    next_upload_relative_path,
    normalize_upload_target,
    sanitize_upload_filename,
    upload_artifact_kind,
)


CHAT_PAGE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:,">
  <title>Research Agent</title>
  <style>
    :root { color-scheme: light; --bg:#f3f0e8; --panel:#fffdf8; --ink:#1e2430; --line:#d8d2c7; --accent:#2457d6; --soft:#eef2fb; --warn:#a54a14; }
    * { box-sizing:border-box; }
    body { margin:0; font-family:"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; background:linear-gradient(160deg,#efe7d6 0%,#f6f4ee 45%,#ebeef7 100%); color:var(--ink); }
    .wrap { max-width:1060px; margin:32px auto; padding:0 16px; }
    .card { background:rgba(255,253,248,.94); border:1px solid var(--line); border-radius:20px; box-shadow:0 18px 60px rgba(36,56,90,.12); overflow:hidden; }
    .hero { padding:24px; border-bottom:1px solid var(--line); }
    .hero h1 { margin:0 0 8px; font-size:28px; }
    .hero p { margin:0 0 10px; color:#4a5365; line-height:1.5; }
    .hero code { background:#f4f1ea; padding:2px 6px; border-radius:8px; }
    .toolbar { display:flex; gap:12px; padding:16px 20px 0; }
    .toolbar input { flex:1; padding:12px 14px; border:1px solid var(--line); border-radius:12px; background:#fff; }
    .layout { display:grid; grid-template-columns:minmax(0,1.6fr) minmax(320px,.9fr); }
    .chat { height:56vh; overflow:auto; padding:20px; display:flex; flex-direction:column; gap:14px; border-right:1px solid var(--line); }
    .msg { max-width:88%; padding:14px 16px; border-radius:16px; white-space:pre-wrap; line-height:1.55; }
    .user { align-self:flex-end; background:#2457d6; color:#fff; }
    .assistant { align-self:flex-start; background:var(--soft); color:#1e2430; }
    .sidebar { padding:18px 20px 20px; background:#faf8f1; display:flex; flex-direction:column; gap:18px; }
    .section { display:flex; flex-direction:column; gap:8px; }
    .section h3 { margin:0; font-size:15px; }
    .status { font-size:14px; color:#4a5365; line-height:1.5; }
    .cloud-links { display:flex; gap:10px; flex-wrap:wrap; }
    .cloud-links a { color:#2457d6; text-decoration:none; font-size:13px; }
    .checkpoint-box { padding:12px 14px; border:1px solid #e5dccd; border-radius:14px; background:#fffaf2; white-space:pre-wrap; line-height:1.45; font-size:14px; }
    .feedback { width:100%; min-height:96px; resize:vertical; padding:12px 14px; border:1px solid var(--line); border-radius:12px; font:inherit; background:#fff; }
    .actions { display:flex; gap:10px; flex-wrap:wrap; }
    .actions[hidden] { display:none; }
    .button { border:0; border-radius:12px; padding:11px 14px; cursor:pointer; font:inherit; }
    .primary { background:var(--accent); color:#fff; }
    .secondary { background:#fff; color:#1e2430; border:1px solid var(--line); }
    .composer { padding:16px 20px 20px; border-top:1px solid var(--line); display:flex; gap:12px; }
    .composer textarea { flex:1; min-height:108px; resize:vertical; padding:14px; border:1px solid var(--line); border-radius:14px; font:inherit; background:#fff; }
    .composer .button { width:150px; }
    .upload-panel { padding:16px 20px; border-top:1px solid var(--line); background:#faf8f1; display:grid; grid-template-columns:minmax(0,1fr) 180px; gap:12px; align-items:stretch; }
    .drop-zone { min-height:92px; border:2px dashed #aeb9d4; background:#fff; display:flex; align-items:center; justify-content:center; gap:12px; padding:16px; cursor:pointer; transition:border-color .16s,background .16s; }
    .drop-zone:focus-visible { outline:3px solid rgba(36,87,214,.22); outline-offset:2px; }
    .drop-zone.dragging { border-color:var(--accent); background:#eef2fb; }
    .upload-icon { width:34px; height:34px; border:1px solid #b9c5df; display:grid; place-items:center; color:var(--accent); font-size:20px; flex:0 0 auto; }
    .upload-copy { min-width:0; }
    .upload-copy strong { display:block; font-size:14px; margin-bottom:4px; }
    .upload-controls { display:flex; flex-direction:column; gap:8px; }
    .upload-controls label { font-size:12px; color:#6c7484; }
    .upload-controls select { width:100%; padding:10px 12px; border:1px solid var(--line); background:#fff; font:inherit; }
    .upload-status { grid-column:1 / -1; min-height:20px; font-size:13px; color:#4a5365; }
    .upload-status.error { color:#a12d2d; }
    .upload-list { grid-column:1 / -1; display:flex; flex-wrap:wrap; gap:8px; }
    .upload-item { padding:6px 9px; border:1px solid #d7dfef; background:#fff; font-size:12px; word-break:break-all; }
    .artifacts, .progress { display:flex; flex-direction:column; gap:8px; }
    .artifacts a { color:#2457d6; text-decoration:none; word-break:break-all; }
    .artifact-card { display:flex; flex-direction:column; gap:8px; padding:10px 12px; background:#fff; border:1px solid #e7e0d4; border-radius:12px; }
    .artifact-preview { max-width:100%; border:1px solid #ddd6c8; border-radius:10px; background:#fff; }
    .progress-item { padding:10px 12px; background:#fff; border:1px solid #e7e0d4; border-radius:12px; font-size:13px; line-height:1.45; }
    .muted { color:#6c7484; font-size:13px; }
    .warning { color:var(--warn); }
    @media (max-width: 900px) {
      .layout { grid-template-columns: 1fr; }
      .chat { border-right:0; border-bottom:1px solid var(--line); height:44vh; }
      .upload-panel { grid-template-columns:1fr; }
      .upload-status, .upload-list { grid-column:1; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <div class="hero">
        <h1>Research Agent</h1>
        <p>这是科研智能体，不是通用聊天机器人。它面向文献调研、选题、实验、论文写作、审稿回复和研究记忆。</p>
        <p>常用命令：<code>/review</code> <code>/idea</code> <code>/plan</code> <code>/code</code> <code>/write</code> <code>/rebuttal</code> <code>/fig</code> <code>/present</code> <code>/wiki</code></p>
        <p><code>/present</code> 默认优先使用最近上传批次；可通过 <code>--type paper|stage</code> 和 <code>--source attachments|selected|session|workspace</code> 控制汇报类型与材料范围。</p>
      </div>
      <div class="toolbar">
        <input id="session" placeholder="首次发消息后会显示 session id" readonly>
        <input id="hint" value="例如：/idea 做一个关于科研写作智能体的选题；或直接问：你是谁？">
      </div>
      <div class="layout">
        <div id="chat" class="chat"></div>
        <div class="sidebar">
          <div class="section">
            <h3>当前状态</h3>
            <div id="status" class="status">当前没有活动任务。</div>
          </div>
          <div class="section">
            <h3>云端工作区</h3>
            <div id="cloud-status" class="status">未启用云盘同步。</div>
            <div id="cloud-links" class="cloud-links"></div>
          </div>
          <div class="section">
            <h3>审核点</h3>
            <div id="checkpoint" class="checkpoint-box muted">当前没有待审核的 checkpoint。</div>
            <textarea id="feedback" class="feedback" placeholder="如果要打回修改，在这里写反馈。例如：请把实验设计更具体，补上评价指标。"></textarea>
            <div id="actions" class="actions" hidden>
              <button id="approve" class="button primary" type="button">批准继续</button>
              <button id="revise" class="button secondary" type="button">发送修改意见</button>
            </div>
            <div class="muted">批准时可留空。打回修改时请填写具体意见。</div>
          </div>
          <div class="section">
            <h3>中间进度</h3>
            <div id="progress" class="progress">
              <div class="progress-item muted">任务执行后，这里会显示路由、阶段开始、阶段完成、等待审核等中间步骤摘要。</div>
            </div>
          </div>
          <div class="section">
            <h3>最新产物</h3>
            <div id="artifacts" class="artifacts">
              <div class="muted">当前没有产物。</div>
            </div>
          </div>
        </div>
      </div>
      <div class="upload-panel">
        <div id="drop-zone" class="drop-zone" role="button" tabindex="0" aria-label="上传研究文件">
          <span class="upload-icon" aria-hidden="true">&#8593;</span>
          <div class="upload-copy">
            <strong>拖拽文件到这里，或点击选择</strong>
            <span class="muted">支持多文件；自动归档到当前会话工作区</span>
          </div>
        </div>
        <div class="upload-controls">
          <label for="upload-target">归档目录</label>
          <select id="upload-target">
            <option value="auto">自动分类</option>
            <option value="bib">bib</option>
            <option value="plan">plan</option>
            <option value="idea">idea</option>
            <option value="code">code</option>
            <option value="figures">figures</option>
            <option value="paper">paper</option>
            <option value="presentation">presentation</option>
            <option value="rebuttal">rebuttal</option>
            <option value="wiki">wiki</option>
            <option value="Content">Content</option>
            <option value="logs">logs</option>
          </select>
        </div>
        <input id="file-input" type="file" multiple hidden>
        <div id="upload-status" class="upload-status" aria-live="polite"></div>
        <div id="upload-list" class="upload-list"></div>
      </div>
      <div class="composer">
        <textarea id="prompt" placeholder="输入问题或命令。例如：/write 写一篇关于 retrieval-aware writing agents 的论文，默认输出 word 和 pdf"></textarea>
        <button id="send" class="button primary" type="button">发送</button>
      </div>
    </div>
  </div>
  <script>
    const chat = document.getElementById("chat");
    const prompt = document.getElementById("prompt");
    const feedbackEl = document.getElementById("feedback");
    const send = document.getElementById("send");
    const sessionInput = document.getElementById("session");
    const statusEl = document.getElementById("status");
    const cloudStatusEl = document.getElementById("cloud-status");
    const cloudLinksEl = document.getElementById("cloud-links");
    const checkpointEl = document.getElementById("checkpoint");
    const artifactsEl = document.getElementById("artifacts");
    const progressEl = document.getElementById("progress");
    const actionsEl = document.getElementById("actions");
    const approveBtn = document.getElementById("approve");
    const reviseBtn = document.getElementById("revise");
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const uploadTarget = document.getElementById("upload-target");
    const uploadStatus = document.getElementById("upload-status");
    const uploadList = document.getElementById("upload-list");
    let currentTaskId = "";
    let currentCheckpoint = null;
    let uploadInProgress = false;
    let pollTimer = null;

    function renderMessage(role, content) {
      const div = document.createElement("div");
      div.className = `msg ${role}`;
      div.textContent = content;
      chat.appendChild(div);
      chat.scrollTop = chat.scrollHeight;
    }

    function renderArtifacts(artifacts) {
      artifactsEl.innerHTML = "";
      if (!artifacts || artifacts.length === 0) {
        artifactsEl.innerHTML = '<div class="muted">当前没有产物。</div>';
        return;
      }
      for (const artifact of artifacts) {
        const card = document.createElement("div");
        card.className = "artifact-card";
        const a = document.createElement("a");
        a.href = artifact.url_path;
        a.target = "_blank";
        a.textContent = `${artifact.relative_path} - ${artifact.description}`;
        card.appendChild(a);
        if (artifact.kind === "image" || /\\.(png|jpg|jpeg|webp|gif)$/i.test(artifact.relative_path || "")) {
          const img = document.createElement("img");
          img.src = artifact.url_path;
          img.alt = artifact.relative_path;
          img.className = "artifact-preview";
          card.appendChild(img);
        }
        artifactsEl.appendChild(card);
      }
    }

    function renderProgress(progress) {
      progressEl.innerHTML = "";
      if (!progress || progress.length === 0) {
        progressEl.innerHTML = '<div class="progress-item muted">当前没有中间进度摘要。</div>';
        return;
      }
      for (const item of progress) {
        const div = document.createElement("div");
        div.className = "progress-item";
        div.textContent = item;
        progressEl.appendChild(div);
      }
    }

    function renderCloudWorkspace(cloud) {
      cloudLinksEl.innerHTML = "";
      if (!cloud || !cloud.status || cloud.status === "disabled") {
        cloudStatusEl.textContent = "未启用云盘同步。";
        return;
      }
      if (cloud.status === "error") {
        cloudStatusEl.textContent = `同步失败：${cloud.error || "未知错误"}`;
        return;
      }
      cloudStatusEl.textContent = `已同步 ${cloud.synced_files || 0} 个文件到 ${cloud.remote_path || "云盘"}`;
      const links = [
        ["预览文件夹", cloud.preview_url || cloud.share_url],
        ["下载文件夹", cloud.download_url || cloud.share_url]
      ];
      for (const [label, url] of links) {
        if (!url) continue;
        const link = document.createElement("a");
        link.href = url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = label;
        cloudLinksEl.appendChild(link);
      }
    }

    function renderCheckpoint(checkpoint) {
      checkpointEl.classList.remove("warning");
      if (!checkpoint) {
        checkpointEl.textContent = "当前没有待审核的 checkpoint。";
        actionsEl.hidden = true;
        return;
      }
      checkpointEl.textContent = checkpoint.prompt || checkpoint.title || "待审核";
      actionsEl.hidden = false;
    }

    function scheduleTaskPoll() {
      if (pollTimer || !currentTaskId) return;
      pollTimer = window.setTimeout(pollTask, 1500);
    }

    function stopTaskPoll() {
      if (!pollTimer) return;
      window.clearTimeout(pollTimer);
      pollTimer = null;
    }

    async function pollTask() {
      pollTimer = null;
      if (!currentTaskId) return;
      const taskId = currentTaskId;
      try {
        const response = await fetch(`/api/tasks/${taskId}`, { cache: "no-store" });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || `获取任务状态失败 (${response.status})`);
        if (taskId === currentTaskId) renderState(data);
      } catch (error) {
        statusEl.textContent = `进度刷新失败：${String(error.message || error)}`;
        scheduleTaskPoll();
      }
    }

    function renderState(data) {
      currentTaskId = data.task_id || "";
      currentCheckpoint = data.checkpoint || null;
      if (data.session_id) {
        sessionInput.value = data.session_id;
        localStorage.setItem("research-agent-session", data.session_id);
      }
      if (currentTaskId) localStorage.setItem("research-agent-task", currentTaskId);
      statusEl.textContent = currentTaskId
        ? `Task ${currentTaskId} | ${data.command || ""} | ${data.status} | 当前阶段：${data.current_stage_name || data.workflow_title || "准备中"}`
        : "当前没有活动任务。";
      renderArtifacts(data.artifacts || []);
      renderProgress(data.progress || []);
      renderCloudWorkspace(data.cloud_workspace || {});
      renderCheckpoint(currentCheckpoint);
      if (data.status === "running") scheduleTaskPoll();
      else stopTaskPoll();
    }

    async function restoreTaskState() {
      const savedSession = localStorage.getItem("research-agent-session");
      const savedTask = localStorage.getItem("research-agent-task");
      if (savedSession) sessionInput.value = savedSession;
      try {
        if (savedTask) {
          const response = await fetch(`/api/tasks/${savedTask}`, { cache: "no-store" });
          if (response.ok) {
            renderState(await response.json());
            return;
          }
        }
        const response = await fetch("/api/tasks", { cache: "no-store" });
        if (!response.ok) return;
        const tasks = await response.json();
        const active = tasks.find(task => task.user_id === "local" && ["running", "waiting_human"].includes(task.status));
        if (active) {
          const detailResponse = await fetch(`/api/tasks/${active.task_id}`, { cache: "no-store" });
          if (detailResponse.ok) renderState(await detailResponse.json());
        }
      } catch (error) {
        statusEl.textContent = `恢复任务状态失败：${String(error.message || error)}`;
      }
    }

    function formatFileSize(bytes) {
      if (bytes < 1024) return `${bytes} B`;
      if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
      return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    }

    function showUploadedFiles(files) {
      uploadList.innerHTML = "";
      for (const file of files) {
        const item = document.createElement("span");
        item.className = "upload-item";
        item.textContent = `${file.relative_path} (${formatFileSize(file.size)})`;
        uploadList.appendChild(item);
      }
    }

    async function uploadFiles(fileList) {
      const files = Array.from(fileList || []).filter(file => file.size > 0);
      if (!files.length || uploadInProgress) return;
      uploadInProgress = true;
      dropZone.classList.remove("dragging");
      uploadStatus.classList.remove("error");
      uploadStatus.textContent = `正在上传 ${files.length} 个文件...`;
      const formData = new FormData();
      if (sessionInput.value) formData.append("session_id", sessionInput.value);
      formData.append("user_id", "local");
      formData.append("target", uploadTarget.value);
      for (const file of files) formData.append("files", file, file.name);
      try {
        const response = await fetch("/api/session/files", { method: "POST", body: formData });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || `上传失败 (${response.status})`);
        sessionInput.value = data.session_id;
        uploadStatus.textContent = `已上传 ${data.files.length} 个文件到 ${data.workspace_root}`;
        showUploadedFiles(data.files);
        renderCloudWorkspace(data.cloud_workspace || {});
      } catch (error) {
        uploadStatus.classList.add("error");
        uploadStatus.textContent = String(error.message || error);
      } finally {
        uploadInProgress = false;
        fileInput.value = "";
      }
    }

    async function submit() {
      const text = prompt.value.trim();
      if (!text) return;
      renderMessage("user", text);
      prompt.value = "";
      send.disabled = true;
      try {
        const response = await fetch("/api/agent/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionInput.value || null, message: text })
        });
        const data = await response.json();
        renderMessage("assistant", data.text || data.detail || "No response");
        renderState(data);
      } catch (error) {
        renderMessage("assistant", String(error));
      } finally {
        send.disabled = false;
      }
    }

    async function approveTask() {
      if (!currentTaskId) return;
      approveBtn.disabled = true;
      reviseBtn.disabled = true;
      try {
        const response = await fetch(`/api/tasks/${currentTaskId}/approve`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ feedback: feedbackEl.value.trim() })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || `审批失败 (${response.status})`);
        renderMessage("assistant", data.text || "已批准，正在后台生成。请在右侧查看实时进度。");
        feedbackEl.value = "";
        renderState(data);
      } catch (error) {
        renderMessage("assistant", String(error.message || error));
      } finally {
        approveBtn.disabled = false;
        reviseBtn.disabled = false;
      }
    }

    async function reviseTask() {
      if (!currentTaskId) return;
      const feedback = feedbackEl.value.trim();
      if (!feedback) {
        checkpointEl.textContent = "请先填写修改意见，再点击“发送修改意见”。";
        checkpointEl.classList.add("warning");
        return;
      }
      renderMessage("user", `修改意见：${feedback}`);
      approveBtn.disabled = true;
      reviseBtn.disabled = true;
      try {
        const response = await fetch(`/api/tasks/${currentTaskId}/reject`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ feedback })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || `发送修改意见失败 (${response.status})`);
        renderMessage("assistant", data.text || "修改意见已发送，正在后台重新生成。请在右侧查看实时进度。");
        feedbackEl.value = "";
        renderState(data);
      } catch (error) {
        renderMessage("assistant", String(error.message || error));
      } finally {
        approveBtn.disabled = false;
        reviseBtn.disabled = false;
      }
    }

    send.addEventListener("click", submit);
    prompt.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        submit();
      }
    });
    approveBtn.addEventListener("click", approveTask);
    reviseBtn.addEventListener("click", reviseTask);
    dropZone.addEventListener("click", () => fileInput.click());
    dropZone.addEventListener("keydown", event => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        fileInput.click();
      }
    });
    fileInput.addEventListener("change", () => uploadFiles(fileInput.files));
    document.addEventListener("dragover", event => {
      if (!event.dataTransfer || !Array.from(event.dataTransfer.types).includes("Files")) return;
      event.preventDefault();
      dropZone.classList.add("dragging");
    });
    document.addEventListener("dragleave", event => {
      if (!event.relatedTarget) dropZone.classList.remove("dragging");
    });
    document.addEventListener("drop", event => {
      if (!event.dataTransfer || !event.dataTransfer.files.length) return;
      event.preventDefault();
      uploadFiles(event.dataTransfer.files);
    });
    restoreTaskState();
  </script>
</body>
</html>"""


agent = ResearchAgentService()
background_tasks: dict[str, asyncio.Task[Any]] = {}
Path(config.artifact_root).mkdir(parents=True, exist_ok=True)


def task_status_payload(task_id: str, *, text: str = "") -> dict[str, Any]:
    task = agent.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Unknown task: {task_id}")
    checkpoint = (
        task.approvals[-1]
        if task.status == "waiting_human"
        and task.approvals
        and task.approvals[-1].status == "pending"
        else None
    )
    payload = task.model_dump()
    session = agent.store.load_session(task.session_id)
    payload.update(
        {
            "text": text or task.summary or task.error,
            "artifacts": [artifact.model_dump() for artifact in task.artifacts[-6:]],
            "progress": task.progress_log[-10:],
            "checkpoint": checkpoint.model_dump() if checkpoint else None,
            "cloud_workspace": session.cloud_workspace.model_dump() if session else {},
        }
    )
    return payload


async def run_task_in_background(task_id: str, operation: str, feedback: str) -> None:
    try:
        if operation == "approve":
            await agent.approve_task(task_id, feedback)
        elif operation == "reject":
            await agent.reject_task(task_id, feedback)
        else:
            await agent.continue_task(task_id)
    except BaseException as exc:
        agent.record_task_failure(task_id, exc)
        if isinstance(exc, asyncio.CancelledError):
            raise


def schedule_task(task_id: str, operation: str, feedback: str = "") -> None:
    active = background_tasks.get(task_id)
    if active and not active.done():
        return
    task = asyncio.create_task(run_task_in_background(task_id, operation, feedback))
    background_tasks[task_id] = task
    task.add_done_callback(lambda completed, key=task_id: background_tasks.pop(key, None))


async def resume_interrupted_tasks() -> None:
    for task in agent.list_tasks():
        if task.status == "running":
            operation = (
                "approve"
                if task.approvals and task.approvals[-1].status == "pending"
                else "continue"
            )
            schedule_task(task.task_id, operation)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await resume_interrupted_tasks()
    yield
    pending = [task for task in background_tasks.values() if not task.done()]
    for task in pending:
        task.cancel()
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)


app = FastAPI(title="research-agent-platform", version="0.4.0", lifespan=lifespan)
app.mount("/workspace-files", StaticFiles(directory=config.artifact_root), name="workspace-files")


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/chat")


@app.get("/health")
async def health() -> dict[str, str]:
    models = await upstream_list_models()
    first_model = ((models.get("data") or [{}])[0]).get("id", "")
    return {"status": "ok", "model": first_model, "workspace": config.artifact_root}


@app.get("/chat")
def chat_page() -> HTMLResponse:
    return HTMLResponse(CHAT_PAGE)


@app.post("/api/agent/chat")
async def api_agent_chat(payload: dict[str, Any]) -> dict[str, Any]:
    return await agent.chat(
        payload.get("session_id"),
        str(payload.get("message", "")),
        str(payload.get("user_id") or "local"),
    )


@app.post("/api/session/files")
async def api_upload_session_files(
    session_id: str | None = Form(None),
    user_id: str = Form("local"),
    target: str = Form("auto"),
    files: list[UploadFile] = File(...),
) -> dict[str, Any]:
    if not files:
        raise HTTPException(status_code=400, detail="No files were provided")
    if len(files) > config.upload_max_files:
        raise HTTPException(
            status_code=400,
            detail=f"At most {config.upload_max_files} files can be uploaded at once",
        )
    try:
        normalized_target = normalize_upload_target(target)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    max_bytes = config.upload_max_file_mb * 1024 * 1024
    for upload in files:
        if upload.size is not None and upload.size > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"{upload.filename or 'file'} exceeds the {config.upload_max_file_mb} MB limit",
            )

    session = agent.store.get_or_create_session(session_id, user_id or "local")
    workspace_root = agent.artifacts.session_root(
        user_id=session.user_id,
        session_id=session.session_id,
    )
    session.workspace_root = str(workspace_root.resolve())
    agent.store.save_session(session)
    artifacts: list[dict[str, Any]] = []
    for upload in files:
        try:
            filename = sanitize_upload_filename(upload.filename or "")
            directory = classify_upload(filename, normalized_target)
            content = await upload.read(max_bytes + 1)
            if len(content) > max_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"{filename} exceeds the {config.upload_max_file_mb} MB limit",
                )
            relative_path = next_upload_relative_path(workspace_root, directory, filename)
            artifact = agent.artifacts.write_bytes(
                "session-upload",
                relative_path,
                content,
                kind=upload_artifact_kind(filename),
                description="User-uploaded research material.",
                task_root=workspace_root,
            )
            artifacts.append({**artifact.model_dump(), "size": len(content)})
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        finally:
            await upload.close()

    upload_batch = UploadBatchRecord(
        relative_paths=[artifact["relative_path"] for artifact in artifacts]
    )
    session.upload_batches.append(upload_batch)
    session.upload_batches = session.upload_batches[-20:]
    agent.store.save_session(session)
    await agent.sync_session_workspace(session)

    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "workspace_root": str(workspace_root.resolve()),
        "upload_batch_id": upload_batch.upload_batch_id,
        "files": artifacts,
        "cloud_workspace": session.cloud_workspace.model_dump(),
    }


@app.get("/api/tasks")
def api_tasks(session_id: str | None = None) -> list[dict[str, Any]]:
    return [task.model_dump() for task in agent.list_tasks(session_id)]


@app.get("/api/tasks/{task_id}")
def api_task(task_id: str) -> dict[str, Any]:
    return task_status_payload(task_id)


@app.get("/api/tasks/{task_id}/files")
def api_task_files(task_id: str) -> dict[str, Any]:
    task = agent.get_task(task_id)
    if not task:
        return {"error": f"Unknown task: {task_id}"}
    root = Path(task.artifact_root)
    if not root.exists():
        return {"task_id": task_id, "files": []}
    files: list[dict[str, Any]] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        files.append(
            {
                "relative_path": path.relative_to(root).as_posix(),
                "absolute_path": str(path.resolve()),
                "url_path": agent.artifacts.url_for(root, path.relative_to(root).as_posix()),
                "size": path.stat().st_size,
            }
        )
    session = agent.store.load_session(task.session_id)
    return {
        "task_id": task_id,
        "artifact_root": task.artifact_root,
        "files": files,
        "cloud_workspace": session.cloud_workspace.model_dump() if session else {},
    }


@app.post("/api/tasks/{task_id}/approve")
async def api_approve(task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    task = agent.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Unknown task: {task_id}")
    active = background_tasks.get(task_id)
    if active and not active.done():
        return task_status_payload(task_id, text="任务已在后台执行，请查看实时进度。")
    if task.status != "waiting_human":
        raise HTTPException(status_code=409, detail=f"Task is not waiting for approval: {task.status}")
    agent.mark_task_scheduled(task_id, "approve")
    schedule_task(task_id, "approve", str(payload.get("feedback", "")))
    return task_status_payload(task_id, text="已批准，正在后台生成逐页内容、页面图片和 PPT。")


@app.post("/api/tasks/{task_id}/reject")
async def api_reject(task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    task = agent.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Unknown task: {task_id}")
    active = background_tasks.get(task_id)
    if active and not active.done():
        return task_status_payload(task_id, text="任务已在后台执行，请查看实时进度。")
    if task.status != "waiting_human":
        raise HTTPException(status_code=409, detail=f"Task is not waiting for revision: {task.status}")
    feedback = str(payload.get("feedback", "")).strip()
    if not feedback:
        raise HTTPException(status_code=400, detail="Revision feedback is required.")
    agent.mark_task_scheduled(task_id, "reject")
    schedule_task(task_id, "reject", feedback)
    return task_status_payload(task_id, text="修改意见已发送，正在后台重新生成大纲。")


@app.post("/api/tasks/{task_id}/resume")
async def api_resume(task_id: str) -> dict[str, Any]:
    task = agent.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Unknown task: {task_id}")
    active = background_tasks.get(task_id)
    if active and not active.done():
        return task_status_payload(task_id, text="任务已在后台执行，请查看实时进度。")
    if task.status not in {"running", "failed"}:
        raise HTTPException(status_code=409, detail=f"Task cannot be resumed from status: {task.status}")
    task.status = "running"
    task.error = ""
    task.summary = "正在从最近的工作流断点恢复。"
    agent._log_progress(task, task.summary)
    agent.store.save_task(task)
    session = agent.store.load_session(task.session_id)
    if session:
        session.active_task_id = task.task_id
        agent.store.save_session(session)
    operation = (
        "approve"
        if task.approvals and task.approvals[-1].status == "pending"
        else "continue"
    )
    schedule_task(task_id, operation)
    return task_status_payload(task_id, text="任务已从断点恢复，正在后台继续生成。")


@app.get("/v1/models")
async def list_models() -> dict[str, Any]:
    return await upstream_list_models()


@app.post("/v1/chat/completions")
async def chat_completions(payload: dict[str, Any]) -> dict[str, Any]:
    messages = payload.get("messages", [])
    session_id = None
    user_id = "local"
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        session_id = metadata.get("session_id")
        user_id = str(metadata.get("user_id") or metadata.get("user") or user_id)
    if not session_id:
        session_id = payload.get("user")
    if user_id == "local" and payload.get("user"):
        user_id = str(payload.get("user"))

    latest_user = ""
    for item in reversed(messages):
        if item.get("role") == "user":
            latest_user = extract_text_from_message(item.get("content", ""))
            break
    if not latest_user:
        latest_user = "Please summarize the current task state."

    agent_result = await agent.chat(session_id, latest_user, user_id)
    assistant_text = agent_result["text"]
    response_id = agent_result["task_id"] or agent_result["session_id"]
    return {
        "id": f"chatcmpl-{response_id}",
        "object": "chat.completion",
        "created": 0,
        "model": payload.get("model", "research-agent-platform"),
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": assistant_text},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "x_agent_task": {
            "task_id": agent_result["task_id"],
            "status": agent_result["status"],
            "artifact_root": agent_result["artifact_root"],
            "session_id": agent_result["session_id"],
            "progress": agent_result.get("progress", []),
        },
    }


@app.post("/v1/responses")
async def responses(payload: dict[str, Any]) -> dict[str, Any]:
    session_id = None
    user_id = "local"
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        session_id = metadata.get("session_id")
        user_id = str(metadata.get("user_id") or metadata.get("user") or user_id)
    if user_id == "local" and payload.get("user"):
        user_id = str(payload.get("user"))
    result = await agent.chat(session_id, str(payload.get("input", "")), user_id)
    text = result["text"]
    response_id = result["task_id"] or result["session_id"]
    return {
        "id": f"resp-{response_id}",
        "object": "response",
        "created_at": 0,
        "model": payload.get("model", "research-agent-platform"),
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": text}],
            }
        ],
        "metadata": {
            "task_id": result["task_id"],
            "status": result["status"],
            "artifact_root": result["artifact_root"],
            "session_id": result["session_id"],
            "progress": result.get("progress", []),
        },
    }

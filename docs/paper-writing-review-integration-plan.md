# 论文写作与模拟审稿能力接入计划

> **分支：** `feat/paper-writing-review-capabilities`  
> **目标：** 将 `research-paper-agent` 已验证的写作、模拟审稿、返修和终检设计，以平台现有的会话、工作流、产物和 `/chat` UI 契约接入；不迁移独立运行时或重复实现平台已有能力。

## 1. 已审阅的现状

平台已提供可运行的 FastAPI 服务、内嵌 `/chat` UI、会话级工作区、文件上传、SSE 任务进度、LangGraph checkpoint、`/write`、`/review` 与 `/rebuttal` 工作流。写作流程已包含来源冻结、证据映射、提纲、草稿、自审、修订和 DOCX/PDF/TeX 导出；返修流程已包含输入冻结、评论映射、策略、回复、修订计划、修订稿和闭环报告。

`research-paper-agent` 已验证的差异化能力是：

- `WritingPackage` 和 `scientist-agent-handoff/v1`：对上游研究方案、代码、结果、图表和声明作可审计交接。
- 学科、语言、文章类型和 venue 路由：生成可复用的 `ManuscriptContext` 与写作上下文。
- 范文/规则驱动的 `FieldWritingGuide`：保存可解释的结构、修辞、字数和引用规则。
- 受控多角色模拟审稿：冻结稿件快照，角色只读并输出可定位的结构化 findings，再机械合并为 `ReviewPackage`。
- 返修变更审计：`changes.json`、统一 diff、修改理由、修订矩阵和逐条核验。
- 基础投稿终检：占位符、引用键、BibTeX、LaTeX 交叉引用和图表编号闭合。

## 2. 接入原则与边界

1. **以平台为宿主。** 复用 `ResearchAgentService`、`WorkflowDefinition`、`TaskRun`、`ArtifactStore`、上传路由、SSE 和 UI；不嵌套或调用另一个 `ChatboxApplication`。
2. **先扩展契约，再接入生成。** 每项能力先定义稳定 JSON/Markdown artifact、输入来源和确定性校验，再添加 LLM 阶段。
3. **保持目录所有权。** 平台已有 `paper/`、`rebuttal/`、`Content/`、`plan/` 和 `bib/`；新产物必须落入这些目录，不新建平行项目根目录。
4. **证据优先与最小修改。** 数字、公式、引文、图表与结论仅可来自冻结 SourceSet；缺失项显式标记为 `AUTHOR INPUT NEEDED`。
5. **模拟审稿不冒充真实审稿。** UI、artifact 和回复均称“模拟审稿”，不得给出投稿决定。
6. **不迁移本地生成物。** 不复制 `.venv`、`__pycache__`、`evaluation_runs`、旧版架构 HTML 或与平台已有 skill 重复的整套资源。

## 3. 契约映射

| 现有论文 Agent 能力 | 平台接入位置 | 新增/兼容产物 | 适配重点 |
| --- | --- | --- | --- |
| `/paper-init` + 上游 handoff | `/write` 的确定性 `paper_evidence` 前置阶段 | `Content/WRITING_PACKAGE.json`、`Content/UPSTREAM_HANDOFFS.json` | 将附件、工作区材料和 `scientist-agent-handoff/v1` 统一为可追溯输入；保留现有 `PAPER_SOURCE_SELECTION.json`。 |
| 学科/语言/venue 路由 | `/write` 的 `paper_plan`、`draft_sections`、`paper_self_review` 提示上下文 | `Content/MANUSCRIPT_CONTEXT.json`、`Content/WRITING_CONTEXT.json` | 从命令、附件和 `PAPER_PLAN.md` 解析显式字段；用户选择优先于推断。 |
| 风格学习 | 新增 `/style` 工作流，或作为 `/write --style` 的独立阶段 | `paper/guides/FIELD_WRITING_GUIDE.json` | 先以规则摘要落盘；仅在有范文时启用，禁止复刻范文句子。 |
| `/paper-draft` + 段落契约 | 现有 `paper_plan` / `draft_sections` | 扩展 `PAPER_PLAN.md` 的 paragraph jobs、claim/evidence IDs、术语边界 | 不替换已有完整论文生成；增强上下文与验收字段。 |
| `/paper-revise` | 现有 `paper_revision` 或新增显式 `/revise` 路由 | `paper/CHANGES.json`、`paper/REVISION_DIFF.md`、`paper/CHANGE_RATIONALE.md` | 保留 `PAPER_REVISED.md` 作为交付源；差异与理由必须可复算。 |
| `/paper-review` 多角色模拟审稿 | 新增 `/peer-review` 工作流；`/rebuttal` 可读取其输出 | `rebuttal/reviews/REVIEW_SNAPSHOT.json`、`REVIEW_PACKAGE.json`、`REVIEW_REPORT.md` | editor/domain/methods/evidence/adversarial/language-format 角色只读，统一 finding schema，去重逻辑确定性。 |
| `/paper-revise-from-review` | 扩展现有 `/rebuttal` | 兼容 `REVIEW_PACKAGE.json`，补 `REVISION_MATRIX.json` 与 `REVISION_VERIFICATION.json` | 作者确认策略后才实施实质修改；现有 `REBUTTAL_CLOSURE_REPORT.json` 保持权威闭环报告。 |
| `/paper-final-check` | 新增 `/final-check` 工作流，或作为 `/write` / `/rebuttal` 可选末阶段 | `paper/FINAL_GATE_REPORT.json` | 先实现文本/LaTeX/BibTeX 的确定性检查，不承诺 PDF 视觉审稿或官方投稿规则抓取。 |

## 4. 建议分期实施

### Phase 0 — 合同与基线（首个 PR）

- 在 `models.py` 增加 `ManuscriptContext`、`WritingPackage`、`StructuredFinding`、`ReviewPackage` 和 `RevisionChange` 的 Pydantic schema。
- 新增可复用的确定性模块：输入归类、学科/语言/venue 解析、引用与占位符检查、diff/changeset、review finding 去重。
- 为每个 schema、输入边界和负例补单元测试；不改变 `/write`、`/review`、`/rebuttal` 的现有行为。
- 验收：`uv run pytest -q` 通过；JSON 产物可被已有 artifact API 和 UI 链接访问。

### Phase 1 — 写作上下文与审计（第二个 PR）

- 在 `paper_evidence` 后写入 `WRITING_PACKAGE` / `MANUSCRIPT_CONTEXT` / `WRITING_CONTEXT`，并注入 `paper_plan`、`draft_sections` 和 `paper_self_review`。
- 增强 `PAPER_PLAN.md`：补 paragraph jobs、claim-to-evidence map、术语边界和缺失证据。
- 为 `paper_revision` 生成 `CHANGES.json`、`REVISION_DIFF.md` 和 `CHANGE_RATIONALE.md`，但不改动现有的 `PAPER_REVISED.md` 交付路径。
- 验收：上传研究方案、结果表和 BibTeX 后，`/write --source attachments` 产生以上 artifact，并且未知引文、未提供数字不会被写成事实。

### Phase 2 — 模拟审稿与返修衔接（第三个 PR）

- 新增显式 `/peer-review`，而不是复用含义不同的 `/review`（后者是文献综述）。
- 在 `router/intent.py` 新增命令、别名与中英文启发式；在 `graphs/workflows.py` 注册冻结快照、角色 findings、合并报告三个阶段。
- `/rebuttal` 支持将 `REVIEW_PACKAGE.json` 作为审稿意见输入，并产出修订矩阵与逐条核验。
- 验收：同一输入在角色顺序不变时得到稳定的 finding ID；每条 rebuttal comment 都能回链到稿件位置、证据或明确缺口。

### Phase 3 — 风格学习与最终检查（独立、可延后）

- 添加 `/style` 生成可审计 `FIELD_WRITING_GUIDE.json`，在 `/write --style <path>` 时显式加载。
- 添加 `/final-check`，覆盖占位符、引文/BibTeX、LaTeX 引用、图表/表格编号和基础章节完整性。
- 验收：规则来自范文结构统计而非原句复制；终检报告能区分 `PASS`、`REVISE`、`BLOCK`。

## 5. 前端与 API 适配

- 现有前端无需重写：`/chat` 已支持文件选择/拖放、任务提交、SSE、checkpoint、artifact 链接与图片预览。
- UI 增量仅包括命令帮助、`/peer-review` 与 `/final-check` 的进度标题、以及对 `CHANGES.json` / `REVIEW_PACKAGE.json` / `FINAL_GATE_REPORT.json` 的更清晰描述。
- 继续使用 `POST /api/session/files` 上传，`POST /api/chat/tasks` 创建后台任务，`GET /api/tasks/{task_id}/events` 订阅 SSE。
- 健康检查和 `/v1/models` 依赖真实的 `UPSTREAM_API_KEY`；本地无模型时，应将前端的模型依赖错误明确显示，而不是把它误判为 UI 故障。

## 6. 前端自动化验收

每个涉及 UI 的 PR 在本地以 Playwright CLI 验收：

1. 启动服务：`uv run uvicorn --app-dir src research_agent_platform.api:app --host 127.0.0.1 --port 8000`。
2. 打开 `/chat`，创建会话，验证 session ID、输入框和状态栏。
3. 上传 Markdown/TXT、BibTeX 和审稿意见，确认它们被分流到预期工作区。
4. 提交 `/write`、`/peer-review`、`/rebuttal`、`/final-check`，验证 SSE 阶段、checkpoint、artifact 链接和错误状态。
5. 使用测试模型或 mock upstream 覆盖完整成功路径；真实模型凭据只留在未提交的 `.env`。

本分支的基线已完成真实浏览器冒烟：新建会话、普通消息、SSE 完成状态和 TXT 上传均正常。无 `.env` 的本地实例在 `/health` 与 `/v1/models` 返回 `500 Missing UPSTREAM_API_KEY`，这是预期配置前置条件。

## 7. Git 与 PR 工作流

```bash
# 本地分支已创建
git switch feat/paper-writing-review-capabilities

# 首个 PR 仅提交本计划和 Phase 0 的 schema/测试；不要混入平台无关清理
git push -u origin feat/paper-writing-review-capabilities

# 提交 PR 时：head=Amber-December:feat/paper-writing-review-capabilities
# base=chenlubenren:master

# 合并前同步上游
git fetch upstream
git rebase upstream/master
git push --force-with-lease origin feat/paper-writing-review-capabilities
```

若平台维护者希望小 PR，Phase 0、Phase 1、Phase 2、Phase 3 应分别提交/PR；若希望一个能力分支，则在同一分支按上述阶段提交，但每阶段都应可独立测试和回退。

## 8. 明确不在本轮合并范围

- 自动替作者决定投稿、回复策略或署名。
- 未授权全文抓取、绕过付费墙、伪造引用、结果或审稿结论。
- Word/PDF 原生格式保真编辑、PDF/VLM 视觉审稿、官方 venue guideline 自动抓取。
- 从原项目直接复制其虚拟环境、缓存、评测运行产物或整套独立 API/runtime。

## 9. 当前平台与分支架构

平台运行链路为：`FastAPI API` → `ResearchAgentService` → `router/intent.py` 意图路由 → `graphs/workflows.py` LangGraph 工作流 → `state/` 会话与任务状态、`artifacts/` 产物索引 → `agent-workspace/local/<session_id>/` 会话工作区 → `/chat` SSE 与下载链接。

核心目录职责如下：

| 目录 | 平台职责 | 本分支融合点 |
| --- | --- | --- |
| `router/` | 显式命令、别名和启发式/LLM 路由 | 注册 `/peer-review`、`/final-check` |
| `graphs/` | 工作流阶段、进度和产物交付 | 接入模拟审稿、投稿终检阶段 |
| `paper/` | 稿件、来源选择、证据图、修订和导出 | `FINAL_GATE_REPORT.*`、`REVISION_AUDIT.json` |
| `rebuttal/` | 审稿意见、回复和闭环 | `reviews/REVIEW_PACKAGE.*` |
| `Content/` | 上下文、索引、评测和任务记录 | `WRITING_CONTEXT.json`、`WRITING_EVALUATION_REPORT.json` |
| `bib/` | BibTeX、论文 PDF 和文献下载记录 | `@key`、`\\cite{}`、author-year 闭合检查 |
| `tests/` | 工作流、API、文件、UI 契约的回归测试 | 写作/审稿/终检和对抗性 rubric 测试 |

当前分支没有平行运行时：写作能力复用现有 `/write`，文献综述仍由 `/review` 负责，返修仍由 `/rebuttal` 负责；新增能力只通过命令路由和标准 artifact 接入前端。

## 10. 当前实现状态

已实现：`/write` 写作上下文与修订审计；`/peer-review` 确定性模拟审稿；`/final-check` 稿件、引用、占位符、Markdown/LaTeX 章节、LaTeX 交叉引用和 Markdown 图表编号终检；写作质量 rubric；`@key`、`\\cite{}`、常见单姓 author-year 与 BibTeX 闭合；PE ID 与 `PAPER_EVIDENCE_MAP.json` 闭合；强主张和量化主张的邻近证据检查；前端文件上传、SSE 进度和 artifact 下载链路。

尚未实现：真正的多角色 LLM 同行评审与语义去重；author-year 的复杂姓名、机构作者、跨年后缀和 BibTeX 宏的完整解析；PDF/VLM 视觉审稿；不同期刊官方规范自动抓取；自动把 review findings 转成 `/rebuttal` 修订矩阵并安全修改正文；真实投稿系统提交。

当前质量边界：`PASS` 只表示确定性规则通过，不等于期刊接收；模拟审稿不代表真实审稿决定；无模型凭据时，平台 API 的模型调用仍会因缺少 `UPSTREAM_API_KEY` 失败，但本地确定性工作流和测试不依赖真实模型。

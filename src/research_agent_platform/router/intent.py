from __future__ import annotations

from dataclasses import dataclass

from ..upstream import generate_text


APPROVE_WORDS = {
    "approve",
    "approved",
    "go",
    "continue",
    "ok",
    "yes",
    "y",
    "同意",
    "批准",
    "继续",
    "通过",
    "可以",
}

STOP_WORDS = {"stop", "halt", "cancel", "停止", "取消"}

ALIASES = {
    "/research-pipeline": "/plan",
    "/pipeline": "/plan",
    "/idea-discovery": "/idea",
    "/experiment-bridge": "/code",
    "/paper-writing": "/write",
    "/literature-review": "/review",
    "/lit-review": "/review",
    "/auto-review-loop": "/rebuttal",
    "/review-response": "/rebuttal",
    "/paper-slides": "/present",
    "/research-wiki": "/wiki",
}

COMMAND_DESCRIPTIONS = {
    "/review": "search, organize, and synthesize research literature and evidence",
    "/idea": "generate, challenge, verify, and select research ideas",
    "/plan": "turn a selected idea or objective into experiments and an execution plan",
    "/code": "turn the chosen plan into implementation and experiment execution materials",
    "/fig": "design figures, tables, and visual narratives for the research output",
    "/write": "create paper outlines, narrative reports, and draft sections",
    "/rebuttal": "analyze peer-review comments and produce rebuttal and revision materials",
    "/present": "prepare slides, poster, talk track, and Q&A materials",
    "/wiki": "update persistent research memory and reusable knowledge notes",
}

HEURISTICS = {
    "/review": [
        "literature review",
        "related work",
        "survey paper",
        "literature search",
        "文献综述",
        "文献调研",
        "找文献",
        "相关工作",
        "查新",
    ],
    "/idea": ["idea", "novelty", "research topic", "选题", "想法", "创新点", "研究方向"],
    "/plan": [
        "experiment plan",
        "research plan",
        "roadmap",
        "pipeline",
        "milestone",
        "实验方案",
        "研究计划",
        "规划",
        "路线图",
    ],
    "/code": ["experiment", "implement", "code", "reproduce", "run", "实验", "实现", "复现"],
    "/fig": ["figure", "plot", "diagram", "chart", "图", "图表", "流程图"],
    "/write": ["paper", "draft", "write", "manuscript", "论文", "写作", "草稿"],
    "/rebuttal": [
        "rebuttal",
        "reviewer comments",
        "peer review",
        "revision letter",
        "审稿意见",
        "审稿回复",
        "返修",
        "回复审稿人",
    ],
    "/present": ["slides", "poster", "talk", "presentation", "汇报", "答辩", "ppt"],
    "/wiki": ["wiki", "memory", "knowledge base", "知识库", "记忆", "归档"],
}

CHAT_CUES = {
    "hello",
    "hi",
    "hey",
    "你好",
    "您好",
    "在吗",
    "谢谢",
    "thanks",
    "how are you",
    "who are you",
}


@dataclass
class RouteDecision:
    command: str
    source: str
    reason: str


def is_approval_message(message: str) -> bool:
    return message.strip().lower() in APPROVE_WORDS


def is_stop_message(message: str) -> bool:
    return message.strip().lower() in STOP_WORDS


def _looks_like_chat(message: str) -> bool:
    stripped = message.strip().lower()
    if not stripped:
        return True
    if stripped in CHAT_CUES:
        return True
    return len(stripped) <= 24 and any(cue in stripped for cue in CHAT_CUES)


async def route_message(message: str) -> RouteDecision | None:
    stripped = message.strip()
    first_token = stripped.split(maxsplit=1)[0] if stripped else ""
    if first_token.startswith("/"):
        command = ALIASES.get(first_token, first_token)
        if command in COMMAND_DESCRIPTIONS:
            return RouteDecision(command=command, source="explicit", reason=f"explicit command {first_token}")

    if _looks_like_chat(stripped):
        return None

    lowered = stripped.lower()
    best_command = ""
    best_score = (0, 0)
    for command, keywords in HEURISTICS.items():
        matches = [keyword for keyword in keywords if keyword.lower() in lowered]
        score = (len(matches), sum(len(keyword) for keyword in matches))
        if score > best_score:
            best_command = command
            best_score = score
    if best_command and best_score[0] > 0:
        return RouteDecision(
            command=best_command,
            source="implicit_heuristic",
            reason=f"keyword heuristic matches={best_score[0]} specificity={best_score[1]}",
        )

    options = "\n".join(f"{name}: {description}" for name, description in COMMAND_DESCRIPTIONS.items())
    classifier_prompt = (
        "Classify the user's request into exactly one command from the list below, or return chat if this is casual conversation.\n"
        "Return only one token: a command token or chat.\n\n"
        f"{options}\n\nUser request:\n{message}"
    )
    raw = await generate_text(
        system_prompt="You are a strict intent router. Output one token only.",
        user_prompt=classifier_prompt,
        temperature=0,
    )
    command = raw.strip().splitlines()[0].strip()
    if command.lower() == "chat":
        return None
    command = ALIASES.get(command, command)
    if command not in COMMAND_DESCRIPTIONS:
        return None
    return RouteDecision(command=command, source="implicit_llm", reason=f"llm classifier -> {command}")

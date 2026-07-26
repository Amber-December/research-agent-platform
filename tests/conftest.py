from __future__ import annotations

import asyncio
import io
import sys
from pathlib import Path

import pytest
from PIL import Image

PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from research_agent_platform import agent as agent_module
from research_agent_platform.config import config
from research_agent_platform.agent import ResearchAgentService
from research_agent_platform.upstream import GeneratedImage


@pytest.fixture()
def isolated_env(tmp_path, monkeypatch):
    state_root = tmp_path / ".agent-state"
    artifact_root = tmp_path / "agent-workspace"
    wiki_root = tmp_path / "research-wiki"
    aris_root = tmp_path / "aris"
    prd_path = tmp_path / "research-agent-prd.md"
    tech_spec_path = tmp_path / "research-agent-tech-spec.md"

    for path in (state_root, artifact_root, wiki_root, aris_root):
        path.mkdir(parents=True, exist_ok=True)

    prd_path.write_text("# PRD\n\nTest PRD.", encoding="utf-8")
    tech_spec_path.write_text("# Tech Spec\n\nTest tech spec.", encoding="utf-8")

    monkeypatch.setattr(config, "state_root", str(state_root))
    monkeypatch.setattr(config, "artifact_root", str(artifact_root))
    monkeypatch.setattr(config, "wiki_root", str(wiki_root))
    monkeypatch.setattr(config, "aris_repo_root", str(aris_root))
    monkeypatch.setattr(config, "prd_path", str(prd_path))
    monkeypatch.setattr(config, "tech_spec_path", str(tech_spec_path))
    monkeypatch.setattr(config, "upstream_api_key", "test-key")
    monkeypatch.setattr(config, "upstream_base_url", "https://example.invalid/v1")
    monkeypatch.setattr(config, "upstream_model", "gpt-5.4-mini")
    monkeypatch.setattr(config, "image_model", "gpt-image-2")

    async def fake_generate_text(*, system_prompt, user_prompt, model=None, temperature=0.3):
        prompt = f"{system_prompt}\n{user_prompt}"
        if "Current stage: Slides Outline" in prompt:
            return (
                "# 幻灯片大纲\n\n"
                "## Talk Arc\n- 问题\n- 方案\n- 结果\n\n"
                "## Slide List\n- 封面\n- 问题\n- 方法\n- 结论\n\n"
                "## Key Evidence per Slide\n- 关键证据\n\n"
                "## Open Design Questions\n- 无"
            )
        if "Current stage: Slide Content" in prompt:
            return (
                "# Stage Report\n\n"
                "## Slide 1: Research objective\n"
                "### Page Type\ncover\n"
                "### Render Mode\nimage2_full\n"
                "### Layout Hint\nhero\n"
                "### Main Message\n- Define the current question.\n"
                "### On-Slide Text\n- Objective and scope\n"
                "### Visual\n- Minimal title composition\n"
                "### Source Files\n- `plan/EXPERIMENT_PLAN.md`\n\n"
                "## Slide 2: Stage conclusion\n"
                "### Page Type\nnarrative\n"
                "### Render Mode\nimage2_full\n"
                "### Layout Hint\nprimary-secondary\n"
                "### Main Message\n- Summarize available evidence.\n"
                "### On-Slide Text\n- Results, risks, and next steps\n"
                "### Visual\n- Result and conclusion\n"
                "### Source Files\n- `figures/RESULT.png`\n"
            )
        if "Current stage: Speaker Notes" in prompt:
            return (
                "# 讲者备注\n\n"
                "## Per-Slide Notes\n- 逐页说明\n\n"
                "## Timing\n- 10 分钟\n\n"
                "## Transitions\n- 平滑过渡\n\n"
                "## Backup Slides\n- 备份页"
            )
        if "Current stage: Q and A Brief" in prompt:
            return (
                "# Q&A 简报\n\n"
                "## Likely Questions\n- 会不会过拟合？\n\n"
                "## Recommended Answers\n- 说明控制变量\n\n"
                "## Evidence Pointers\n- 指向实验结果"
            )
        return "# 通用回复\n\n- 已生成。"

    monkeypatch.setattr(agent_module, "generate_text", fake_generate_text)

    async def fake_generate_image(
        *,
        prompt,
        model=None,
        size="1536x1024",
        quality="low",
        output_format="png",
        input_image=None,
        input_image_name="source.png",
        input_image_mime_type="image/png",
    ):
        buffer = io.BytesIO()
        Image.new("RGB", (1536, 1024), color=(245, 248, 250)).save(buffer, format="PNG")
        return GeneratedImage(
            image_bytes=buffer.getvalue(),
            mime_type="image/png",
            model=model or "gpt-image-2",
            revised_prompt="",
            size=size,
            quality=quality,
            output_format=output_format,
        )

    monkeypatch.setattr(agent_module, "generate_image", fake_generate_image)

    return {
        "state_root": state_root,
        "artifact_root": artifact_root,
        "wiki_root": wiki_root,
        "aris_root": aris_root,
        "prd_path": prd_path,
        "tech_spec_path": tech_spec_path,
    }


@pytest.fixture()
def service(isolated_env):
    return ResearchAgentService()


def run(coro):
    return asyncio.run(coro)

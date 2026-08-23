from research_agent_platform.agent import _retain_requested_write_sections


def test_section_delivery_keeps_only_requested_abstract_and_keywords():
    content = """# Title

## 摘要
拟开展洪涝避险规划研究，不报告既有结果。

## 关键词
洪涝避险；应急避难场所

## 引言
This section must not be delivered.
"""

    delivered = _retain_requested_write_sections(content, ["摘要", "关键词"])

    assert delivered.startswith("## 摘要")
    assert "## 关键词" in delivered
    assert "## 引言" not in delivered
    assert "This section" not in delivered

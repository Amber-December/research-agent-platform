from __future__ import annotations

import asyncio
from pathlib import Path

import httpx

from research_agent_platform.connectors.scholar import LiteratureBundle, PaperRecord
from research_agent_platform.institutional_access import (
    build_institutional_handoff,
    institutional_handoff_markdown,
)
from research_agent_platform.literature_downloads import download_public_pdfs


def _bundle(*pdf_urls: str) -> LiteratureBundle:
    papers = [
        PaperRecord(
            title=f"Research paper {index}",
            year=2024,
            abstract="Abstract",
            authors=["Author"],
            url=f"https://doi.org/10.1000/{index}",
            venue="Journal",
            citation_count=1,
            paper_id=f"P{index:03d}",
            pdf_url=pdf_url,
        )
        for index, pdf_url in enumerate(pdf_urls, start=1)
    ]
    return LiteratureBundle(query="test", papers=papers, provider_status={})


def test_download_public_pdfs_writes_only_valid_pdf(monkeypatch, tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("valid.pdf"):
            return httpx.Response(200, content=b"%PDF-1.7\nvalid", request=request)
        return httpx.Response(200, content=b"<html>not a pdf</html>", request=request)

    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    bundle = _bundle(
        "https://example.org/valid.pdf",
        "https://example.org/html.pdf",
        "",
    )

    result = asyncio.run(download_public_pdfs(bundle, tmp_path, timeout_seconds=1))

    assert result["counts"]["downloaded"] == 1
    assert result["counts"]["invalid_pdf"] == 2
    assert result["counts"].get("no_public_pdf", 0) == 0
    assert (tmp_path / "bib/papers/P001_Research_paper_1.pdf").read_bytes().startswith(b"%PDF")
    assert bundle.papers[1].download_status == "invalid_pdf"
    assert bundle.papers[2].download_status == "invalid_pdf"


def test_download_public_pdfs_respects_limit(monkeypatch, tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"%PDF-1.7\nvalid", request=request)

    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    result = asyncio.run(
        download_public_pdfs(
            _bundle("https://example.org/one.pdf", "https://example.org/two.pdf"),
            tmp_path,
            limit=1,
            timeout_seconds=1,
        )
    )
    assert result["counts"]["downloaded"] == 1
    assert result["counts"]["skipped_limit"] == 1


def test_institutional_handoff_lists_non_downloaded_papers(tmp_path: Path) -> None:
    bundle = _bundle("", "https://example.org/open.pdf")
    bundle.papers[0].identifiers["doi"] = "10.1000/closed"
    bundle.papers[0].download_status = "no_public_pdf"
    bundle.papers[1].download_status = "downloaded"
    bundle.papers[1].downloaded_path = "bib/papers/P002_open.pdf"

    handoff = build_institutional_handoff(
        bundle,
        tmp_path,
        enabled=True,
        institution_name="Tsinghua University",
        gateway_base="https://tlink.lib.tsinghua.edu.cn/",
        eproxy_base="https://eproxy.lib.tsinghua.edu.cn/reader/home",
        openurl_base="https://resolver.example/openurl",
        proxy_prefix="",
        mode="handoff",
    )
    markdown = institutional_handoff_markdown(handoff)

    assert len(handoff["items"]) == 1
    assert handoff["items"][0]["paper_id"] == "P001"
    assert handoff["items"][0]["links"]["doi"] == "https://doi.org/10.1000/closed"
    assert "target=bib" in markdown

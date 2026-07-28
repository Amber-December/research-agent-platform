from __future__ import annotations

import asyncio
from pathlib import Path

import httpx

from research_agent_platform.agent import ResearchAgentService
from research_agent_platform.connectors.scholar import LiteratureBundle, PaperRecord
from research_agent_platform.graphs.workflows import workflow_registry
from research_agent_platform.literature_downloads import download_public_pdfs_from_sources


def _bundle(*, title: str = "Test paper", doi: str = "10.1000/test", pdf_url: str = "") -> LiteratureBundle:
    return LiteratureBundle(
        query=title,
        papers=[
            PaperRecord(
                title=title,
                year=2024,
                abstract="Abstract",
                authors=["Author"],
                url=f"https://doi.org/{doi}",
                venue="Journal",
                citation_count=1,
                paper_id="P001",
                pdf_url=pdf_url,
                identifiers={"doi": doi},
            )
        ],
        provider_status={"openalex": "ok"},
    )


def test_download_workflow_is_registered():
    workflows = workflow_registry()

    assert "/download" in workflows
    assert [stage.name for stage in workflows["/download"].stage_definitions] == [
        "download_plan",
        "download_search",
        "download_fetch",
    ]


def test_download_source_parser_reads_bib_and_text_sources(
    service: ResearchAgentService,
    monkeypatch,
):
    session = service.store.create_session()
    workspace = Path(session.workspace_root)
    bib = workspace / "bib"
    bib.mkdir(parents=True, exist_ok=True)
    (bib / "sources.bib").write_text(
        """@article{paper1,
  title = {Public PDF Lookup},
  doi = {10.1000/lookup},
  url = {https://example.org/article}
}""",
        encoding="utf-8",
    )
    (bib / "queries.txt").write_text(
        "Q1: download paper title\n10.1000/text-doi\nhttps://example.org/text",
        encoding="utf-8",
    )

    async def fake_search_bundle(query, **_kwargs):
        return _bundle(title="Public PDF Lookup", doi="10.1000/lookup", pdf_url="https://example.org/article.pdf")

    monkeypatch.setattr(service.scholar, "search_bundle", fake_search_bundle)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "doi.org" or request.url.path.endswith("article.pdf"):
            return httpx.Response(200, content=b"%PDF-1.7\nvalid", request=request)
        return httpx.Response(404, content=b"missing", request=request)

    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs),
    )

    result = asyncio.run(
        service.chat(
            session.session_id,
            "/download bib/sources.bib bib/queries.txt download paper title",
        )
    )
    task = service.get_task(result["task_id"])

    assert result["status"] == "completed"
    assert task is not None
    assert task.download_source is not None
    assert task.download_source.resolved_scope == "selected"
    assert "bib/sources.bib" in task.download_source.source_refs
    assert "bib/queries.txt" in task.download_source.source_refs
    assert task.download_source.query_terms


def test_download_public_pdfs_from_sources_uses_source_doi(monkeypatch, tmp_path: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        if "doi.org" in request.url.host:
            return httpx.Response(200, content=b"%PDF-1.7\npdf", request=request)
        return httpx.Response(404, content=b"missing", request=request)

    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs),
    )

    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "bib").mkdir(parents=True, exist_ok=True)
    (workspace / "bib" / "sources.bib").write_text(
        """@article{paper1,
  title = {Public PDF Lookup},
  doi = {10.1000/lookup}
}""",
        encoding="utf-8",
    )

    result = asyncio.run(
        download_public_pdfs_from_sources(
            _bundle(doi="10.1000/lookup"),
            workspace,
            ["bib/sources.bib"],
            timeout_seconds=1,
        )
    )

    assert result["counts"]["downloaded"] == 1
    assert (workspace / "bib" / "papers" / "P001_Test_paper.pdf").read_bytes().startswith(b"%PDF")

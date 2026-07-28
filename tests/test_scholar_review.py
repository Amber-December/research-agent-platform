from __future__ import annotations

import asyncio

import httpx

from research_agent_platform.connectors.scholar import PaperRecord, ScholarSearchService
from research_agent_platform.review_pipeline import clean_review_topic, parse_review_queries


def _paper(
    title: str,
    abstract: str,
    *,
    source: str,
    doi: str = "",
) -> PaperRecord:
    return PaperRecord(
        title=title,
        year=2024,
        abstract=abstract,
        authors=["Researcher"],
        url=f"https://doi.org/{doi}" if doi else "",
        venue="Water Research",
        citation_count=12,
        sources=[source],
        identifiers={"doi": doi} if doi else {},
    )


def test_review_topic_and_query_protocol_are_cleaned() -> None:
    objective = "/review 写一个当前海绵城市相关的综述"
    brief = "Q1: 海绵城市\nQ2: sponge city\nQ3: green stormwater infrastructure review"

    assert clean_review_topic(objective) == "海绵城市"
    assert parse_review_queries(objective, brief) == [
        "海绵城市",
        "sponge city",
        "green stormwater infrastructure review",
    ]


def test_multi_query_search_filters_noise_merges_doi_and_survives_provider_failure(monkeypatch) -> None:
    service = ScholarSearchService(timeout_seconds=0.1)
    arxiv_calls = 0

    async def openalex(_client, query, _limit):
        if query == "sponge city":
            return [
                _paper(
                    "Sponge city planning for urban stormwater",
                    "Green infrastructure and runoff management.",
                    source="OpenAlex",
                    doi="10.1000/sponge",
                ),
                _paper(
                    "Contemporary Chinese film and ritual aesthetics",
                    "A study of literature and cinema.",
                    source="OpenAlex",
                ),
                _paper(
                    "Urban cultural development in contemporary cities",
                    "A city policy study without stormwater content.",
                    source="OpenAlex",
                ),
            ]
        return [
            _paper(
                "Urban runoff management through sponge-city systems",
                "Sponge city green infrastructure for stormwater control.",
                source="OpenAlex",
                doi="https://doi.org/10.1000/SPONGE",
            )
        ]

    async def semantic_scholar(_client, query, _limit):
        return [
            _paper(
                f"{query.title()} evidence synthesis",
                f"Review of {query} methods, data, and limitations.",
                source="Semantic Scholar",
                doi=f"10.1000/{query.replace(' ', '-')}",
            )
        ]

    async def arxiv(_client, _query, _limit):
        nonlocal arxiv_calls
        arxiv_calls += 1
        request = httpx.Request("GET", "https://export.arxiv.org/api/query")
        response = httpx.Response(503, request=request)
        raise httpx.HTTPStatusError("unavailable", request=request, response=response)

    monkeypatch.setattr(service, "_search_openalex", openalex)
    monkeypatch.setattr(service, "_search_semantic_scholar", semantic_scholar)
    monkeypatch.setattr(service, "_search_arxiv", arxiv)

    bundle = asyncio.run(
        service.search_bundle(
            "sponge city",
            queries=["sponge city", "green stormwater infrastructure"],
            per_source_limit=8,
        )
    )

    assert arxiv_calls == 4
    assert bundle.provider_status["arxiv"] == "error (2/2 queries failed)"
    assert bundle.excluded_count == 2
    assert all("film" not in paper.title.casefold() for paper in bundle.papers)
    assert all("cultural development" not in paper.title.casefold() for paper in bundle.papers)
    assert len([paper for paper in bundle.papers if paper.identifiers.get("doi", "").casefold().endswith("sponge")]) == 1
    assert [paper.paper_id for paper in bundle.papers] == [
        f"P{index:03d}" for index in range(1, len(bundle.papers) + 1)
    ]
    assert all(paper.verification_status == "traceable_identifier" for paper in bundle.papers)


def test_identifier_and_title_bridge_collapses_existing_duplicate_groups(monkeypatch) -> None:
    service = ScholarSearchService(timeout_seconds=0.1)

    async def openalex(_client, _query, _limit):
        return [
            _paper("Sponge city systems", "Sponge city stormwater evidence.", source="OpenAlex", doi="10.1/a"),
            _paper("Urban stormwater systems", "Sponge city stormwater evidence.", source="OpenAlex", doi="10.1/b"),
        ]

    async def semantic_scholar(_client, _query, _limit):
        return [
            _paper("Urban stormwater systems", "Sponge city stormwater evidence.", source="Semantic Scholar", doi="10.1/a"),
        ]

    async def arxiv(_client, _query, _limit):
        return []

    monkeypatch.setattr(service, "_search_openalex", openalex)
    monkeypatch.setattr(service, "_search_semantic_scholar", semantic_scholar)
    monkeypatch.setattr(service, "_search_arxiv", arxiv)

    bundle = asyncio.run(service.search_bundle("sponge city", per_source_limit=8))

    assert len(bundle.papers) == 1
    assert set(bundle.papers[0].sources) == {"OpenAlex", "Semantic Scholar"}

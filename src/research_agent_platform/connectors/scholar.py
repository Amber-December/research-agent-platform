from __future__ import annotations

import asyncio
import json
import re
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field

import httpx


OPENALEX_URL = "https://api.openalex.org/works"
SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
ARXIV_URL = "https://export.arxiv.org/api/query"
WOS_DEFAULT_BASE_URL = "https://api.clarivate.com/apis/wos-starter/v1"


@dataclass
class PaperRecord:
    title: str
    year: int | None
    abstract: str
    authors: list[str]
    url: str
    venue: str
    citation_count: int | None
    sources: list[str] = field(default_factory=list)
    identifiers: dict[str, str] = field(default_factory=dict)
    paper_id: str = ""
    relevance_score: float = 0.0
    matched_queries: list[str] = field(default_factory=list)
    verification_status: str = "source_metadata"
    pdf_url: str = ""
    download_status: str = "not_attempted"
    downloaded_path: str = ""
    download_error: str = ""

    def merge(self, other: "PaperRecord") -> None:
        if not self.abstract and other.abstract:
            self.abstract = other.abstract
        if not self.url and other.url:
            self.url = other.url
        if not self.pdf_url and other.pdf_url:
            self.pdf_url = other.pdf_url
        if not self.venue and other.venue:
            self.venue = other.venue
        if self.year is None and other.year is not None:
            self.year = other.year
        if self.citation_count is None and other.citation_count is not None:
            self.citation_count = other.citation_count
        if len(other.authors) > len(self.authors):
            self.authors = other.authors
        for source in other.sources:
            if source not in self.sources:
                self.sources.append(source)
        self.identifiers.update({k: v for k, v in other.identifiers.items() if v})
        for query in other.matched_queries:
            if query not in self.matched_queries:
                self.matched_queries.append(query)
        self.relevance_score = max(self.relevance_score, other.relevance_score)
        if other.download_status == "downloaded":
            self.download_status = other.download_status
            self.downloaded_path = other.downloaded_path
            self.download_error = other.download_error
        elif self.download_status == "not_attempted" and other.download_status != "not_attempted":
            self.download_status = other.download_status
            self.downloaded_path = other.downloaded_path
            self.download_error = other.download_error


@dataclass
class LiteratureBundle:
    query: str
    papers: list[PaperRecord]
    provider_status: dict[str, str]
    queries: list[str] = field(default_factory=list)
    excluded_count: int = 0
    quality: dict[str, object] = field(default_factory=dict)

    def to_markdown(self) -> str:
        lines = [
            "# Literature Search Bundle",
            "",
            f"- Query: {self.query}",
            f"- Expanded queries: {', '.join(self.queries) or self.query}",
            f"- Retrieval quality: {self.quality.get('status', 'unknown')}",
            f"- Relevant papers retained: {len(self.papers)}",
            f"- Irrelevant candidates excluded: {self.excluded_count}",
            "",
            "## Provider Status",
        ]
        for provider, status in self.provider_status.items():
            lines.append(f"- {provider}: {status}")
        lines.extend(["", "## Aggregated Papers"])
        if not self.papers:
            lines.append("")
            lines.append("_No papers retrieved._")
            return "\n".join(lines) + "\n"
        for index, paper in enumerate(self.papers, start=1):
            title = paper.title or "Untitled"
            year = f" ({paper.year})" if paper.year else ""
            lines.extend(
                [
                    "",
                    f"### [{paper.paper_id or f'P{index:03d}'}] {title}{year}",
                    f"- Sources: {', '.join(paper.sources) or 'unknown'}",
                    f"- Matched queries: {', '.join(paper.matched_queries) or 'unknown'}",
                    f"- Relevance score: {paper.relevance_score:.3f}",
                    f"- Traceability: {paper.verification_status}",
                    f"- Authors: {', '.join(paper.authors[:8]) or 'unknown'}",
                    f"- Venue: {paper.venue or 'unknown'}",
                    f"- Citations: {paper.citation_count if paper.citation_count is not None else 'unknown'}",
                    f"- URL: {paper.url or 'unknown'}",
                    f"- Public PDF: {paper.pdf_url or 'not advertised'}",
                    f"- Download: {paper.download_status}"
                    + (f" (`{paper.downloaded_path}`)" if paper.downloaded_path else ""),
                ]
            )
            if paper.download_error:
                lines.append(f"- Download note: {paper.download_error}")
            if paper.identifiers:
                identifiers = ", ".join(f"{key}={value}" for key, value in paper.identifiers.items())
                lines.append(f"- Identifiers: {identifiers}")
            if paper.abstract:
                lines.extend(["", "Summary:", paper.abstract.strip()])
        return "\n".join(lines) + "\n"

    def to_json(self) -> str:
        payload = {
            "query": self.query,
            "queries": self.queries,
            "provider_status": self.provider_status,
            "excluded_count": self.excluded_count,
            "quality": self.quality,
            "papers": [asdict(item) for item in self.papers],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def prompt_excerpt(self, *, limit: int = 4500) -> str:
        lines = ["# Admitted Evidence Records"]
        for index, paper in enumerate(self.papers, start=1):
            stable_id = paper.paper_id or f"P{index:03d}"
            heading = f"### [{stable_id}]"
            if paper.title:
                heading += f" {paper.title}"
            if paper.year:
                heading += f" ({paper.year})"
            lines.extend(["", heading])
            if paper.authors:
                lines.append(f"- Authors: {', '.join(paper.authors[:8])}")
            if paper.venue:
                lines.append(f"- Venue: {paper.venue}")
            if paper.url:
                lines.append(f"- Source URL: {paper.url}")
            if paper.identifiers:
                identifiers = ", ".join(f"{key}={value}" for key, value in paper.identifiers.items())
                lines.append(f"- Stable identifiers: {identifiers}")
            if paper.abstract:
                lines.extend(["", "Admitted evidence summary:", paper.abstract.strip()])
        return ("\n".join(lines) + "\n")[:limit]


class ScholarSearchService:
    def __init__(
        self,
        timeout_seconds: float = 30.0,
        *,
        wos_api_base_url: str = WOS_DEFAULT_BASE_URL,
        wos_api_key: str = "",
        wos_default_db: str = "WOS",
        cnki_search_endpoint: str = "",
        cnki_search_method: str = "GET",
        cnki_api_key: str = "",
        cnki_auth_header: str = "X-ApiKey",
        cnki_auth_scheme: str = "",
        minimum_for_synthesis: int = 10,
        recommended_for_review: int = 15,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.wos_api_base_url = wos_api_base_url.rstrip("/")
        self.wos_api_key = wos_api_key.strip()
        self.wos_default_db = wos_default_db.strip() or "WOS"
        self.cnki_search_endpoint = cnki_search_endpoint.strip()
        self.cnki_search_method = cnki_search_method.strip().upper() or "GET"
        self.cnki_api_key = cnki_api_key.strip()
        self.cnki_auth_header = cnki_auth_header.strip() or "X-ApiKey"
        self.cnki_auth_scheme = cnki_auth_scheme.strip()
        self.minimum_for_synthesis = max(1, minimum_for_synthesis)
        self.recommended_for_review = max(self.minimum_for_synthesis, recommended_for_review)

    async def search_bundle(
        self,
        query: str,
        *,
        queries: list[str] | None = None,
        per_source_limit: int = 8,
        max_papers: int = 24,
    ) -> LiteratureBundle:
        provider_status: dict[str, str] = {}
        merged: dict[str, PaperRecord] = {}
        canonical_by_alias: dict[str, str] = {}
        planned_queries = _deduplicate_queries(queries or [query])[:6]
        provider_counts: dict[str, int] = {}
        provider_errors: dict[str, int] = {}

        async with httpx.AsyncClient(timeout=self.timeout_seconds, headers={"User-Agent": "research-agent-platform"}) as client:
            providers = [
                ("openalex", self._search_openalex),
                ("semantic_scholar", self._search_semantic_scholar),
                ("arxiv", self._search_arxiv),
            ]
            if self.wos_api_key:
                providers.append(("wos", self._search_wos))
            else:
                provider_status["wos"] = "disabled: missing WOS_API_KEY"
            if self.cnki_search_endpoint:
                providers.append(("cnki", self._search_cnki))
            else:
                provider_status["cnki"] = "disabled: missing CNKI_SEARCH_ENDPOINT"

            runs = await asyncio.gather(
                *(
                    self._safe_fetch(name, fetch, client, planned_query, per_source_limit)
                    for planned_query in planned_queries
                    for name, fetch in providers
                )
            )

        for name, planned_query, records, error in runs:
            if error:
                provider_errors[name] = provider_errors.get(name, 0) + 1
            else:
                provider_counts[name] = provider_counts.get(name, 0) + len(records)
            for record in records:
                record.matched_queries.append(planned_query)
                aliases = _paper_aliases(record)
                if not aliases:
                    continue
                existing_keys = list(
                    dict.fromkeys(canonical_by_alias[alias] for alias in aliases if alias in canonical_by_alias)
                )
                if existing_keys:
                    existing_key = existing_keys[0]
                    for duplicate_key in existing_keys[1:]:
                        merged[existing_key].merge(merged.pop(duplicate_key))
                        for alias, canonical_key in list(canonical_by_alias.items()):
                            if canonical_key == duplicate_key:
                                canonical_by_alias[alias] = existing_key
                    merged[existing_key].merge(record)
                    for alias in aliases:
                        canonical_by_alias[alias] = existing_key
                else:
                    canonical_key = aliases[0]
                    merged[canonical_key] = record
                    for alias in aliases:
                        canonical_by_alias[alias] = canonical_key

        for name, _ in providers:
            successes = len(planned_queries) - provider_errors.get(name, 0)
            provider_status[name] = (
                f"ok ({provider_counts.get(name, 0)} records across {successes}/{len(planned_queries)} queries)"
                if successes
                else f"error ({provider_errors.get(name, 0)}/{len(planned_queries)} queries failed)"
            )

        candidates = list(merged.values())
        for record in candidates:
            record.relevance_score = _paper_relevance(record, planned_queries)
            record.verification_status = (
                "traceable_identifier" if record.identifiers or record.url else "unverified_metadata"
            )
        relevant = [record for record in candidates if record.relevance_score >= 0.34]
        papers = sorted(
            relevant,
            key=lambda item: (
                -item.relevance_score,
                -(item.citation_count or 0),
                -(item.year or 0),
                item.title.lower(),
            ),
        )
        papers = papers[:max_papers]
        for index, paper in enumerate(papers, start=1):
            paper.paper_id = f"P{index:03d}"
        quality_status = (
            "adequate"
            if len(papers) >= self.recommended_for_review
            else "marginal"
            if len(papers) >= self.minimum_for_synthesis
            else "insufficient"
        )
        quality = {
            "status": quality_status,
            "candidate_count": len(candidates),
            "eligible_count": len(relevant),
            "relevant_count": len(papers),
            "truncated_count": max(0, len(relevant) - len(papers)),
            "minimum_for_synthesis": self.minimum_for_synthesis,
            "recommended_for_review": self.recommended_for_review,
            "traceable_count": sum(p.verification_status == "traceable_identifier" for p in papers),
            "provider_success_count": sum(status.startswith("ok") for status in provider_status.values()),
        }
        return LiteratureBundle(
            query=query,
            queries=planned_queries,
            papers=papers,
            provider_status=provider_status,
            excluded_count=max(0, len(candidates) - len(relevant)),
            quality=quality,
        )

    async def _safe_fetch(self, name: str, fn, client: httpx.AsyncClient, query: str, limit: int):
        last_error = ""
        for attempt in range(2):
            try:
                return name, query, await fn(client, query, limit), ""
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                last_error = exc.__class__.__name__
                if attempt == 0:
                    await asyncio.sleep(0.35)
            except Exception as exc:
                return name, query, [], exc.__class__.__name__
        return name, query, [], last_error

    async def _search_openalex(self, client: httpx.AsyncClient, query: str, limit: int) -> list[PaperRecord]:
        response = await client.get(
            OPENALEX_URL,
            params={
                "search": query,
                "per-page": limit,
                "sort": "relevance_score:desc",
                "mailto": "research-agent@example.com",
            },
        )
        response.raise_for_status()
        data = response.json().get("results", [])
        records: list[PaperRecord] = []
        for item in data:
            authors = [
                author.get("author", {}).get("display_name", "")
                for author in item.get("authorships", [])
                if author.get("author", {}).get("display_name")
            ]
            primary_location = item.get("primary_location") if isinstance(item.get("primary_location"), dict) else {}
            pdf_url = _first_public_pdf_url(
                item.get("best_oa_location"),
                primary_location,
                *(item.get("locations") or []) if isinstance(item.get("locations"), list) else (),
            )
            url = (
                primary_location.get("landing_page_url")
                or pdf_url
                or item.get("doi")
                or item.get("id", "")
            )
            venue = item.get("primary_location", {}).get("source", {}).get("display_name", "")
            abstract = _decode_openalex_abstract(item.get("abstract_inverted_index") or {})
            identifiers = {"openalex": item.get("id", ""), "doi": item.get("doi", "")}
            records.append(
                PaperRecord(
                    title=str(item.get("display_name", "")).strip(),
                    year=item.get("publication_year"),
                    abstract=abstract,
                    authors=authors[:10],
                    url=str(url or ""),
                    venue=str(venue or ""),
                    citation_count=item.get("cited_by_count"),
                    sources=["OpenAlex"],
                    identifiers={key: value for key, value in identifiers.items() if value},
                    pdf_url=pdf_url,
                )
            )
        return records

    async def _search_semantic_scholar(self, client: httpx.AsyncClient, query: str, limit: int) -> list[PaperRecord]:
        response = await client.get(
            SEMANTIC_SCHOLAR_URL,
            params={
                "query": query,
                "limit": limit,
                "fields": "title,abstract,year,authors,url,venue,citationCount,externalIds,openAccessPdf",
            },
        )
        response.raise_for_status()
        data = response.json().get("data", [])
        records: list[PaperRecord] = []
        for item in data:
            authors = [author.get("name", "") for author in item.get("authors", []) if author.get("name")]
            identifiers = item.get("externalIds") or {}
            open_access = item.get("openAccessPdf") if isinstance(item.get("openAccessPdf"), dict) else {}
            records.append(
                PaperRecord(
                    title=str(item.get("title", "")).strip(),
                    year=item.get("year"),
                    abstract=str(item.get("abstract", "") or "").strip(),
                    authors=authors[:10],
                    url=str(item.get("url", "") or ""),
                    venue=str(item.get("venue", "") or ""),
                    citation_count=item.get("citationCount"),
                    sources=["Semantic Scholar"],
                    identifiers={str(key): str(value) for key, value in identifiers.items() if value},
                    pdf_url=str(open_access.get("url", "") or ""),
                )
            )
        return records

    async def _search_arxiv(self, client: httpx.AsyncClient, query: str, limit: int) -> list[PaperRecord]:
        response = await client.get(
            ARXIV_URL,
            params={
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": limit,
            },
        )
        response.raise_for_status()
        root = ET.fromstring(response.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        records: list[PaperRecord] = []
        for entry in root.findall("atom:entry", ns):
            title = _xml_text(entry.find("atom:title", ns))
            summary = _xml_text(entry.find("atom:summary", ns))
            url = _xml_text(entry.find("atom:id", ns))
            published = _xml_text(entry.find("atom:published", ns))
            year = int(published[:4]) if published[:4].isdigit() else None
            authors = [_xml_text(author.find("atom:name", ns)) for author in entry.findall("atom:author", ns)]
            identifiers = {}
            if url:
                identifiers["arxiv"] = url.rstrip("/").split("/")[-1]
            pdf_url = ""
            for link in entry.findall("atom:link", ns):
                if link.attrib.get("type") == "application/pdf" or link.attrib.get("title", "").casefold() == "pdf":
                    pdf_url = link.attrib.get("href", "")
                    break
            if not pdf_url and identifiers.get("arxiv"):
                pdf_url = f"https://arxiv.org/pdf/{identifiers['arxiv']}.pdf"
            records.append(
                PaperRecord(
                    title=title,
                    year=year,
                    abstract=summary,
                    authors=[author for author in authors if author][:10],
                    url=url,
                    venue="arXiv",
                    citation_count=None,
                    sources=["arXiv"],
                    identifiers=identifiers,
                    pdf_url=pdf_url,
                )
            )
        return records

    async def _search_wos(self, client: httpx.AsyncClient, query: str, limit: int) -> list[PaperRecord]:
        response = await client.get(
            f"{self.wos_api_base_url}/documents",
            params={
                "db": self.wos_default_db,
                "q": self._wos_query(query),
                "limit": limit,
            },
            headers={"X-ApiKey": self.wos_api_key},
        )
        response.raise_for_status()
        payload = response.json()
        records: list[PaperRecord] = []
        for item in self._extract_records(payload):
            title = self._first_text(
                item.get("title"),
                item.get("sourceTitle"),
                self._first_nested_value(item.get("titles"), "value"),
                self._first_nested_value(item.get("titles"), "display"),
            )
            if not title:
                continue
            source = item.get("source") if isinstance(item.get("source"), dict) else {}
            year = self._first_int(
                item.get("publishedYear"),
                source.get("publishYear"),
                item.get("year"),
            )
            authors = self._extract_authors(item)
            url = (
                item.get("url")
                or item.get("links", {}).get("record")
                or item.get("links", {}).get("self")
                or source.get("url")
                or ""
            )
            venue = (
                item.get("sourceTitle")
                or source.get("sourceTitle")
                or source.get("title")
                or ""
            )
            citation_count = self._first_int(
                item.get("citations"),
                item.get("citationCount"),
                item.get("stats", {}).get("citations"),
            )
            identifiers = self._normalize_identifiers(item)
            pdf_url = _first_public_pdf_url(item, item.get("links"))
            records.append(
                PaperRecord(
                    title=title,
                    year=year,
                    abstract=str(item.get("abstract", "") or "").strip(),
                    authors=authors[:10],
                    url=str(url or ""),
                    venue=str(venue or ""),
                    citation_count=citation_count,
                    sources=["Web of Science"],
                    identifiers=identifiers,
                    pdf_url=pdf_url,
                )
            )
        return records

    async def _search_cnki(self, client: httpx.AsyncClient, query: str, limit: int) -> list[PaperRecord]:
        request_kwargs: dict = {}
        if self.cnki_api_key:
            value = self.cnki_api_key
            if self.cnki_auth_scheme:
                value = f"{self.cnki_auth_scheme} {value}"
            request_kwargs["headers"] = {self.cnki_auth_header: value}

        method = self.cnki_search_method.upper()
        if method == "POST":
            response = await client.post(
                self.cnki_search_endpoint,
                json={"query": query, "limit": limit},
                **request_kwargs,
            )
        else:
            response = await client.get(
                self.cnki_search_endpoint,
                params={"query": query, "limit": limit},
                **request_kwargs,
            )
        response.raise_for_status()
        payload = response.json()
        records: list[PaperRecord] = []
        for item in self._extract_records(payload):
            title = str(item.get("title", "") or item.get("name", "") or "").strip()
            if not title:
                continue
            year = self._first_int(item.get("year"), item.get("publishedYear"))
            authors = self._normalize_string_list(item.get("authors") or item.get("author"))
            url = item.get("url") or item.get("link") or item.get("recordUrl") or ""
            venue = item.get("journal") or item.get("source") or item.get("venue") or ""
            citation_count = self._first_int(item.get("citationCount"), item.get("citations"))
            abstract = str(item.get("abstract", "") or item.get("summary", "") or "").strip()
            identifiers = self._normalize_identifiers(item)
            pdf_url = _first_public_pdf_url(item, item.get("links"))
            records.append(
                PaperRecord(
                    title=title,
                    year=year,
                    abstract=abstract,
                    authors=authors[:10],
                    url=str(url or ""),
                    venue=str(venue or ""),
                    citation_count=citation_count,
                    sources=["CNKI"],
                    identifiers=identifiers,
                    pdf_url=pdf_url,
                )
            )
        return records

    def _normalize_title(self, title: str) -> str:
        normalized = " ".join(title.lower().split())
        return normalized[:220]

    def _extract_records(self, payload: object) -> list[dict]:
        if isinstance(payload, dict):
            for key in ("items", "papers", "records", "data", "hits", "result", "results"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
                if isinstance(value, dict):
                    nested = self._extract_records(value)
                    if nested:
                        return nested
            return []
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        return []

    def _extract_authors(self, item: dict) -> list[str]:
        candidates = item.get("authors") or item.get("author") or item.get("creators") or []
        if isinstance(candidates, list):
            return self._normalize_string_list(candidates)
        if isinstance(candidates, dict):
            nested = candidates.get("items") or candidates.get("data") or []
            if isinstance(nested, list):
                return self._normalize_string_list(nested)
        return []

    def _normalize_string_list(self, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        result: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                result.append(item.strip())
            elif isinstance(item, dict):
                candidate = (
                    item.get("name")
                    or item.get("fullName")
                    or item.get("displayName")
                    or item.get("authorName")
                )
                if candidate:
                    result.append(str(candidate).strip())
        return result

    def _first_text(self, *values: object) -> str:
        for value in values:
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    def _first_nested_value(self, value: object, key: str) -> str:
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    candidate = item.get(key)
                    if isinstance(candidate, str) and candidate.strip():
                        return candidate.strip()
        if isinstance(value, dict):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        return ""

    def _normalize_identifiers(self, item: dict) -> dict[str, str]:
        identifiers: dict[str, str] = {}
        for key in ("doi", "issn", "eissn", "pmid", "uid", "wos", "cnki", "id"):
            value = item.get(key)
            if value:
                identifiers[key] = str(value)
        external = item.get("externalIds")
        if isinstance(external, dict):
            for key, value in external.items():
                if value:
                    identifiers[str(key)] = str(value)
        return identifiers

    def _first_int(self, *values: object) -> int | None:
        for value in values:
            if value is None:
                continue
            if isinstance(value, int):
                return value
            if isinstance(value, float):
                return int(value)
            if isinstance(value, str) and value.strip().isdigit():
                return int(value.strip())
        return None

    def _wos_query(self, query: str) -> str:
        cleaned = " ".join(query.split()).replace('"', '\\"')
        return f"TS=({cleaned})"


def _decode_openalex_abstract(inverted_index: dict[str, list[int]]) -> str:
    if not inverted_index:
        return ""
    positions: dict[int, str] = {}
    for token, slots in inverted_index.items():
        for slot in slots:
            positions[slot] = token
    return " ".join(token for _, token in sorted(positions.items())).strip()


def _first_public_pdf_url(*locations: object) -> str:
    for location in locations:
        if not isinstance(location, dict):
            continue
        candidates = [
            location.get("pdf_url"),
            location.get("pdfUrl"),
            location.get("fullTextUrl"),
            location.get("download_url"),
            location.get("downloadUrl"),
        ]
        links = location.get("links")
        if isinstance(links, dict):
            candidates.extend(
                [links.get("pdf"), links.get("fullText"), links.get("download")]
            )
        for candidate in candidates:
            if isinstance(candidate, str) and _looks_like_pdf_url(candidate):
                return candidate.strip()
    return ""


def _looks_like_pdf_url(value: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(value.strip())
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    path = parsed.path.casefold()
    query = parsed.query.casefold()
    return path.endswith(".pdf") or "/pdf/" in path or "format=pdf" in query or "type=pdf" in query


def _deduplicate_queries(queries: list[str]) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for query in queries:
        cleaned = " ".join(query.split()).strip(" ,，。;；")
        key = cleaned.casefold()
        if cleaned and key not in seen:
            results.append(cleaned)
            seen.add(key)
    return results


def _paper_aliases(record: PaperRecord) -> list[str]:
    aliases: list[str] = []
    normalized_identifiers = {
        str(key).casefold(): str(value).strip().casefold()
        for key, value in record.identifiers.items()
        if value
    }
    doi = normalized_identifiers.get("doi", "")
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi)
    if doi:
        aliases.append(f"doi:{doi}")
    arxiv = normalized_identifiers.get("arxiv", "")
    arxiv = re.sub(r"^https?://arxiv\.org/(?:abs|pdf)/", "", arxiv).removesuffix(".pdf")
    if arxiv:
        aliases.append(f"arxiv:{arxiv}")
    normalized_title = " ".join(record.title.lower().split())[:220]
    if normalized_title:
        aliases.append(f"title:{normalized_title}")
    return _deduplicate_queries(aliases)


def _paper_relevance(record: PaperRecord, queries: list[str]) -> float:
    text = f"{record.title} {record.abstract} {record.venue}".casefold()
    title = record.title.casefold()
    query_scores: list[float] = []
    for query in queries:
        terms = _query_terms(query)
        if not terms:
            continue
        matched = sum(term in text for term in terms)
        title_matched = sum(term in title for term in terms)
        phrase_match = query.casefold() in text
        if len(terms) > 1 and matched < 2 and not phrase_match:
            query_scores.append(0.0)
            continue
        phrase_bonus = 0.35 if phrase_match else 0.0
        query_scores.append(min(1.0, matched / len(terms) + title_matched / len(terms) * 0.35 + phrase_bonus))
    if not query_scores:
        return 0.0
    multi_query_bonus = min(0.12, max(0, len(record.matched_queries) - 1) * 0.03)
    metadata_bonus = 0.04 if record.identifiers or record.url else 0.0
    return round(min(1.0, max(query_scores) + multi_query_bonus + metadata_bonus), 3)


def _query_terms(query: str) -> list[str]:
    stopwords = {
        "a", "an", "and", "article", "current", "for", "in", "of", "on", "or", "review",
        "survey", "the", "to", "write", "一个", "与", "写", "写一份", "当前", "相关", "的", "综述",
        "研究", "进展", "论文", "文献", "请", "帮我",
    }
    english = re.findall(r"[a-z][a-z0-9-]{2,}", query.casefold())
    chinese_chunks = re.findall(r"[\u4e00-\u9fff]{2,}", query)
    chinese: list[str] = []
    for chunk in chinese_chunks:
        cleaned = chunk
        for token in sorted((word for word in stopwords if any("\u4e00" <= char <= "\u9fff" for char in word)), key=len, reverse=True):
            cleaned = cleaned.replace(token, " ")
        chinese.extend(part for part in cleaned.split() if len(part) >= 2)
    return _deduplicate_queries([term for term in [*english, *chinese] if term not in stopwords])


def _xml_text(element: ET.Element | None) -> str:
    if element is None or element.text is None:
        return ""
    return urllib.parse.unquote_plus(element.text.strip())

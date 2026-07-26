from __future__ import annotations

import json
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field

import httpx


OPENALEX_URL = "https://api.openalex.org/works"
SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
ARXIV_URL = "http://export.arxiv.org/api/query"
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

    def merge(self, other: "PaperRecord") -> None:
        if not self.abstract and other.abstract:
            self.abstract = other.abstract
        if not self.url and other.url:
            self.url = other.url
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


@dataclass
class LiteratureBundle:
    query: str
    papers: list[PaperRecord]
    provider_status: dict[str, str]

    def to_markdown(self) -> str:
        lines = [
            "# Literature Search Bundle",
            "",
            f"- Query: {self.query}",
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
                    f"### {index}. {title}{year}",
                    f"- Sources: {', '.join(paper.sources) or 'unknown'}",
                    f"- Authors: {', '.join(paper.authors[:8]) or 'unknown'}",
                    f"- Venue: {paper.venue or 'unknown'}",
                    f"- Citations: {paper.citation_count if paper.citation_count is not None else 'unknown'}",
                    f"- URL: {paper.url or 'unknown'}",
                ]
            )
            if paper.identifiers:
                identifiers = ", ".join(f"{key}={value}" for key, value in paper.identifiers.items())
                lines.append(f"- Identifiers: {identifiers}")
            if paper.abstract:
                lines.extend(["", "Summary:", paper.abstract.strip()])
        return "\n".join(lines) + "\n"

    def to_json(self) -> str:
        payload = {
            "query": self.query,
            "provider_status": self.provider_status,
            "papers": [asdict(item) for item in self.papers],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def prompt_excerpt(self, *, limit: int = 4500) -> str:
        return self.to_markdown()[:limit]


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

    async def search_bundle(self, query: str, *, per_source_limit: int = 4) -> LiteratureBundle:
        provider_status: dict[str, str] = {}
        merged: dict[str, PaperRecord] = {}

        async with httpx.AsyncClient(timeout=self.timeout_seconds, headers={"User-Agent": "research-agent-platform"}) as client:
            openalex_records = await self._safe_fetch(
                provider_status, "openalex", self._search_openalex, client, query, per_source_limit
            )
            semantic_records = await self._safe_fetch(
                provider_status, "semantic_scholar", self._search_semantic_scholar, client, query, per_source_limit
            )
            arxiv_records = await self._safe_fetch(
                provider_status, "arxiv", self._search_arxiv, client, query, per_source_limit
            )
            if self.wos_api_key:
                wos_records = await self._safe_fetch(
                    provider_status, "wos", self._search_wos, client, query, per_source_limit
                )
            else:
                provider_status["wos"] = "disabled: missing WOS_API_KEY"
                wos_records = []
            if self.cnki_search_endpoint:
                cnki_records = await self._safe_fetch(
                    provider_status, "cnki", self._search_cnki, client, query, per_source_limit
                )
            else:
                provider_status["cnki"] = "disabled: missing CNKI_SEARCH_ENDPOINT"
                cnki_records = []

        for group in (openalex_records, semantic_records, arxiv_records, wos_records, cnki_records):
            for record in group:
                key = self._normalize_title(record.title)
                if not key:
                    continue
                if key in merged:
                    merged[key].merge(record)
                else:
                    merged[key] = record

        papers = sorted(
            merged.values(),
            key=lambda item: (
                -(item.citation_count or 0),
                -(item.year or 0),
                item.title.lower(),
            ),
        )
        return LiteratureBundle(query=query, papers=papers[:8], provider_status=provider_status)

    async def _safe_fetch(self, status: dict[str, str], name: str, fn, client: httpx.AsyncClient, query: str, limit: int) -> list[PaperRecord]:
        try:
            records = await fn(client, query, limit)
            status[name] = f"ok ({len(records)} records)"
            return records
        except Exception as exc:
            status[name] = f"error: {exc.__class__.__name__}"
            return []

    async def _search_openalex(self, client: httpx.AsyncClient, query: str, limit: int) -> list[PaperRecord]:
        response = await client.get(
            OPENALEX_URL,
            params={
                "search": query,
                "per-page": limit,
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
            url = (
                item.get("primary_location", {}).get("landing_page_url")
                or item.get("primary_location", {}).get("pdf_url")
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
                )
            )
        return records

    async def _search_semantic_scholar(self, client: httpx.AsyncClient, query: str, limit: int) -> list[PaperRecord]:
        response = await client.get(
            SEMANTIC_SCHOLAR_URL,
            params={
                "query": query,
                "limit": limit,
                "fields": "title,abstract,year,authors,url,venue,citationCount,externalIds",
            },
        )
        response.raise_for_status()
        data = response.json().get("data", [])
        records: list[PaperRecord] = []
        for item in data:
            authors = [author.get("name", "") for author in item.get("authors", []) if author.get("name")]
            identifiers = item.get("externalIds") or {}
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


def _xml_text(element: ET.Element | None) -> str:
    if element is None or element.text is None:
        return ""
    return urllib.parse.unquote_plus(element.text.strip())

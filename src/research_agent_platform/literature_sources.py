from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .models import DownloadSourceConfig, UploadBatchRecord

PDF_EXTENSIONS = {".pdf"}
BIB_EXTENSIONS = {".bib", ".enw", ".nbib", ".ris"}
TEXT_EXTENSIONS = {".md", ".rst", ".txt", ".tex", ".csv", ".tsv", ".json", ".xml", ".html", ".htm"}
WORKSPACE_ORDER = ("bib", "paper", "plan", "idea", "Content", "wiki", "logs")


@dataclass(frozen=True)
class DownloadSource:
    source_path: str
    source_type: str
    title: str = ""
    doi: str = ""
    url: str = ""
    query: str = ""


def discover_download_sources(workspace_root: Path, source_refs: Iterable[str]) -> list[DownloadSource]:
    sources: list[DownloadSource] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for relative in source_refs:
        path = (workspace_root / relative).resolve()
        if not _is_within_root(workspace_root, path) or not path.exists() or not path.is_file():
            continue
        for source in _parse_source_file(path, workspace_root):
            key = (source.source_path, source.source_type, source.title, source.doi, source.url)
            if key not in seen:
                seen.add(key)
                sources.append(source)
    return sources


def extract_download_queries(sources: Iterable[DownloadSource]) -> list[str]:
    queries: list[str] = []
    seen: set[str] = set()
    for source in sources:
        candidates = [
            source.query,
            source.title,
            source.doi,
            source.url,
        ]
        for candidate in candidates:
            cleaned = _clean_query(candidate)
            if not cleaned:
                continue
            key = cleaned.casefold()
            if key not in seen:
                seen.add(key)
                queries.append(cleaned)
    return queries


def download_targets_markdown(sources: Iterable[DownloadSource]) -> str:
    lines = ["# Literature Download Sources", ""]
    empty = True
    for source in sources:
        empty = False
        lines.extend(
            [
                f"- `{source.source_path}`",
                f"  - Type: {source.source_type}",
            ]
        )
        if source.title:
            lines.append(f"  - Title: {source.title}")
        if source.doi:
            lines.append(f"  - DOI: {source.doi}")
        if source.url:
            lines.append(f"  - URL: {source.url}")
        if source.query:
            lines.append(f"  - Query: {source.query}")
    if empty:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def resolve_download_source_config(
    objective: str,
    workspace_root: Path,
    upload_batches: Iterable[UploadBatchRecord] = (),
    *,
    source_limit: int = 50,
) -> DownloadSourceConfig:
    requested_scope = _requested_source_scope(objective)
    explicit_refs = _extract_explicit_refs(objective, workspace_root)
    batches = list(upload_batches)
    latest_batch = batches[-1] if batches else None
    latest_refs = _valid_refs(
        workspace_root,
        latest_batch.relative_paths if latest_batch else (),
    )[:source_limit]
    workspace_refs = select_download_workspace_sources(workspace_root, limit=source_limit)

    if explicit_refs:
        source_refs = _expand_refs(workspace_root, explicit_refs, source_limit)
        sources = discover_download_sources(workspace_root, source_refs)
        return DownloadSourceConfig(
            requested_scope=requested_scope,
            resolved_scope="selected",
            source_refs=source_refs,
            query_terms=extract_download_queries(sources),
            upload_batch_id=latest_batch.upload_batch_id if latest_batch else "",
            selection_reason="用户在 /download 指令中明确指定了下载源。",
        )
    if requested_scope == "attachments":
        sources = discover_download_sources(workspace_root, latest_refs)
        return DownloadSourceConfig(
            requested_scope=requested_scope,
            resolved_scope="attachments",
            source_refs=latest_refs,
            query_terms=extract_download_queries(sources),
            upload_batch_id=latest_batch.upload_batch_id if latest_batch else "",
            selection_reason="用户要求仅使用最近一次上传批次。",
        )
    if requested_scope == "session":
        session_refs = _deduplicate(
            ref
            for batch in batches
            for ref in _valid_refs(workspace_root, batch.relative_paths)
        )[:source_limit]
        sources = discover_download_sources(workspace_root, session_refs)
        return DownloadSourceConfig(
            requested_scope=requested_scope,
            resolved_scope="session",
            source_refs=session_refs,
            query_terms=extract_download_queries(sources),
            upload_batch_id=latest_batch.upload_batch_id if latest_batch else "",
            selection_reason="用户要求使用当前会话全部上传材料。",
        )
    if requested_scope == "workspace":
        sources = discover_download_sources(workspace_root, workspace_refs)
        return DownloadSourceConfig(
            requested_scope=requested_scope,
            resolved_scope="workspace",
            source_refs=workspace_refs,
            query_terms=extract_download_queries(sources),
            selection_reason="用户要求扫描工作区中的文献线索。",
        )

    combined = _deduplicate([*latest_refs, *workspace_refs])[:source_limit]
    sources = discover_download_sources(workspace_root, combined)
    if latest_refs:
        reason = "自动模式优先纳入最新上传的文献清单，并补充工作区中的题目、摘要和 bib 线索。"
        scope = "session"
    else:
        reason = "自动模式未发现上传清单，改为扫描工作区中的文献线索。"
        scope = "workspace"
    return DownloadSourceConfig(
        requested_scope="auto",
        resolved_scope=scope,
        source_refs=combined,
        query_terms=extract_download_queries(sources),
        upload_batch_id=latest_batch.upload_batch_id if latest_batch and latest_refs else "",
        selection_reason=reason,
    )


def select_download_workspace_sources(workspace_root: Path, *, limit: int = 50) -> list[str]:
    ranked: list[tuple[int, int, str]] = []
    for directory_rank, directory_name in enumerate(WORKSPACE_ORDER):
        directory = workspace_root / directory_name
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if not _is_source_file(path):
                continue
            relative = path.relative_to(workspace_root).as_posix()
            priority = directory_rank * 100
            lowered = path.stem.lower()
            if path.suffix.lower() in BIB_EXTENSIONS:
                priority -= 80
            if any(term in lowered for term in ("download", "paper", "bib", "reference", "literature")):
                priority -= 20
            ranked.append((priority, -path.stat().st_mtime_ns, relative))
    return [relative for _, _, relative in sorted(ranked)[:limit]]


def _parse_source_file(path: Path, workspace_root: Path) -> list[DownloadSource]:
    suffix = path.suffix.lower()
    if suffix in PDF_EXTENSIONS:
        return []
    if suffix in BIB_EXTENSIONS:
        return _parse_bibliography(path, workspace_root)
    if suffix in TEXT_EXTENSIONS:
        return _parse_text(path, workspace_root)
    return []


def _parse_bibliography(path: Path, workspace_root: Path) -> list[DownloadSource]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    entries: list[DownloadSource] = []
    for block in re.split(r"(?m)^@", text):
        if not block.strip():
            continue
        title = _extract_field(block, "title")
        doi = _extract_field(block, "doi")
        url = _extract_field(block, "url")
        key = _extract_entry_key(block)
        query = title or doi or key
        entries.append(
            DownloadSource(
                source_path=_relative_path(workspace_root, path),
                source_type="bibliography",
                title=title,
                doi=_normalize_doi(doi),
                url=_normalize_url(url),
                query=query,
            )
        )
    if entries:
        return entries
    return [
        DownloadSource(
            source_path=_relative_path(workspace_root, path),
            source_type="bibliography",
            query=path.stem,
        )
    ]


def _parse_text(path: Path, workspace_root: Path) -> list[DownloadSource]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    items: list[DownloadSource] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("#", "-", "*", "Q")):
            query = _strip_query_prefix(stripped)
            if query:
                items.append(
                    DownloadSource(
                        source_path=_relative_path(workspace_root, path),
                        source_type="text",
                        query=query,
                    )
                )
                continue
        doi = _extract_doi_from_text(stripped)
        url = _extract_url_from_text(stripped)
        if doi or url:
            items.append(
                DownloadSource(
                    source_path=_relative_path(workspace_root, path),
                    source_type="text",
                    doi=doi,
                    url=url,
                    query=doi or url or stripped,
                )
            )
    if items:
        return items
    return [
        DownloadSource(
            source_path=_relative_path(workspace_root, path),
            source_type="text",
            query=path.stem,
        )
    ]


def _extract_field(block: str, field: str) -> str:
    match = re.search(rf'(?im)^\s*{re.escape(field)}\s*=\s*[\{{"]\s*(.+?)\s*[\}}"]\s*,?\s*$', block)
    return match.group(1).strip() if match else ""


def _extract_entry_key(block: str) -> str:
    match = re.match(r"(?is)\s*\w+\s*\{\s*([^,\s]+)", block)
    return match.group(1).strip() if match else ""


def _extract_doi_from_text(text: str) -> str:
    match = re.search(r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", text, re.I)
    return _normalize_doi(match.group(1)) if match else ""


def _extract_url_from_text(text: str) -> str:
    match = re.search(r"https?://\S+", text)
    return _normalize_url(match.group(0)) if match else ""


def _normalize_doi(value: str) -> str:
    cleaned = value.strip()
    cleaned = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", cleaned, flags=re.I)
    return cleaned.strip().rstrip(".,;)")


def _normalize_url(value: str) -> str:
    cleaned = value.strip()
    try:
        parsed = urllib.parse.urlparse(cleaned)
    except ValueError:
        return ""
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return cleaned.rstrip(".,;)")


def _strip_query_prefix(value: str) -> str:
    cleaned = re.sub(r"^(?:[-*]\s*|Q\d+\s*[:：]\s*)", "", value).strip()
    return cleaned.strip(" `\"'")


def _clean_query(value: str) -> str:
    cleaned = " ".join(value.split()).strip(" `\"'")
    return cleaned


def _relative_path(workspace_root: Path, path: Path) -> str:
    return path.resolve().relative_to(workspace_root.resolve()).as_posix()


def _requested_source_scope(objective: str) -> str:
    match = re.search(
        r"--(?:source|scope)(?:-scope)?(?:=|\s+)(auto|attachments|selected|session|workspace)\b",
        objective,
        re.I,
    )
    return match.group(1).lower() if match else "auto"


def _extract_explicit_refs(objective: str, workspace_root: Path) -> list[str]:
    candidates = re.findall(
        r"(?:`([^`]+)`|[\"']([^\"']+)[\"']|(?<![\w.-])((?:bib|plan|idea|code|figures|paper|rebuttal|wiki|Content|logs)[/\\][^\s,;]+))",
        objective,
        re.I,
    )
    values = [next((part for part in groups if part), "").rstrip(".,;") for groups in candidates]
    return _valid_refs(workspace_root, values)


def _valid_refs(workspace_root: Path, values: Iterable[str]) -> list[str]:
    root = workspace_root.resolve()
    refs: list[str] = []
    for value in values:
        normalized = str(value).replace("\\", "/").lstrip("./")
        target = (workspace_root / normalized).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            continue
        if target.exists() and normalized not in refs:
            refs.append(normalized)
    return refs


def _expand_refs(workspace_root: Path, refs: Iterable[str], limit: int) -> list[str]:
    expanded: list[str] = []
    for relative in refs:
        target = workspace_root / relative
        if _is_source_file(target):
            expanded.append(target.relative_to(workspace_root).as_posix())
        elif target.is_dir():
            expanded.extend(
                path.relative_to(workspace_root).as_posix()
                for path in sorted(target.rglob("*"))
                if _is_source_file(path)
            )
        if len(expanded) >= limit:
            break
    return _deduplicate(expanded)[:limit]


def _is_source_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in (BIB_EXTENSIONS | TEXT_EXTENSIONS | PDF_EXTENSIONS)


def _deduplicate(values: Iterable[str]) -> list[str]:
    results: list[str] = []
    for value in values:
        if value not in results:
            results.append(value)
    return results


def _is_within_root(workspace_root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(workspace_root.resolve())
    except ValueError:
        return False
    return True

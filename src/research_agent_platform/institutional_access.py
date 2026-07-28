from __future__ import annotations

import urllib.parse
from pathlib import Path

from .connectors.scholar import LiteratureBundle, PaperRecord


def _doi_for(paper: PaperRecord) -> str:
    doi = paper.identifiers.get("doi", "").strip()
    if doi:
        return doi.removeprefix("https://doi.org/").removeprefix("http://doi.org/")
    url = paper.url.strip()
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc.casefold() in {"doi.org", "dx.doi.org"}:
        return parsed.path.lstrip("/")
    return ""


def _join_proxy(prefix: str, url: str) -> str:
    prefix = prefix.strip()
    if not prefix:
        return ""
    if "{url}" in prefix:
        return prefix.replace("{url}", urllib.parse.quote(url, safe=""))
    return prefix.rstrip("/") + "/" + url.lstrip("/")


def _openurl_link(base: str, paper: PaperRecord, doi: str) -> str:
    if not base.strip():
        return ""
    params = {
        "genre": "article",
        "atitle": paper.title,
        "title": paper.venue,
        "date": str(paper.year or ""),
        "doi": doi,
    }
    encoded = urllib.parse.urlencode(
        {key: value for key, value in params.items() if value},
        quote_via=urllib.parse.quote,
    )
    separator = "&" if "?" in base else "?"
    return f"{base}{separator}{encoded}"


def build_institutional_handoff(
    bundle: LiteratureBundle,
    workspace_root: Path,
    *,
    enabled: bool,
    institution_name: str,
    gateway_base: str,
    eproxy_base: str,
    openurl_base: str,
    proxy_prefix: str,
    mode: str,
) -> dict[str, object]:
    items: list[dict[str, object]] = []
    if not enabled:
        return {"enabled": False, "institution": institution_name, "mode": mode, "items": []}

    for paper in bundle.papers:
        if paper.download_status == "downloaded":
            continue
        doi = _doi_for(paper)
        doi_url = f"https://doi.org/{doi}" if doi else paper.url
        links = {
            "doi": doi_url,
            "openurl": _openurl_link(openurl_base, paper, doi),
            "gateway": gateway_base.strip(),
            "eproxy": eproxy_base.strip(),
            "proxied_doi": _join_proxy(proxy_prefix, doi_url) if doi_url else "",
        }
        links = {key: value for key, value in links.items() if value}
        if not links:
            continue
        items.append(
            {
                "paper_id": paper.paper_id,
                "title": paper.title,
                "doi": doi,
                "status": "requires_institution_login",
                "reason": paper.download_error or paper.download_status or "No public PDF was downloaded.",
                "links": links,
                "upload_target": "bib",
                "recommended_path": f"bib/papers/{paper.paper_id or 'paper'}_<downloaded-title>.pdf",
            }
        )

    return {
        "enabled": True,
        "institution": institution_name,
        "mode": mode,
        "workspace_hint": "After downloading with your own institutional account, upload PDFs with target=bib so they are stored under bib/papers/.",
        "items": items,
    }


def institutional_handoff_markdown(handoff: dict[str, object]) -> str:
    institution = str(handoff.get("institution") or "Institution")
    items = list(handoff.get("items") or [])
    lines = [
        "# Institutional Access Handoff",
        "",
        f"- Institution: {institution}",
        f"- Mode: {handoff.get('mode', 'handoff')}",
        "- Account policy: Use each user's own institutional login. Do not share or store personal credentials.",
        "- Download policy: This file only provides authorized access links for papers without an automatically downloaded public PDF.",
        "- Upload destination: Upload downloaded literature PDFs with `target=bib`; the platform stores them under `bib/papers/`.",
        "- Browser shortcut: if your upload UI only supports automatic routing, rename downloaded PDFs to start with the paper ID, for example `P001_method.pdf`; automatic upload will then store them under `bib/papers/`.",
        "",
        "## Papers Requiring Institutional Login",
    ]
    if not items:
        lines.append("- None")
        return "\n".join(lines) + "\n"

    for item in items:
        lines.extend(
            [
                "",
                f"### {item.get('paper_id', '')} {item.get('title', 'Untitled')}",
                f"- Status: {item.get('status', 'requires_institution_login')}",
                f"- Reason: {item.get('reason', '')}",
                f"- DOI: {item.get('doi', '') or 'unknown'}",
                f"- Recommended upload target: `{item.get('upload_target', 'bib')}`",
                f"- Recommended workspace path: `{item.get('recommended_path', '')}`",
                f"- Browser upload filename hint: `{item.get('paper_id', 'P000')}_{item.get('title', 'paper')}.pdf`",
                "- Links:",
            ]
        )
        links = dict(item.get("links") or {})
        for label, url in links.items():
            lines.append(f"  - {label}: {url}")
    return "\n".join(lines) + "\n"

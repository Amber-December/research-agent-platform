from __future__ import annotations

import re
from pathlib import Path

from .artifacts.store import WORKSPACE_DIRS


IMAGE_EXTENSIONS = {".gif", ".jpeg", ".jpg", ".png", ".svg", ".tif", ".tiff", ".webp"}
PAPER_EXTENSIONS = {".doc", ".docx", ".latex", ".pdf", ".rst", ".tex"}
PRESENTATION_EXTENSIONS = {".key", ".odp", ".ppt", ".pptx"}
BIB_EXTENSIONS = {".bib", ".enw", ".nbib", ".ris"}
CODE_EXTENSIONS = {
    ".c",
    ".cc",
    ".cpp",
    ".css",
    ".cu",
    ".go",
    ".h",
    ".hpp",
    ".html",
    ".ipynb",
    ".java",
    ".js",
    ".jsx",
    ".m",
    ".mjs",
    ".py",
    ".r",
    ".rs",
    ".sh",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".vue",
    ".xml",
    ".yaml",
    ".yml",
}
REVIEW_FILENAME_TERMS = (
    "review",
    "reviewer",
    "referee",
    "decision_letter",
    "审稿",
    "评审",
    "审阅意见",
    "修改意见",
)


def normalize_upload_target(target: str) -> str:
    normalized = target.strip() or "auto"
    if normalized != "auto" and normalized not in WORKSPACE_DIRS:
        raise ValueError(f"Unknown workspace directory: {target}")
    return normalized


def classify_upload(filename: str, target: str = "auto") -> str:
    normalized_target = normalize_upload_target(target)
    if normalized_target != "auto":
        return normalized_target
    lowered_name = Path(filename).stem.lower()
    if any(term in lowered_name for term in REVIEW_FILENAME_TERMS):
        return "rebuttal"
    extension = Path(filename).suffix.lower()
    if extension == ".pdf" and re.match(r"^p\d{3}(?:[_-]|$)", lowered_name):
        return "bib"
    if extension in IMAGE_EXTENSIONS:
        return "figures"
    if extension in PAPER_EXTENSIONS:
        return "paper"
    if extension in PRESENTATION_EXTENSIONS:
        return "presentation"
    if extension in BIB_EXTENSIONS:
        return "bib"
    if extension in CODE_EXTENSIONS:
        return "code"
    return "Content"


def sanitize_upload_filename(filename: str) -> str:
    basename = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
    basename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", basename).strip(" .")
    if basename in {"", ".", ".."}:
        raise ValueError("Upload filename is empty or invalid")
    return basename[:180]


def next_upload_relative_path(workspace_root: Path, directory: str, filename: str) -> str:
    upload_directory = _upload_directory(workspace_root, directory, filename)
    candidate = upload_directory / filename
    if not candidate.exists():
        return candidate.relative_to(workspace_root).as_posix()
    suffix = candidate.suffix
    stem = candidate.stem
    for index in range(2, 10000):
        numbered = upload_directory / f"{stem}_{index}{suffix}"
        if not numbered.exists():
            return numbered.relative_to(workspace_root).as_posix()
    raise ValueError(f"Too many files share the same name: {filename}")


def _upload_directory(workspace_root: Path, directory: str, filename: str) -> Path:
    if directory == "bib" and Path(filename).suffix.lower() == ".pdf":
        return workspace_root / "bib" / "papers"
    return workspace_root / directory / "uploads"


def upload_artifact_kind(filename: str) -> str:
    extension = Path(filename).suffix.lower()
    if extension in IMAGE_EXTENSIONS:
        return "image"
    if extension in PAPER_EXTENSIONS or extension in PRESENTATION_EXTENSIONS:
        return "document"
    return "note"

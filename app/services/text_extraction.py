"""Shared text extraction utilities for PDF and EPUB formats.

Both BookService and EmbeddingsService use these helpers so that neither
service depends on the other for format detection or text extraction.
"""

from __future__ import annotations

import re
from html import unescape
from pathlib import Path
from typing import Any


def detect_format(path: Path) -> str:
    """Return 'pdf' or 'epub' based on the file extension."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix == ".epub":
        return "epub"
    raise ValueError("Only PDF and EPUB formats are supported.")


def extract_text(
    path: Path,
    file_format: str,
    preserve_format: bool = False,
) -> tuple[str, int | None]:
    """Extract plain text from *path*.

    Returns ``(text, page_count)`` where *page_count* may be ``None`` for EPUB.
    """
    if file_format == "pdf":
        return _extract_pdf_text(path, preserve_format=preserve_format)
    if file_format == "epub":
        return _extract_epub_text(path, preserve_format=preserve_format)
    raise ValueError("Unsupported format.")


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------


def _extract_pdf_text(path: Path, preserve_format: bool = False) -> tuple[str, int | None]:
    try:
        import pdfplumber
    except ImportError as exc:
        raise ValueError("pdfplumber is required to extract PDF text.") from exc

    texts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            if preserve_format:
                try:
                    page_text = (
                        page.extract_text(
                            layout=True,
                            x_tolerance=2,
                            y_tolerance=2,
                        )
                        or ""
                    )
                except TypeError:
                    page_text = page.extract_text() or ""
                if _looks_unspaced(page_text):
                    page_text = _extract_pdf_words(page)
                page_text = _normalize_bullets(page_text)
                texts.append(f"--- Page {page_number} ---\n{page_text}".rstrip())
            else:
                texts.append(page.extract_text() or "")
        page_count = len(pdf.pages)
    return "\n".join(texts).strip(), page_count


def _looks_unspaced(text: str, min_length: int = 200) -> bool:
    if not text or len(text) < min_length:
        return False
    space_ratio = text.count(" ") / max(len(text), 1)
    return space_ratio < 0.01


def _extract_pdf_words(page: Any) -> str:
    words = page.extract_words(use_text_flow=True)
    if not words:
        return ""
    lines: list[list[Any]] = []
    for word in words:
        if not lines:
            lines.append([word])
            continue
        last_line = lines[-1]
        if abs(word["top"] - last_line[-1]["top"]) <= 3:
            last_line.append(word)
        else:
            lines.append([word])
    rendered_lines = [" ".join(item["text"] for item in line) for line in lines]
    return "\n".join(rendered_lines)


def _normalize_bullets(text: str) -> str:
    if not text:
        return text
    text = re.sub(r"(?<!^)(?<!\n)(?=[•●○])", "\n", text)
    text = re.sub(r"(?<!^)(?<!\n)[ \t]*([•●○])", r"\n\1", text)
    text = re.sub(r"([•●○])(?!\s)", r"\1 ", text)
    text = re.sub(r"(?<!^)(\s+-\s+)", r"\n\1", text)
    return text


# ---------------------------------------------------------------------------
# EPUB
# ---------------------------------------------------------------------------


def _extract_epub_text(path: Path, preserve_format: bool = False) -> tuple[str, int | None]:
    try:
        from ebooklib import ITEM_DOCUMENT, epub
    except ImportError as exc:
        raise ValueError("ebooklib is required to extract EPUB text.") from exc

    book = epub.read_epub(str(path))
    texts: list[str] = []
    for item in book.get_items_of_type(ITEM_DOCUMENT):
        content = item.get_content().decode("utf-8", errors="ignore")
        if preserve_format:
            texts.append(content)
        else:
            texts.append(_strip_html(content))
    return "\n".join(texts).strip(), None


def _strip_html(content: str) -> str:
    text = re.sub(r"<[^>]+>", " ", content)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()

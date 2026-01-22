from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

import pdfplumber


@dataclass(frozen=True)
class PdfMeta:
    pages: int
    title: str | None
    author: str | None
    producer: str | None
    creator: str | None
    subject: str | None


def _clean_text(text: str) -> str:
    # Common PDF artifacts: non-breaking space, weird hyphenation markers, etc.
    return (
        text.replace("\u00a0", " ")
        .replace("\ufeff", "")
        .replace("￾", "")  # seen in some exports
        .replace("\r", "")
        .strip()
    )


def extract_text_pages(source: Path | BinaryIO) -> tuple[list[str], PdfMeta]:
    """Extract plain text page-by-page using pdfplumber.

    Works best when PDF contains embedded text layer.
    """
    with pdfplumber.open(source) as pdf:
        meta: dict[str, Any] = pdf.metadata or {}
        text_pages: list[str] = []
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
            text_pages.append(_clean_text(text))
        pdf_meta = PdfMeta(
            pages=len(pdf.pages),
            title=_clean_text(meta.get("Title", "")) or None,
            author=_clean_text(meta.get("Author", "")) or None,
            producer=_clean_text(meta.get("Producer", "")) or None,
            creator=_clean_text(meta.get("Creator", "")) or None,
            subject=_clean_text(meta.get("Subject", "")) or None,
        )
    return text_pages, pdf_meta

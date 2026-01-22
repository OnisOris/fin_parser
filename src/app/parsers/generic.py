from __future__ import annotations

from typing import Any

from app.parsers.base import BaseParser
from app.utils.pdf import PdfMeta


class GenericParser(BaseParser):
    doc_type = "generic_text_v1"

    def can_parse(self, text_pages: list[str], meta: PdfMeta) -> bool:
        return True

    def parse(self, text_pages: list[str], meta: PdfMeta) -> dict[str, Any]:
        return {
            "meta": {
                "pages": meta.pages,
                "title": meta.title,
                "author": meta.author,
                "producer": meta.producer,
                "creator": meta.creator,
                "subject": meta.subject,
            },
            "pages": [{"page": i + 1, "text": t} for i, t in enumerate(text_pages)],
        }

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.utils.pdf import PdfMeta


class BaseParser(ABC):
    """Interface for document-specific parsers."""

    doc_type: str = "unknown"

    @abstractmethod
    def can_parse(self, text_pages: list[str], meta: PdfMeta) -> bool:
        raise NotImplementedError

    @abstractmethod
    def parse(self, text_pages: list[str], meta: PdfMeta) -> dict[str, Any]:
        raise NotImplementedError

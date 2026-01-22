from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.parsers.base import BaseParser
from app.parsers.generic import GenericParser
from app.parsers.tbank_cashflow import TBankCashflowParser
from app.utils.pdf import PdfMeta


@dataclass(frozen=True)
class ParseResult:
    doc_type: str
    meta: dict[str, Any]
    data: dict[str, Any]


_PARSERS: list[BaseParser] = [
    # Most specific first
    TBankCashflowParser(),
    GenericParser(),
]


def parse_document(text_pages: list[str], meta: PdfMeta) -> ParseResult:
    for parser in _PARSERS:
        if parser.can_parse(text_pages, meta):
            parsed = parser.parse(text_pages, meta)
            # Each parser includes "meta" and either "data" or generic fields.
            # We unify the outer shape here.
            if parser.doc_type == "generic_text_v1":
                return ParseResult(doc_type=parser.doc_type, meta=parsed.get("meta", {}), data=parsed)
            return ParseResult(
                doc_type=parser.doc_type,
                meta=parsed.get("meta", {}),
                data=parsed.get("data", {}),
            )
    # Fallback (shouldn't happen because GenericParser.can_parse is True)
    gp = GenericParser()
    parsed = gp.parse(text_pages, meta)
    return ParseResult(doc_type=gp.doc_type, meta=parsed.get("meta", {}), data=parsed)

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import uvicorn

from app.api.server import create_app
from app.parsers.registry import parse_document
from app.utils.pdf import extract_text_pages


def _cmd_serve(args: argparse.Namespace) -> int:
    app = create_app()
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        reload=args.reload,
    )
    return 0


def _cmd_parse(args: argparse.Namespace) -> int:
    pdf_path = Path(args.file)
    if not pdf_path.exists():
        print(f"File not found: {pdf_path}", file=sys.stderr)
        return 2

    text_pages, meta = extract_text_pages(pdf_path)

    if all(not t.strip() for t in text_pages):
        print(
            "No extractable text found (likely scanned PDF). OCR is not enabled.",
            file=sys.stderr,
        )
        return 3

    result = parse_document(text_pages, meta)
    out = {
        "doc_type": result.doc_type,
        "meta": result.meta,
        "data": result.data,
    }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pdf-parser", description="PDF → JSON parser service")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("serve", help="Run HTTP API server")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", default=8000, type=int)
    s.add_argument("--log-level", default="info")
    s.add_argument("--reload", action="store_true", help="Auto-reload on code changes (dev only)")
    s.set_defaults(func=_cmd_serve)

    c = sub.add_parser("parse", help="Parse a PDF file locally and print JSON")
    c.add_argument("--file", required=True, help="Path to PDF")
    c.set_defaults(func=_cmd_parse)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    code = int(args.func(args))
    raise SystemExit(code)


if __name__ == "__main__":
    main()

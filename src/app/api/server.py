from __future__ import annotations

from io import BytesIO

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.parsers.registry import parse_document
from app.utils.pdf import extract_text_pages


def create_app() -> FastAPI:
    app = FastAPI(
        title="pdf-parser-service",
        version="0.1.0",
        description="Upload PDF → parse → return JSON",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/parse")
    async def parse_pdf(file: UploadFile = File(...)) -> JSONResponse:
        if file.content_type not in ("application/pdf", "application/octet-stream"):
            raise HTTPException(status_code=415, detail="Only PDF uploads are supported.")

        blob = await file.read()
        if not blob:
            raise HTTPException(status_code=400, detail="Empty file.")
        # Basic safety guard (~20MB). Tune as needed.
        if len(blob) > 20 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large (limit 20MB).")

        try:
            text_pages, meta = extract_text_pages(BytesIO(blob))
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"Failed to open/parse PDF: {e}") from e

        # If PDF has no text layer, text_pages may be empty strings.
        if all(not t.strip() for t in text_pages):
            raise HTTPException(
                status_code=422,
                detail="PDF contains no extractable text (likely scanned). OCR is not enabled in this build.",
            )

        result = parse_document(text_pages, meta)
        return JSONResponse(
            {
                "doc_type": result.doc_type,
                "meta": result.meta,
                "data": result.data,
            }
        )

    return app

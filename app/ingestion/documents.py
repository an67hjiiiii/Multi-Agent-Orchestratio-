from __future__ import annotations

import hashlib
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

from app.retrieval.text import normalize_text


DOCUMENT_INGESTION_VERSION = "s2-document-ingestion-v1"
MAX_DOCUMENT_BYTES = 2_000_000
SUPPORTED_TEXT_EXTENSIONS = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
}
SUPPORTED_DOCUMENT_EXTENSIONS = {
    **SUPPORTED_TEXT_EXTENSIONS,
    ".pdf": "application/pdf",
}


class DocumentTypeError(ValueError):
    """Raised when a document is outside the bounded local ingestion scope."""


@dataclass(frozen=True)
class ExtractedDocument:
    source_name: str
    text: str
    source_type: str
    source_format: str
    byte_size: int
    source_hash: str
    provenance: dict[str, Any]


def extract_document(
    data: bytes | str,
    source_name: str,
    *,
    origin: str = "upload",
    content_type: str | None = None,
) -> ExtractedDocument:
    """Extract UTF-8 TXT/MD or selectable text from a PDF.

    The PDF boundary deliberately uses text extraction only.  Scanned-image
    PDFs fail explicitly; OCR is outside the Sprint 2 contract.
    """

    clean_name = str(source_name or "").strip()
    if not clean_name:
        raise ValueError("source_name must not be empty")
    suffix = Path(clean_name).suffix.casefold()
    source_type = SUPPORTED_DOCUMENT_EXTENSIONS.get(suffix)
    if source_type is None:
        supported = ", ".join(sorted(SUPPORTED_DOCUMENT_EXTENSIONS))
        raise DocumentTypeError(
            f"unsupported document type {suffix or '<none>'}; supported: {supported}"
        )

    if suffix == ".pdf":
        if not isinstance(data, bytes):
            raise TypeError("PDF document data must be bytes")
        byte_size = len(data)
        _assert_size(byte_size)
        raw_text, page_count = _extract_pdf_text(data)
    elif isinstance(data, bytes):
        byte_size = len(data)
        _assert_size(byte_size)
        try:
            raw_text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise UnicodeError("document must be valid UTF-8") from exc
    elif isinstance(data, str):
        raw_text = data
        byte_size = len(data.encode("utf-8"))
        _assert_size(byte_size)
    else:
        raise TypeError("document data must be bytes or text")

    text = normalize_text(raw_text)
    if not text:
        raise ValueError("text must not be empty")

    source_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    provenance: dict[str, Any] = {
        "ingestion_version": DOCUMENT_INGESTION_VERSION,
        "source_type": source_type,
        "source_format": suffix.lstrip("."),
        "source_hash": source_hash,
        "byte_size": byte_size,
        "origin": str(origin or "upload").strip() or "upload",
    }
    if isinstance(content_type, str) and content_type.strip():
        provenance["declared_content_type"] = content_type.strip().lower()
    if suffix == ".pdf":
        provenance.update({"page_count": page_count, "parser": "pypdf-text-v1"})

    return ExtractedDocument(
        source_name=clean_name,
        text=text,
        source_type=source_type,
        source_format=suffix.lstrip("."),
        byte_size=byte_size,
        source_hash=source_hash,
        provenance=provenance,
    )


def _assert_size(byte_size: int) -> None:
    if byte_size > MAX_DOCUMENT_BYTES:
        raise ValueError(f"document exceeds the {MAX_DOCUMENT_BYTES}-byte size limit")


def _extract_pdf_text(data: bytes) -> tuple[str, int]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - environment-specific
        raise DocumentTypeError("PDF text extraction requires pypdf") from exc

    try:
        reader = PdfReader(BytesIO(data), strict=False)
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:
        raise DocumentTypeError("PDF text extraction failed") from exc

    text = "\n\n".join(page for page in pages if page.strip()).strip()
    if not text:
        raise DocumentTypeError(
            "PDF contains no extractable text; scanned-image OCR is not supported"
        )
    return text, len(reader.pages)


__all__ = [
    "DOCUMENT_INGESTION_VERSION",
    "MAX_DOCUMENT_BYTES",
    "SUPPORTED_TEXT_EXTENSIONS",
    "SUPPORTED_DOCUMENT_EXTENSIONS",
    "DocumentTypeError",
    "ExtractedDocument",
    "extract_document",
]

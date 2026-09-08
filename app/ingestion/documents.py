from __future__ import annotations

import hashlib
from io import BytesIO
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.retrieval.text import normalize_source_name, normalize_text


DOCUMENT_INGESTION_VERSION = "kb-v3-document-ingestion-v1"
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
    """Raised when a document is outside the deliberately small local boundary."""


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
    """Decode one supported local document and return stable metadata.

    PDF extraction is text-only and intentionally does not attempt OCR. The
    optional parser is imported lazily so the lexical TXT/MD path remains
    usable when the PDF dependency is not installed.
    """

    clean_name = normalize_source_name(source_name)
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
        if byte_size > MAX_DOCUMENT_BYTES:
            raise ValueError(
                f"document exceeds the {MAX_DOCUMENT_BYTES}-byte size limit"
            )
        raw_text, page_count = _extract_pdf_text(data)
    elif isinstance(data, bytes):
        byte_size = len(data)
        if byte_size > MAX_DOCUMENT_BYTES:
            raise ValueError(
                f"document exceeds the {MAX_DOCUMENT_BYTES}-byte size limit"
            )
        try:
            raw_text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise UnicodeError("document must be valid UTF-8") from exc
    elif isinstance(data, str):
        raw_text = data
        byte_size = len(data.encode("utf-8"))
        if byte_size > MAX_DOCUMENT_BYTES:
            raise ValueError(
                f"document exceeds the {MAX_DOCUMENT_BYTES}-byte size limit"
            )
    else:
        raise TypeError("document data must be bytes or text")

    clean_text = normalize_text(raw_text)
    if not clean_text:
        raise ValueError("text must not be empty")

    source_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()
    provenance = {
        "ingestion_version": DOCUMENT_INGESTION_VERSION,
        "source_type": source_type,
        "source_format": suffix.lstrip("."),
        "source_hash": source_hash,
        "byte_size": byte_size,
        "origin": origin.strip() if isinstance(origin, str) and origin.strip() else "upload",
    }
    if isinstance(content_type, str) and content_type.strip():
        provenance["declared_content_type"] = content_type.strip().lower()
    if suffix == ".pdf":
        provenance["page_count"] = page_count
        provenance["parser"] = "pypdf-text-v1"

    return ExtractedDocument(
        source_name=clean_name,
        text=clean_text,
        source_type=source_type,
        source_format=suffix.lstrip("."),
        byte_size=byte_size,
        source_hash=source_hash,
        provenance=provenance,
    )


def _extract_pdf_text(data: bytes) -> tuple[str, int]:
    """Extract selectable PDF text without attempting image OCR."""

    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError as exc:
        raise DocumentTypeError(
            "PDF text extraction requires the optional pypdf dependency"
        ) from exc

    try:
        reader = PdfReader(BytesIO(data))
        pages: list[str] = []
        for page in reader.pages:
            text = page.extract_text() or ""
            if text.strip():
                pages.append(text)
    except Exception as exc:
        raise DocumentTypeError("PDF text extraction failed") from exc

    extracted = "\n\n".join(pages).strip()
    if not extracted:
        raise DocumentTypeError(
            "PDF contains no extractable text; scanned-image OCR is not supported"
        )
    return extracted, len(reader.pages)


def extract_document_path(path: str | Path) -> ExtractedDocument:
    """Read a local path without persisting the absolute path as provenance."""

    document_path = Path(path)
    try:
        data = document_path.read_bytes()
    except OSError as exc:
        raise ValueError(f"unable to read document: {document_path.name}") from exc
    return extract_document(data, document_path.name, origin="local_path")


__all__ = [
    "DOCUMENT_INGESTION_VERSION",
    "MAX_DOCUMENT_BYTES",
    "SUPPORTED_TEXT_EXTENSIONS",
    "SUPPORTED_DOCUMENT_EXTENSIONS",
    "DocumentTypeError",
    "ExtractedDocument",
    "extract_document",
    "extract_document_path",
]

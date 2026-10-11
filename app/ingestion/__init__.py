"""Document extraction and ingestion boundaries."""

from app.ingestion.documents import (
    DOCUMENT_INGESTION_VERSION,
    MAX_DOCUMENT_BYTES,
    DocumentTypeError,
    ExtractedDocument,
    extract_document,
)

__all__ = [
    "DOCUMENT_INGESTION_VERSION",
    "MAX_DOCUMENT_BYTES",
    "DocumentTypeError",
    "ExtractedDocument",
    "extract_document",
]

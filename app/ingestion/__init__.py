"""Document extraction boundaries for the local knowledge base."""

from app.ingestion.documents import (
    DOCUMENT_INGESTION_VERSION,
    MAX_DOCUMENT_BYTES,
    SUPPORTED_TEXT_EXTENSIONS,
    DocumentTypeError,
    extract_document,
    extract_document_path,
)

__all__ = [
    "DOCUMENT_INGESTION_VERSION",
    "MAX_DOCUMENT_BYTES",
    "SUPPORTED_TEXT_EXTENSIONS",
    "DocumentTypeError",
    "extract_document",
    "extract_document_path",
]

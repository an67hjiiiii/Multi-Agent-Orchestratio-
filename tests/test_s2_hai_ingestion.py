from __future__ import annotations

import pytest

from app.ingestion.documents import DocumentTypeError, extract_document


def test_txt_and_markdown_extraction_is_utf8_and_bounded():
    txt = extract_document("Xin chào".encode("utf-8"), "notes.txt")
    markdown = extract_document(b"# Heading\n\nEvidence", "notes.md")

    assert txt.text == "Xin chào"
    assert txt.source_format == "txt"
    assert markdown.source_format == "md"
    assert txt.provenance["ingestion_version"].startswith("s2-")
    assert len(txt.source_hash) == 64


def test_unsupported_document_type_fails_closed():
    with pytest.raises(DocumentTypeError, match="unsupported document type"):
        extract_document(b"name,value\n", "data.csv")


def test_scanned_pdf_is_explicitly_rejected_without_ocr(monkeypatch):
    class Page:
        def extract_text(self):
            return ""

    class Reader:
        def __init__(self, _stream, strict=False):
            self.pages = [Page()]

    import sys
    import types

    fake_pypdf = types.ModuleType("pypdf")
    fake_pypdf.PdfReader = Reader
    monkeypatch.setitem(sys.modules, "pypdf", fake_pypdf)

    with pytest.raises(DocumentTypeError, match="no extractable text"):
        extract_document(b"%PDF-1.7", "scan.pdf")

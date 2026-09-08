from __future__ import annotations

import sys
import types

from app.ingestion.documents import extract_document
from app.retrieval.embeddings import LocalHashEmbedder
from app.storage.knowledge_base import KnowledgeBase
from app.storage.source_store import SourceStore
from app.storage.vector_store import InMemoryVectorStore


def test_hybrid_knowledge_base_keeps_vector_and_lexical_paths_local(tmp_path):
    store = SourceStore(tmp_path / "data")
    store.import_text(
        "auth.md",
        "Authentication verifies identity before authorization checks permission.",
    )
    vector = InMemoryVectorStore(vector_size=16)
    knowledge = KnowledgeBase(
        store,
        vector_store=vector,
        embedder=LocalHashEmbedder(dimension=16),
        backend_name="memory",
        retrieval_mode="HYBRID",
    )

    results = knowledge.search("verify identity", top_k=3)

    assert results
    assert results[0].source_name == "auth.md"
    assert knowledge.status()["retrieval_backend"] == "hybrid"
    assert knowledge.status()["vector_indexed_chunks"] == 1


def test_pdf_extraction_records_text_provenance_without_ocr(monkeypatch):
    class Page:
        def extract_text(self):
            return "Selectable PDF text"

    class Reader:
        def __init__(self, _stream):
            self.pages = [Page()]

    fake_pypdf = types.ModuleType("pypdf")
    fake_pypdf.PdfReader = Reader
    monkeypatch.setitem(sys.modules, "pypdf", fake_pypdf)

    document = extract_document(b"%PDF-1.7", "guide.pdf", content_type="application/pdf")

    assert document.text == "Selectable PDF text"
    assert document.source_format == "pdf"
    assert document.provenance["page_count"] == 1
    assert document.provenance["parser"] == "pypdf-text-v1"


def test_pdf_without_selectable_text_is_explicit(monkeypatch):
    class Page:
        def extract_text(self):
            return ""

    class Reader:
        def __init__(self, _stream):
            self.pages = [Page()]

    fake_pypdf = types.ModuleType("pypdf")
    fake_pypdf.PdfReader = Reader
    monkeypatch.setitem(sys.modules, "pypdf", fake_pypdf)

    try:
        extract_document(b"%PDF-1.7", "scan.pdf")
    except ValueError as exc:
        assert "no extractable text" in str(exc)
    else:
        raise AssertionError("scanned-image PDF must remain explicit without OCR")

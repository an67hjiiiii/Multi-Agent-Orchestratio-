from fastapi.testclient import TestClient

from app import main as main_module
from app.auth.store import AuthStore
from app.main import app


def _make_text_pdf(text: str) -> bytes:
    content = f"BT /F1 12 Tf 20 50 Td ({text}) Tj ET".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 100] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n"
        + content
        + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii") + obj + b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


def _authenticated_user(tmp_path):
    store = AuthStore(tmp_path / "auth")
    user = store.register(email="pdf-owner@example.test", password="correct-horse")
    token, _ = store.create_session(user["user_id"])
    app.state.auth_store = store
    return {"Authorization": f"Bearer {token}"}


def test_text_pdf_upload_extracts_text_into_owner_source(tmp_path, monkeypatch):
    monkeypatch.setattr(main_module, "DATA_DIR", str(tmp_path / "data"))
    headers = _authenticated_user(tmp_path)

    with TestClient(app) as client:
        uploaded = client.post(
            "/api/sources/file",
            headers=headers,
            files={"file": ("notes.pdf", _make_text_pdf("Sprint one evidence"), "application/pdf")},
        )
        source_id = uploaded.json()["source_id"]
        source = client.get(f"/api/sources/{source_id}", headers=headers)

    assert uploaded.status_code == 200
    assert source.status_code == 200
    extracted_text = source.json()["chunks"][0]["text"].strip()
    assert extracted_text == "Sprint one evidence"
    assert "%PDF" not in extracted_text


def test_image_only_pdf_is_rejected_without_ocr(tmp_path, monkeypatch):
    monkeypatch.setattr(main_module, "DATA_DIR", str(tmp_path / "data"))
    headers = _authenticated_user(tmp_path)

    with TestClient(app) as client:
        uploaded = client.post(
            "/api/sources/file",
            headers=headers,
            files={"file": ("image-only.pdf", _make_text_pdf(""), "application/pdf")},
        )

    assert uploaded.status_code == 422
    assert uploaded.json()["detail"] == "PDF_NO_TEXT"

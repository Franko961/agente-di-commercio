"""
Iteration 4 - Document Upload (Emergent object storage)
- POST /api/documents/upload (multipart) success + validation errors
- GET /api/documents/{id}/download (auth via header, o via token firmato da /signed-url)
- DELETE /api/documents/{id} soft delete + listing excludes them
"""
import os
import io
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"
EMAIL = "agente@demo.it"
PASSWORD = "demo1234"

# Minimal valid PDF bytes
MINI_PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
    b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n"
    b"0000000052 00000 n \n0000000099 00000 n \ntrailer<</Size 4/Root 1 0 R>>\n"
    b"startxref\n149\n%%EOF\n"
)


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    if r.status_code != 200:
        pytest.skip(f"Login failed: {r.status_code}")
    return r.json()["token"]


@pytest.fixture(scope="module")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def created_doc(auth_headers):
    files = {"file": ("TEST_doc.pdf", MINI_PDF, "application/pdf")}
    data = {"name": "TEST_pdf_upload", "category": "contratto", "notes": "test note"}
    r = requests.post(f"{API}/documents/upload", headers=auth_headers, files=files, data=data, timeout=60)
    assert r.status_code == 200, f"Upload failed: {r.status_code} {r.text}"
    j = r.json()
    yield j
    # Cleanup
    requests.delete(f"{API}/documents/{j['id']}", headers=auth_headers)


class TestUploadSuccess:
    def test_upload_returns_doc_with_required_fields(self, created_doc):
        for k in ["id", "storage_path", "size", "content_type", "original_filename", "name", "category"]:
            assert k in created_doc, f"missing field: {k}"
        assert created_doc["original_filename"] == "TEST_doc.pdf"
        assert created_doc["content_type"] == "application/pdf"
        assert created_doc["size"] == len(MINI_PDF)
        assert created_doc["category"] == "contratto"
        assert created_doc["name"] == "TEST_pdf_upload"
        assert isinstance(created_doc["storage_path"], str) and created_doc["storage_path"]
        assert "_id" not in created_doc

    def test_upload_appears_in_list(self, auth_headers, created_doc):
        r = requests.get(f"{API}/documents", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        docs = r.json()
        assert any(d["id"] == created_doc["id"] for d in docs)

    def test_listing_sorted_desc_by_created_at(self, auth_headers):
        r = requests.get(f"{API}/documents", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        docs = r.json()
        if len(docs) >= 2:
            cas = [d.get("created_at", "") for d in docs if d.get("created_at")]
            assert cas == sorted(cas, reverse=True)


class TestUploadValidation:
    def test_reject_unsupported_extension(self, auth_headers):
        files = {"file": ("evil.exe", b"MZbinary", "application/octet-stream")}
        data = {"name": "TEST_exe", "category": "altro"}
        r = requests.post(f"{API}/documents/upload", headers=auth_headers, files=files, data=data, timeout=30)
        assert r.status_code == 400
        assert "exe" in r.text.lower() or "support" in r.text.lower() or "consentit" in r.text.lower()

    def test_reject_empty_file(self, auth_headers):
        files = {"file": ("empty.pdf", b"", "application/pdf")}
        data = {"name": "TEST_empty", "category": "altro"}
        r = requests.post(f"{API}/documents/upload", headers=auth_headers, files=files, data=data, timeout=30)
        assert r.status_code == 400

    def test_upload_requires_auth(self):
        files = {"file": ("x.pdf", MINI_PDF, "application/pdf")}
        data = {"name": "TEST_noauth"}
        r = requests.post(f"{API}/documents/upload", files=files, data=data, timeout=30)
        assert r.status_code == 401


class TestDownload:
    def test_download_with_bearer_returns_bytes(self, auth_headers, created_doc):
        r = requests.get(f"{API}/documents/{created_doc['id']}/download", headers=auth_headers, timeout=60)
        assert r.status_code == 200, r.text
        assert r.content == MINI_PDF
        assert "application/pdf" in r.headers.get("Content-Type", "")
        cd = r.headers.get("Content-Disposition", "")
        assert "TEST_doc.pdf" in cd

    def test_download_with_signed_url_token(self, auth_headers, created_doc):
        """Il vecchio ?auth=<token di sessione> è stato rimosso (un JWT
        valido 7 giorni per l'intero account non deve mai finire in una
        query string). Al suo posto: /signed-url emette un token specifico
        per QUESTO documento, valido pochi minuti, usabile in query string
        senza gli stessi rischi (cronologia browser, log, analytics...)."""
        r = requests.get(f"{API}/documents/{created_doc['id']}/signed-url", headers=auth_headers, timeout=30)
        assert r.status_code == 200, r.text
        signed_path = r.json()["url"]
        assert f"/documents/{created_doc['id']}/download?token=" in signed_path

        r = requests.get(f"{BASE_URL}{signed_path}", timeout=60)
        assert r.status_code == 200
        assert r.content == MINI_PDF

    def test_signed_url_token_non_valido_per_un_altro_documento(self, auth_headers, created_doc):
        """Un token firmato emesso per il documento A non deve funzionare
        se usato sull'URL di download del documento B."""
        files = {"file": ("TEST_altro.pdf", MINI_PDF, "application/pdf")}
        data = {"name": "TEST_altro_doc"}
        r = requests.post(f"{API}/documents/upload", headers=auth_headers, files=files, data=data, timeout=30)
        other_doc = r.json()
        try:
            signed = requests.get(f"{API}/documents/{created_doc['id']}/signed-url", headers=auth_headers, timeout=30)
            token = signed.json()["url"].split("token=")[-1]

            r = requests.get(f"{API}/documents/{other_doc['id']}/download?token={token}", timeout=30)
            assert r.status_code == 401
        finally:
            requests.delete(f"{API}/documents/{other_doc['id']}", headers=auth_headers)

    def test_signed_url_richiede_autenticazione(self, created_doc):
        r = requests.get(f"{API}/documents/{created_doc['id']}/signed-url", timeout=30)
        assert r.status_code == 401

    def test_download_without_auth_returns_401(self, created_doc):
        r = requests.get(f"{API}/documents/{created_doc['id']}/download", timeout=30)
        assert r.status_code == 401

    def test_download_not_found(self, auth_headers):
        r = requests.get(f"{API}/documents/nonexistent-id-xyz/download", headers=auth_headers, timeout=30)
        assert r.status_code == 404


class TestSoftDelete:
    def test_soft_delete_removes_from_list(self, auth_headers):
        # Create a fresh doc to delete
        files = {"file": ("TEST_del.pdf", MINI_PDF, "application/pdf")}
        data = {"name": "TEST_to_delete", "category": "altro"}
        r = requests.post(f"{API}/documents/upload", headers=auth_headers, files=files, data=data, timeout=60)
        assert r.status_code == 200
        did = r.json()["id"]

        # Delete
        r = requests.delete(f"{API}/documents/{did}", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        assert r.json().get("ok") is True

        # Should be gone from list
        r = requests.get(f"{API}/documents", headers=auth_headers, timeout=30)
        ids = [d["id"] for d in r.json()]
        assert did not in ids

        # Download should now 404 (soft-deleted)
        r = requests.get(f"{API}/documents/{did}/download", headers=auth_headers, timeout=30)
        assert r.status_code == 404

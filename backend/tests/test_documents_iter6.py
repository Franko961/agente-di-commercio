"""
Iteration 6 - Documents new features
- POST /api/documents/upload accepts tags as comma-separated string → returns parsed array
- PATCH /api/documents/{id} updates metadata (tags/name/category/notes/client_id)
- PATCH rejects unknown fields silently, returns {ok: true}
- PATCH returns 404 for non-existent or soft-deleted docs
- GET /api/documents returns tags array
"""

import pytest
import requests

from tests.live_backend_helpers import (
    API,
    delete_live_backend_account,
    register_live_backend_account,
)

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
    account = register_live_backend_account("docs-iter6")
    if not account:
        pytest.skip("Registrazione account di test fallita o backend non raggiungibile")
    yield account["token"]
    delete_live_backend_account(account)


@pytest.fixture(scope="module")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def _upload(auth_headers, name="TEST_iter6", tags="", category="altro", client_id=None):
    files = {"file": ("TEST_iter6.pdf", MINI_PDF, "application/pdf")}
    data = {"name": name, "category": category, "notes": "n", "tags": tags}
    if client_id:
        data["client_id"] = client_id
    r = requests.post(
        f"{API}/documents/upload",
        headers=auth_headers,
        files=files,
        data=data,
        timeout=60,
    )
    assert r.status_code == 200, r.text
    return r.json()


class TestUploadTags:
    def test_upload_with_tags_parses_csv_to_list(self, auth_headers):
        j = _upload(auth_headers, name="TEST_tags_csv", tags="urgente,2026,vip")
        try:
            assert "tags" in j
            assert j["tags"] == ["urgente", "2026", "vip"]
        finally:
            requests.delete(f"{API}/documents/{j['id']}", headers=auth_headers)

    def test_upload_trims_spaces_and_drops_empty(self, auth_headers):
        j = _upload(auth_headers, name="TEST_tags_trim", tags=" urgente ,  ,vip, ")
        try:
            assert j["tags"] == ["urgente", "vip"]
        finally:
            requests.delete(f"{API}/documents/{j['id']}", headers=auth_headers)

    def test_upload_no_tags_returns_empty_list(self, auth_headers):
        j = _upload(auth_headers, name="TEST_notags", tags="")
        try:
            assert j.get("tags") == []
        finally:
            requests.delete(f"{API}/documents/{j['id']}", headers=auth_headers)

    def test_list_returns_tags_array(self, auth_headers):
        j = _upload(auth_headers, name="TEST_list_tags", tags="alpha,beta")
        try:
            r = requests.get(f"{API}/documents", headers=auth_headers, timeout=30)
            assert r.status_code == 200
            docs = r.json()
            m = next((d for d in docs if d["id"] == j["id"]), None)
            assert m is not None
            assert m.get("tags") == ["alpha", "beta"]
        finally:
            requests.delete(f"{API}/documents/{j['id']}", headers=auth_headers)


class TestPatchDocument:
    def test_patch_updates_tags_name_category_notes(self, auth_headers):
        j = _upload(auth_headers, name="TEST_patch_orig", tags="old")
        did = j["id"]
        try:
            body = {
                "name": "TEST_patch_new",
                "category": "contratto",
                "notes": "updated",
                "tags": ["fresh", "new"],
            }
            r = requests.patch(
                f"{API}/documents/{did}", headers=auth_headers, json=body, timeout=30
            )
            assert r.status_code == 200, r.text
            assert r.json().get("ok") is True

            # Verify via GET
            r2 = requests.get(f"{API}/documents", headers=auth_headers, timeout=30)
            m = next((d for d in r2.json() if d["id"] == did), None)
            assert m is not None
            assert m["name"] == "TEST_patch_new"
            assert m["category"] == "contratto"
            assert m["notes"] == "updated"
            assert m["tags"] == ["fresh", "new"]
        finally:
            requests.delete(f"{API}/documents/{did}", headers=auth_headers)

    def test_patch_unknown_fields_silently_ignored(self, auth_headers):
        j = _upload(auth_headers, name="TEST_patch_unknown", tags="x")
        did = j["id"]
        try:
            body = {
                "name": "TEST_patch_kept",
                "evil": "xxx",
                "user_id": "hack",
                "id": "hack",
            }
            r = requests.patch(
                f"{API}/documents/{did}", headers=auth_headers, json=body, timeout=30
            )
            assert r.status_code == 200
            assert r.json().get("ok") is True
            r2 = requests.get(f"{API}/documents", headers=auth_headers, timeout=30)
            m = next((d for d in r2.json() if d["id"] == did), None)
            assert m["name"] == "TEST_patch_kept"
            # id untouched
            assert m["id"] == did
        finally:
            requests.delete(f"{API}/documents/{did}", headers=auth_headers)

    def test_patch_nonexistent_returns_404(self, auth_headers):
        r = requests.patch(
            f"{API}/documents/does-not-exist-xyz",
            headers=auth_headers,
            json={"name": "x"},
            timeout=30,
        )
        assert r.status_code == 404

    def test_patch_soft_deleted_returns_404(self, auth_headers):
        j = _upload(auth_headers, name="TEST_patch_deleted", tags="")
        did = j["id"]
        r = requests.delete(f"{API}/documents/{did}", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        r2 = requests.patch(
            f"{API}/documents/{did}",
            headers=auth_headers,
            json={"name": "x"},
            timeout=30,
        )
        assert r2.status_code == 404

    def test_patch_requires_auth(self, auth_headers):
        j = _upload(auth_headers, name="TEST_patch_auth", tags="")
        did = j["id"]
        try:
            r = requests.patch(f"{API}/documents/{did}", json={"name": "x"}, timeout=30)
            assert r.status_code == 401
        finally:
            requests.delete(f"{API}/documents/{did}", headers=auth_headers)

    def test_patch_other_users_doc_returns_404(self, auth_headers):
        # Registra un secondo agente — user_id diverso
        other_account = register_live_backend_account("docs-iter6-other")
        if not other_account:
            pytest.skip("Registrazione del secondo account di test fallita")
        other_headers = {"Authorization": f"Bearer {other_account['token']}"}

        # Upload as original user
        j = _upload(auth_headers, name="TEST_patch_other", tags="")
        did = j["id"]
        try:
            r = requests.patch(
                f"{API}/documents/{did}",
                headers=other_headers,
                json={"name": "hijack"},
                timeout=30,
            )
            assert r.status_code == 404
        finally:
            requests.delete(f"{API}/documents/{did}", headers=auth_headers)
            delete_live_backend_account(other_account)


class TestBackwardCompat:
    def test_existing_docs_without_tags_still_listed(self, auth_headers):
        r = requests.get(f"{API}/documents", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        docs = r.json()
        # seeded docs have no 'tags' field but should still come through
        assert isinstance(docs, list)

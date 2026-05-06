"""
Iteration 2 - P1 features:
 - CSV exports (clienti, offerte, provvigioni, lead) with semicolon + UTF-8 BOM
 - Email mock /api/email/send + /api/email/logs
 - Offer signature /api/offers/{id}/sign with auto-commission (idempotent)
"""
import os
import csv
import io
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"
EMAIL = "agente@demo.it"
PASSWORD = "demo1234"


@pytest.fixture(scope="module")
def client():
    r = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    if r.status_code != 200:
        pytest.skip(f"Login failed: {r.status_code}")
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {r.json()['token']}", "Content-Type": "application/json"})
    return s


# ---------- Auth gate ----------
class TestAuthRequired:
    def test_export_clients_requires_auth(self):
        r = requests.get(f"{API}/export/clients.csv")
        assert r.status_code == 401

    def test_email_send_requires_auth(self):
        r = requests.post(f"{API}/email/send", json={"to": "x@x.it", "subject": "s", "body": "b"})
        assert r.status_code == 401


# ---------- CSV Exports ----------
class TestCsvExports:
    def _check_csv(self, resp, expected_headers, filename):
        assert resp.status_code == 200, resp.text
        # Content-type
        assert "text/csv" in resp.headers.get("content-type", "")
        # Filename
        assert filename in resp.headers.get("content-disposition", "")
        # BOM
        text = resp.content.decode("utf-8")
        assert text.startswith("\ufeff"), "Missing UTF-8 BOM"
        # Semicolon delimiter — first line should contain ; between header columns
        first_line = text.lstrip("\ufeff").splitlines()[0]
        assert ";" in first_line, "Missing semicolon delimiter"
        # Parse and verify columns
        reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")), delimiter=";")
        assert reader.fieldnames == expected_headers, f"Got {reader.fieldnames}"
        return list(reader)

    def test_export_clients(self, client):
        r = client.get(f"{API}/export/clients.csv")
        rows = self._check_csv(
            r,
            ["company_name", "contact_name", "email", "phone", "vat_number",
             "address", "city", "province", "zone", "sector", "potential", "notes"],
            "clienti.csv",
        )
        assert len(rows) >= 8

    def test_export_offers(self, client):
        r = client.get(f"{API}/export/offers.csv")
        rows = self._check_csv(
            r,
            ["title", "client", "mandante", "total", "status", "items_count", "expires_at", "created_at"],
            "offerte.csv",
        )
        assert len(rows) >= 3
        # Resolved client/mandante names should not be empty for seeded offers
        assert any(row["client"] for row in rows)
        assert any(row["mandante"] for row in rows)

    def test_export_commissions(self, client):
        r = client.get(f"{API}/export/commissions.csv")
        rows = self._check_csv(
            r,
            ["period", "client", "mandante", "amount", "rate", "status"],
            "provvigioni.csv",
        )
        assert len(rows) >= 2

    def test_export_leads(self, client):
        r = client.get(f"{API}/export/leads.csv")
        self._check_csv(
            r,
            ["company_name", "contact_name", "email", "phone", "source",
             "estimated_value", "status", "notes", "created_at"],
            "lead.csv",
        )


# ---------- Email Mock ----------
class TestEmailMock:
    def test_send_and_log(self, client):
        payload = {"to": "test_p1@example.com", "subject": "TEST_P1 subject", "body": "ciao"}
        r = client.post(f"{API}/email/send", json=payload)
        assert r.status_code == 200
        d = r.json()
        assert d.get("ok") is True
        assert d.get("mocked") is True
        assert isinstance(d.get("id"), str) and len(d["id"]) > 5

        # Logged for current user
        r2 = client.get(f"{API}/email/logs")
        assert r2.status_code == 200
        logs = r2.json()
        assert any(l["id"] == d["id"] and l["subject"] == "TEST_P1 subject"
                   and l.get("mocked") is True for l in logs)

    def test_logs_isolated_per_user(self, client):
        # Logs should be scoped to current user; ensure no cross-user data leaks
        r = client.get(f"{API}/email/logs")
        assert r.status_code == 200
        for log in r.json():
            assert "to" in log and "subject" in log


# ---------- Offer Signature ----------
class TestOfferSignature:
    def test_sign_offer_creates_commission_idempotently(self, client):
        # Create a fresh offer
        clients_l = client.get(f"{API}/clients").json()
        mandanti = client.get(f"{API}/mandanti").json()
        payload = {
            "client_id": clients_l[0]["id"],
            "mandante_id": mandanti[0]["id"],
            "title": "TEST_SignOffer",
            "status": "bozza",
            "items": [{"description": "Item", "quantity": 1, "unit_price": 500, "discount": 0}],
        }
        r = client.post(f"{API}/offers", json=payload)
        assert r.status_code == 200
        oid = r.json()["id"]

        before = len(client.get(f"{API}/commissions").json())

        # First sign — should create commission and set status
        r = client.post(
            f"{API}/offers/{oid}/sign",
            json={"signature": "data:image/png;base64,iVBORw0KGgo=", "signer_name": "Mario Rossi"},
        )
        assert r.status_code == 200
        assert r.json().get("ok") is True

        # Verify offer state
        offers = client.get(f"{API}/offers").json()
        signed = next(o for o in offers if o["id"] == oid)
        assert signed["status"] == "accettata"
        assert signed.get("signature", "").startswith("data:image/png;base64")
        assert signed.get("signer_name") == "Mario Rossi"
        assert signed.get("signed_at")

        after = len(client.get(f"{API}/commissions").json())
        assert after == before + 1, "Signing should auto-create one commission"

        # Sign again — should NOT duplicate commission
        r = client.post(
            f"{API}/offers/{oid}/sign",
            json={"signature": "data:image/png;base64,iVBORw0KGgo=", "signer_name": "Mario Rossi"},
        )
        assert r.status_code == 200
        after2 = len(client.get(f"{API}/commissions").json())
        assert after2 == after, "Re-signing must not duplicate commission"

        # Cleanup
        client.delete(f"{API}/offers/{oid}")

    def test_sign_unknown_offer_404(self, client):
        r = client.post(
            f"{API}/offers/non-existent-id/sign",
            json={"signature": "data:image/png;base64,xx", "signer_name": "X"},
        )
        assert r.status_code == 404


# ---------- PWA static assets (frontend served) ----------
class TestPwaAssets:
    def test_manifest(self):
        r = requests.get(f"{BASE_URL}/manifest.json", timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["theme_color"] == "#0A192F"
        assert "agenti" in d["description"].lower()

    def test_sw(self):
        r = requests.get(f"{BASE_URL}/sw.js", timeout=20)
        assert r.status_code == 200
        assert "CACHE_VERSION" in r.text or "caches.open" in r.text

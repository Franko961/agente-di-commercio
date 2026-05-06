"""
Backend API tests for Gestionale Agenti di Commercio
Tests cover: auth, clients, leads, appointments, offers, commissions,
mandanti, products, documents, automations, dashboard, AI.
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://visit-planner-32.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"

EMAIL = "agente@demo.it"
PASSWORD = "demo1234"


# ---------- Fixtures ----------
@pytest.fixture(scope="session")
def auth_token():
    r = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    if r.status_code != 200:
        pytest.skip(f"Login failed: {r.status_code} {r.text}")
    return r.json()["token"]


@pytest.fixture(scope="session")
def client(auth_token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"})
    return s


# ---------- Auth ----------
class TestAuth:
    def test_login_success(self):
        r = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD})
        assert r.status_code == 200
        d = r.json()
        assert "token" in d and isinstance(d["token"], str) and len(d["token"]) > 10
        assert d["email"] == EMAIL
        assert "password_hash" not in d

    def test_login_invalid(self):
        r = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": "wrong"})
        assert r.status_code == 401

    def test_me(self, client):
        r = client.get(f"{API}/auth/me")
        assert r.status_code == 200
        assert r.json()["email"] == EMAIL

    def test_me_no_auth(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401


# ---------- Dashboard ----------
class TestDashboard:
    def test_dashboard_stats(self, client):
        r = client.get(f"{API}/dashboard/stats")
        assert r.status_code == 200
        d = r.json()
        assert "kpi" in d and "by_zone" in d and "monthly" in d and "pipeline" in d
        kpi = d["kpi"]
        for k in ["clients_count", "revenue_won", "commissions_accrued", "monthly_goal"]:
            assert k in kpi
        assert kpi["clients_count"] >= 8


# ---------- Clients ----------
class TestClients:
    def test_list_clients(self, client):
        r = client.get(f"{API}/clients")
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d, list)
        assert len(d) >= 8
        assert all("company_name" in c and "_id" not in c for c in d)

    def test_filter_by_zone(self, client):
        r = client.get(f"{API}/clients?zone=Lombardia")
        assert r.status_code == 200
        for c in r.json():
            assert c["zone"] == "Lombardia"

    def test_filter_by_potential(self, client):
        r = client.get(f"{API}/clients?potential=alto")
        assert r.status_code == 200
        for c in r.json():
            assert c["potential"] == "alto"

    def test_search_q(self, client):
        r = client.get(f"{API}/clients?q=Milano")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_crud_client(self, client):
        payload = {"company_name": "TEST_Acme SRL", "city": "Roma", "zone": "Lazio",
                   "sector": "Industria", "potential": "medio", "lat": 41.9, "lng": 12.5}
        r = client.post(f"{API}/clients", json=payload)
        assert r.status_code == 200
        cid = r.json()["id"]

        r = client.get(f"{API}/clients/{cid}")
        assert r.status_code == 200
        d = r.json()
        assert d["client"]["company_name"] == "TEST_Acme SRL"
        assert "offers" in d and "appointments" in d and "documents" in d and "commissions" in d

        payload["company_name"] = "TEST_Acme Updated"
        r = client.put(f"{API}/clients/{cid}", json=payload)
        assert r.status_code == 200

        r = client.get(f"{API}/clients/{cid}")
        assert r.json()["client"]["company_name"] == "TEST_Acme Updated"

        r = client.delete(f"{API}/clients/{cid}")
        assert r.status_code == 200
        r = client.get(f"{API}/clients/{cid}")
        assert r.status_code == 404


# ---------- Leads ----------
class TestLeads:
    def test_list_leads(self, client):
        r = client.get(f"{API}/leads")
        assert r.status_code == 200 and len(r.json()) >= 5

    def test_lead_crud_and_status(self, client):
        payload = {"company_name": "TEST_Lead Co", "status": "nuovo", "estimated_value": 1000}
        r = client.post(f"{API}/leads", json=payload)
        assert r.status_code == 200
        lid = r.json()["id"]

        r = client.patch(f"{API}/leads/{lid}/status", json={"status": "qualificato"})
        assert r.status_code == 200
        leads = client.get(f"{API}/leads").json()
        assert any(l["id"] == lid and l["status"] == "qualificato" for l in leads)

        client.delete(f"{API}/leads/{lid}")


# ---------- Appointments ----------
class TestAppointments:
    def test_appointments(self, client):
        r = client.get(f"{API}/appointments")
        assert r.status_code == 200 and len(r.json()) >= 5

    def test_appt_crud(self, client):
        from datetime import datetime, timezone, timedelta
        start = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        payload = {"title": "TEST_Visita", "start": start, "status": "pianificato"}
        r = client.post(f"{API}/appointments", json=payload)
        assert r.status_code == 200
        aid = r.json()["id"]
        r = client.put(f"{API}/appointments/{aid}", json={**payload, "title": "TEST_Updated"})
        assert r.status_code == 200
        r = client.delete(f"{API}/appointments/{aid}")
        assert r.status_code == 200


# ---------- Mandanti ----------
class TestMandanti:
    def test_list_mandanti(self, client):
        r = client.get(f"{API}/mandanti")
        assert r.status_code == 200
        d = r.json()
        assert len(d) >= 3

    def test_mandante_crud(self, client):
        r = client.post(f"{API}/mandanti", json={"name": "TEST_Mand", "commission_rate": 7.5})
        assert r.status_code == 200
        mid = r.json()["id"]
        r = client.put(f"{API}/mandanti/{mid}", json={"name": "TEST_Mand Up", "commission_rate": 8.0})
        assert r.status_code == 200
        r = client.delete(f"{API}/mandanti/{mid}")
        assert r.status_code == 200


# ---------- Products ----------
class TestProducts:
    def test_list_products(self, client):
        r = client.get(f"{API}/products")
        assert r.status_code == 200 and len(r.json()) >= 5

    def test_filter_by_mandante(self, client):
        mandanti = client.get(f"{API}/mandanti").json()
        mid = mandanti[0]["id"]
        r = client.get(f"{API}/products?mandante_id={mid}")
        assert r.status_code == 200
        for p in r.json():
            assert p["mandante_id"] == mid

    def test_product_crud(self, client):
        mandanti = client.get(f"{API}/mandanti").json()
        payload = {"mandante_id": mandanti[0]["id"], "name": "TEST_Prod", "price": 10.0}
        r = client.post(f"{API}/products", json=payload)
        assert r.status_code == 200
        pid = r.json()["id"]
        client.delete(f"{API}/products/{pid}")


# ---------- Offers & Commissions ----------
class TestOffers:
    def test_list_offers(self, client):
        r = client.get(f"{API}/offers")
        assert r.status_code == 200 and len(r.json()) >= 3

    def test_offer_status_creates_commission(self, client):
        clients_l = client.get(f"{API}/clients").json()
        mandanti = client.get(f"{API}/mandanti").json()
        payload = {
            "client_id": clients_l[0]["id"], "mandante_id": mandanti[0]["id"],
            "title": "TEST_Offer", "status": "bozza",
            "items": [{"description": "Item", "quantity": 2, "unit_price": 100, "discount": 0}],
        }
        r = client.post(f"{API}/offers", json=payload)
        assert r.status_code == 200
        offer = r.json()
        assert offer["total"] == 200.0
        oid = offer["id"]

        before = len(client.get(f"{API}/commissions").json())
        r = client.patch(f"{API}/offers/{oid}/status", json={"status": "accettata"})
        assert r.status_code == 200
        after = len(client.get(f"{API}/commissions").json())
        assert after == before + 1

        client.delete(f"{API}/offers/{oid}")


class TestCommissions:
    def test_list(self, client):
        r = client.get(f"{API}/commissions")
        assert r.status_code == 200
        d = r.json()
        assert len(d) >= 2

    def test_status_toggle(self, client):
        comms = client.get(f"{API}/commissions").json()
        cid = comms[0]["id"]
        old = comms[0]["status"]
        new = "incassato" if old == "maturato" else "maturato"
        r = client.patch(f"{API}/commissions/{cid}/status", json={"status": new})
        assert r.status_code == 200
        updated = client.get(f"{API}/commissions").json()
        assert next(c for c in updated if c["id"] == cid)["status"] == new
        # restore
        client.patch(f"{API}/commissions/{cid}/status", json={"status": old})


# ---------- Documents ----------
class TestDocuments:
    def test_doc_crud(self, client):
        r = client.get(f"{API}/documents")
        assert r.status_code == 200
        r = client.post(f"{API}/documents", json={"name": "TEST_Doc", "category": "altro"})
        assert r.status_code == 200
        did = r.json()["id"]
        r = client.delete(f"{API}/documents/{did}")
        assert r.status_code == 200


# ---------- Automations ----------
class TestAutomations:
    def test_list(self, client):
        r = client.get(f"{API}/automations")
        assert r.status_code == 200 and len(r.json()) >= 3

    def test_crud(self, client):
        payload = {"name": "TEST_Auto", "trigger": "offer_expiring", "action": "send_reminder",
                   "enabled": True, "config": {"days_before": 5}}
        r = client.post(f"{API}/automations", json=payload)
        assert r.status_code == 200
        aid = r.json()["id"]
        r = client.put(f"{API}/automations/{aid}", json={**payload, "enabled": False})
        assert r.status_code == 200
        client.delete(f"{API}/automations/{aid}")


# ---------- AI ----------
class TestAI:
    def test_ai_chat(self, client):
        r = client.post(f"{API}/ai/chat",
                        json={"message": "Quali clienti devo visitare per primi?"},
                        timeout=90)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "response" in d
        assert isinstance(d["response"], str) and len(d["response"]) > 10

    def test_ai_suggestions(self, client):
        r = client.get(f"{API}/ai/suggestions", timeout=90)
        assert r.status_code == 200
        assert "suggestions" in r.json()

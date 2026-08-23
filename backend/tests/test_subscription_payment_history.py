"""
Verifica services/subscription_service.py: get_payment_history, lo storico
pagamenti unificato Stripe + PayPal mostrato nell'area abbonamento
(GET /api/subscription/payment-history).

Copre:
- Stripe: le fatture (stripe.Invoice.list) vengono normalizzate in item con
  provider/date/amount/currency/status/receipt_url.
- PayPal: le transazioni dell'abbonamento vengono normalizzate allo stesso
  modo, con l'intervallo start_time/end_time richiesto da PayPal.
- I due provider sono indipendenti: se uno configurato fallisce/non
  risponde, l'altro viene comunque restituito (mai un errore totale).
- Utente senza alcun provider configurato -> lista vuota, nessuna chiamata
  di rete.
- L'elenco combinato è ordinato dal più recente al più vecchio.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_subscription_payment_history.py -v
"""
import sys
import asyncio

sys.path.insert(0, ".")

import services.subscription_service as subscription_mod
from services.subscription_service import SubscriptionService


def run(coro):
    return asyncio.run(coro)


class FakeUserRepo:
    def __init__(self, users_by_id):
        self.users_by_id = users_by_id

    async def find_by_id(self, uid):
        return self.users_by_id.get(uid)


class FakeResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = str(self._json)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception("http error")

    def json(self):
        return self._json


class FakeRequestsPayPal:
    def __init__(self, transactions):
        self.transactions = transactions
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return FakeResponse(200, {"access_token": "fake-token"})

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return FakeResponse(200, {"transactions": self.transactions})


def _install_fake_stripe(monkeypatch, invoices):
    class FakeStripeInvoice:
        @staticmethod
        def list(customer=None, limit=None):
            return {"data": invoices}

    fake_stripe_module = type("FakeStripe", (), {"api_key": None, "Invoice": FakeStripeInvoice})
    monkeypatch.setitem(sys.modules, "stripe", fake_stripe_module)


# ---------- Stripe ----------

def test_storico_stripe_normalizza_le_fatture(monkeypatch):
    monkeypatch.setattr(subscription_mod, "STRIPE_SECRET_KEY", "sk_test_fake")
    _install_fake_stripe(monkeypatch, [
        {"created": 1750000000, "amount_paid": 1100, "currency": "eur", "status": "paid",
         "hosted_invoice_url": "https://stripe.example/inv1"},
    ])

    user = {"id": "user-1"}
    repo = FakeUserRepo({"user-1": {"id": "user-1", "stripe_customer_id": "cus_123"}})
    service = SubscriptionService(repo=repo)

    result = run(service.get_payment_history(user))

    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item["provider"] == "stripe"
    assert item["amount"] == 11.0
    assert item["currency"] == "EUR"
    assert item["status"] == "paid"
    assert item["receipt_url"] == "https://stripe.example/inv1"


def test_storico_senza_stripe_customer_id_non_chiama_stripe(monkeypatch):
    monkeypatch.setattr(subscription_mod, "STRIPE_SECRET_KEY", "sk_test_fake")
    calls = []

    class FakeStripeInvoice:
        @staticmethod
        def list(customer=None, limit=None):
            calls.append(customer)
            return {"data": []}

    fake_stripe_module = type("FakeStripe", (), {"api_key": None, "Invoice": FakeStripeInvoice})
    monkeypatch.setitem(sys.modules, "stripe", fake_stripe_module)

    user = {"id": "user-1"}
    repo = FakeUserRepo({"user-1": {"id": "user-1"}})
    service = SubscriptionService(repo=repo)

    result = run(service.get_payment_history(user))

    assert result["items"] == []
    assert calls == []


# ---------- PayPal ----------

def test_storico_paypal_normalizza_le_transazioni(monkeypatch):
    monkeypatch.setattr(subscription_mod, "STRIPE_SECRET_KEY", "")
    monkeypatch.setattr(subscription_mod, "PAYPAL_CLIENT_ID", "cid")
    monkeypatch.setattr(subscription_mod, "PAYPAL_CLIENT_SECRET", "secret")

    fake_requests = FakeRequestsPayPal([
        {"time": "2026-06-01T10:00:00Z", "status": "COMPLETED",
         "amount_with_breakdown": {"gross_amount": {"value": "6.00", "currency_code": "EUR"}}},
    ])
    monkeypatch.setattr(subscription_mod, "requests", fake_requests)

    user = {"id": "user-2"}
    repo = FakeUserRepo({"user-2": {"id": "user-2", "paypal_subscription_id": "I-FAKE123"}})
    service = SubscriptionService(repo=repo)

    result = run(service.get_payment_history(user))

    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item["provider"] == "paypal"
    assert item["date"] == "2026-06-01T10:00:00Z"
    assert item["amount"] == 6.0
    assert item["currency"] == "EUR"
    assert item["status"] == "COMPLETED"

    get_calls = [c for c in fake_requests.calls if c[0] == "GET"]
    assert len(get_calls) == 1
    assert "start_time" in get_calls[0][2]["params"]
    assert "end_time" in get_calls[0][2]["params"]


# ---------- Combinato / resilienza ----------

def test_storico_combina_e_ordina_dal_piu_recente(monkeypatch):
    monkeypatch.setattr(subscription_mod, "STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(subscription_mod, "PAYPAL_CLIENT_ID", "cid")
    monkeypatch.setattr(subscription_mod, "PAYPAL_CLIENT_SECRET", "secret")

    _install_fake_stripe(monkeypatch, [
        {"created": 1700000000, "amount_paid": 600, "currency": "eur", "status": "paid",
         "hosted_invoice_url": None},
    ])
    fake_requests = FakeRequestsPayPal([
        {"time": "2026-06-01T10:00:00Z", "status": "COMPLETED",
         "amount_with_breakdown": {"gross_amount": {"value": "6.00", "currency_code": "EUR"}}},
    ])
    monkeypatch.setattr(subscription_mod, "requests", fake_requests)

    user = {"id": "user-3"}
    repo = FakeUserRepo({"user-3": {
        "id": "user-3", "stripe_customer_id": "cus_1", "paypal_subscription_id": "I-FAKE1",
    }})
    service = SubscriptionService(repo=repo)

    result = run(service.get_payment_history(user))

    assert len(result["items"]) == 2
    # Il pagamento PayPal (2026) è più recente della fattura Stripe (2023 circa)
    assert result["items"][0]["provider"] == "paypal"
    assert result["items"][1]["provider"] == "stripe"


def test_storico_stripe_fallisce_ma_paypal_resta_disponibile(monkeypatch):
    monkeypatch.setattr(subscription_mod, "STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(subscription_mod, "PAYPAL_CLIENT_ID", "cid")
    monkeypatch.setattr(subscription_mod, "PAYPAL_CLIENT_SECRET", "secret")

    class FailingStripeInvoice:
        @staticmethod
        def list(customer=None, limit=None):
            raise Exception("Stripe non raggiungibile")

    fake_stripe_module = type("FakeStripe", (), {"api_key": None, "Invoice": FailingStripeInvoice})
    monkeypatch.setitem(sys.modules, "stripe", fake_stripe_module)

    fake_requests = FakeRequestsPayPal([
        {"time": "2026-06-01T10:00:00Z", "status": "COMPLETED",
         "amount_with_breakdown": {"gross_amount": {"value": "6.00", "currency_code": "EUR"}}},
    ])
    monkeypatch.setattr(subscription_mod, "requests", fake_requests)

    user = {"id": "user-4"}
    repo = FakeUserRepo({"user-4": {
        "id": "user-4", "stripe_customer_id": "cus_1", "paypal_subscription_id": "I-FAKE1",
    }})
    service = SubscriptionService(repo=repo)

    result = run(service.get_payment_history(user))

    assert len(result["items"]) == 1
    assert result["items"][0]["provider"] == "paypal"


def test_storico_utente_senza_provider_configurato_e_vuoto(monkeypatch):
    monkeypatch.setattr(subscription_mod, "STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(subscription_mod, "PAYPAL_CLIENT_ID", "cid")
    monkeypatch.setattr(subscription_mod, "PAYPAL_CLIENT_SECRET", "secret")

    user = {"id": "user-5"}
    repo = FakeUserRepo({"user-5": {"id": "user-5"}})
    service = SubscriptionService(repo=repo)

    result = run(service.get_payment_history(user))

    assert result == {"items": []}

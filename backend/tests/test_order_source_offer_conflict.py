"""
Verifica la protezione contro la doppia conversione offerta -> ordine
(order_service.create_from_offer):

- check-then-act "normale": se un ordine per questa offerta esiste già,
  create_from_offer lo restituisce senza crearne un secondo;
- rete di sicurezza per la race condition che il check da solo non copre
  (due richieste concorrenti sulla stessa offerta, es. pulsante di stato e
  firma digitale quasi simultanei): l'indice univoco DB su
  (user_id, source_offer_id) — vedi startup_service — blocca il secondo
  insert, e create_from_offer deve recuperare e restituire l'ordine appena
  creato dall'altra richiesta invece di propagare l'errore all'utente.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_order_source_offer_conflict.py -v
"""
import sys
import asyncio

import pytest

sys.path.insert(0, ".")

from core.exceptions import ConflictError
import services.order_service as order_service_mod
from services.order_service import OrderService


def run(coro):
    return asyncio.run(coro)


class FakeMandanteRepo:
    def __init__(self):
        self.docs = {}

    async def find_one(self, mid, user_id):
        return self.docs.get(mid)


class FakeCommissionRepo:
    def __init__(self):
        self.docs = []

    async def find_many(self, user_id, mandante_id=None):
        return [d for d in self.docs if d["user_id"] == user_id]

    async def find_by_order(self, order_id, user_id):
        return [d for d in self.docs if d.get("order_id") == order_id]

    async def delete_by_order(self, order_id, user_id):
        self.docs = [d for d in self.docs if d.get("order_id") != order_id]

    async def insert(self, doc):
        self.docs.append(doc)
        return doc


class FakeCommissionService:
    def __init__(self):
        self.repo = FakeCommissionRepo()

    async def check_and_award_bonus(self, user_id, mandante_id):
        pass


class FakeOrderRepo:
    """Applica DAVVERO l'unicità di (user_id, source_offer_id), come farebbe
    l'indice univoco reale in MongoDB."""

    def __init__(self):
        self.docs = {}
        self._counters = {}

    async def find_by_source_offer(self, offer_id, user_id):
        return next(
            (dict(d) for d in self.docs.values() if d.get("source_offer_id") == offer_id and d["user_id"] == user_id),
            None,
        )

    async def find_one(self, oid, user_id):
        d = self.docs.get(oid)
        return dict(d) if d and d["user_id"] == user_id else None

    async def insert(self, doc):
        collide = any(
            d["user_id"] == doc["user_id"] and d.get("source_offer_id") == doc.get("source_offer_id")
            for d in self.docs.values()
            if doc.get("source_offer_id") is not None
        )
        if collide:
            raise ConflictError("Esiste già un ordine creato da questa offerta")
        self.docs[doc["id"]] = doc
        return doc

    async def next_order_number(self, user_id):
        self._counters[user_id] = self._counters.get(user_id, 0) + 1
        return f"ORD-{self._counters[user_id]:04d}"


class RaceOrderRepo(FakeOrderRepo):
    """Simula esattamente l'interleaving della race condition: il check
    preventivo (find_by_source_offer) non vede ancora nulla, ma tra il check
    e l'insert un'altra richiesta "concorrente" ha già scritto l'ordine —
    esattamente il buco che il solo check-then-act non copre, e per cui
    serve l'indice univoco DB come ultima difesa."""

    def __init__(self, offer_id, user_id, concurrent_order):
        super().__init__()
        self._offer_id = offer_id
        self._user_id = user_id
        self._concurrent_order = concurrent_order
        self._check_calls = 0

    async def find_by_source_offer(self, offer_id, user_id):
        self._check_calls += 1
        if self._check_calls == 1:
            # Primo check dentro create_from_offer: non vede ancora nulla.
            return None
        # Secondo check (dopo il ConflictError catturato): l'ordine "creato
        # nel frattempo dall'altra richiesta" è ora visibile.
        return dict(self._concurrent_order)

    async def insert(self, doc):
        if doc.get("source_offer_id") == self._offer_id and doc["user_id"] == self._user_id:
            raise ConflictError("Esiste già un ordine creato da questa offerta")
        self.docs[doc["id"]] = doc
        return doc


def build_service(monkeypatch, order_repo):
    fake_commission_service = FakeCommissionService()
    monkeypatch.setattr(order_service_mod, "commission_service", fake_commission_service)
    return OrderService(repo=order_repo, mandante_repo=FakeMandanteRepo())


FAKE_ITEMS = [{"description": "Prodotto test", "quantity": 1, "unit_price": 100, "discount": 0}]
USER = {"id": "user-1"}
OFFER = {"id": "offer-1", "client_id": "c-1", "mandante_id": "m-1", "items": FAKE_ITEMS, "sale_type": "nuovo", "notes": ""}


def test_seconda_conversione_della_stessa_offerta_non_duplica(monkeypatch):
    repo = FakeOrderRepo()
    service = build_service(monkeypatch, repo)

    d1 = run(service.create_from_offer(USER, OFFER))
    d2 = run(service.create_from_offer(USER, OFFER))

    assert d1["id"] == d2["id"]
    assert len(repo.docs) == 1


def test_race_condition_su_insert_concorrente_recupera_ordine_esistente_senza_errore(monkeypatch):
    concurrent_order = {
        "id": "order-from-other-request", "user_id": "user-1", "client_id": "c-1", "mandante_id": "m-1",
        "items": FAKE_ITEMS, "total": 100, "numero_ordine": "ORD-0001", "status": "confermato",
        "source_offer_id": "offer-1", "created_at": "2026-01-01T00:00:00",
    }
    repo = RaceOrderRepo(offer_id="offer-1", user_id="user-1", concurrent_order=concurrent_order)
    service = build_service(monkeypatch, repo)

    # Il check preventivo non vede nulla (return None al primo giro), ma
    # l'insert collide comunque: create_from_offer NON deve propagare il
    # ConflictError, deve restituire l'ordine dell'altra richiesta.
    result = run(service.create_from_offer(USER, OFFER))

    assert result["id"] == "order-from-other-request"


def test_race_senza_ordine_concorrente_effettivamente_esistente_rilancia(monkeypatch):
    """Se il conflitto non è dovuto a una race genuina (es. bug/stato
    inatteso) e il secondo check non trova comunque nulla, l'errore deve
    essere propagato invece di fallire silenziosamente."""
    class AlwaysConflictingRepo(FakeOrderRepo):
        async def insert(self, doc):
            raise ConflictError("Esiste già un ordine creato da questa offerta")

    repo = AlwaysConflictingRepo()
    service = build_service(monkeypatch, repo)

    with pytest.raises(ConflictError):
        run(service.create_from_offer(USER, OFFER))


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

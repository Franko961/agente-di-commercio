"""
Test per le nuove funzionalità del modulo Ordini: modifica (PUT), aggiornamento
mirato di stato/pagamento/consegna (PATCH /status), numero ordine progressivo,
e soprattutto la risincronizzazione della provvigione collegata — che prima
di questo lavoro richiedeva cancellare e ricreare l'intero ordine per essere
corretta dopo una modifica.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_orders_update.py -v
"""

import asyncio
import sys

import pytest

sys.path.insert(0, ".")

import services.order_service as order_service_mod
from core.exceptions import NotFoundError
from models.order import OrderIn, OrderStatusIn
from services.order_service import OrderService


def run(coro):
    return asyncio.run(coro)


class FakeOrderRepo:
    def __init__(self):
        self.docs = {}
        self._counters = {}

    async def find_many(self, user_id, mandante_id=None):
        docs = [d for d in self.docs.values() if d["user_id"] == user_id]
        if mandante_id:
            docs = [d for d in docs if d["mandante_id"] == mandante_id]
        return docs

    async def find_by_client(self, user_id, client_id):
        return [
            d
            for d in self.docs.values()
            if d["user_id"] == user_id and d["client_id"] == client_id
        ]

    async def find_by_source_offer(self, offer_id, user_id):
        return next(
            (
                d
                for d in self.docs.values()
                if d.get("source_offer_id") == offer_id and d["user_id"] == user_id
            ),
            None,
        )

    async def find_one(self, oid, user_id):
        d = self.docs.get(oid)
        return dict(d) if d and d["user_id"] == user_id else None

    async def insert(self, doc):
        self.docs[doc["id"]] = doc
        return doc

    async def update(self, oid, user_id, data):
        self.docs[oid].update(data)

    async def update_fields(self, oid, user_id, data):
        if oid in self.docs:
            self.docs[oid].update(data)
            return True
        return False

    async def delete(self, oid, user_id):
        self.docs.pop(oid, None)

    async def next_order_number(self, user_id):
        self._counters[user_id] = self._counters.get(user_id, 0) + 1
        return f"ORD-{self._counters[user_id]:04d}"


class FakeCommissionRepo:
    def __init__(self):
        self.docs = []

    async def find_many(self, user_id, mandante_id=None):
        docs = [d for d in self.docs if d["user_id"] == user_id]
        if mandante_id:
            docs = [d for d in docs if d["mandante_id"] == mandante_id]
        return docs

    async def find_by_order(self, order_id, user_id):
        return [
            d
            for d in self.docs
            if d.get("order_id") == order_id and d["user_id"] == user_id
        ]

    async def delete_by_order(self, order_id, user_id):
        self.docs = [
            d
            for d in self.docs
            if not (d.get("order_id") == order_id and d["user_id"] == user_id)
        ]

    async def insert(self, doc):
        self.docs.append(doc)
        return doc


class FakeMandanteRepo:
    def __init__(self, mandanti_by_id):
        self.mandanti_by_id = mandanti_by_id

    async def find_one(self, mid, user_id):
        return self.mandanti_by_id.get(mid)


class FakeClientRepo:
    def __init__(self, clients_by_id):
        self.clients_by_id = clients_by_id

    async def find_one(self, cid, user_id):
        return self.clients_by_id.get(cid)


class FakeCommissionService:
    """Sostituisce il modulo commission_service usato internamente da
    order_service: espone repo (FakeCommissionRepo) e traccia le chiamate a
    check_and_award_bonus per verificare che vengano fatte per il mandante
    giusto, senza dover testare anche la logica della scala premi qui."""

    def __init__(self, mandanti_by_id):
        self.repo = FakeCommissionRepo()
        self.bonus_calls = []

    async def check_and_award_bonus(self, user_id, mandante_id):
        self.bonus_calls.append(mandante_id)


USER = {"id": "u1"}
MANDANTI = {
    "m1": {
        "id": "m1",
        "user_id": "u1",
        "name": "Mandante Uno",
        "commission_rate": 10.0,
    },
    "m2": {
        "id": "m2",
        "user_id": "u1",
        "name": "Mandante Due",
        "commission_rate": 20.0,
    },
}
CLIENTI = {
    "c1": {"id": "c1", "user_id": "u1", "company_name": "Cliente Uno"},
}


def build_service(monkeypatch):
    order_repo = FakeOrderRepo()
    mandante_repo = FakeMandanteRepo(MANDANTI)
    client_repo = FakeClientRepo(CLIENTI)
    fake_commission_service = FakeCommissionService(MANDANTI)
    # commission_service è importato per nome dentro order_service: va
    # sostituito lì, non nel modulo commission_service originale.
    monkeypatch.setattr(
        order_service_mod, "commission_service", fake_commission_service
    )
    service = OrderService(
        repo=order_repo, mandante_repo=mandante_repo, client_repo=client_repo
    )
    return service, order_repo, fake_commission_service


def _order_payload(**overrides):
    base = dict(
        client_id="c1",
        mandante_id="m1",
        sale_type="nuovo",
        notes="",
        items=[
            {
                "description": "Prodotto A",
                "quantity": 2,
                "unit_price": 100,
                "discount": 0,
            }
        ],
    )
    base.update(overrides)
    return OrderIn(**base)


def test_numero_ordine_generato_automaticamente_se_assente(monkeypatch):
    service, order_repo, _ = build_service(monkeypatch)
    order = run(service.create_order(USER, _order_payload()))
    assert order["numero_ordine"] == "ORD-0001"

    order2 = run(service.create_order(USER, _order_payload()))
    assert order2["numero_ordine"] == "ORD-0002"


def test_numero_ordine_esplicito_viene_rispettato(monkeypatch):
    service, order_repo, _ = build_service(monkeypatch)
    order = run(service.create_order(USER, _order_payload(numero_ordine="PO-2026-77")))
    assert order["numero_ordine"] == "PO-2026-77"


def test_update_order_ricalcola_totale_e_rigenera_provvigione(monkeypatch):
    service, order_repo, fake_cs = build_service(monkeypatch)
    order = run(service.create_order(USER, _order_payload()))
    # Totale iniziale: 2 x 100 = 200, provvigione al 10% = 20
    assert order["total"] == 200
    comm = fake_cs.repo.docs[0]
    assert comm["amount"] == 20

    # Modifica: 5 unità invece di 2 -> totale 500, provvigione 50
    updated_payload = _order_payload(
        items=[
            {
                "description": "Prodotto A",
                "quantity": 5,
                "unit_price": 100,
                "discount": 0,
            }
        ]
    )
    run(service.update_order(USER, order["id"], updated_payload))

    stored = run(order_repo.find_one(order["id"], "u1"))
    assert stored["total"] == 500
    assert (
        len(fake_cs.repo.docs) == 1
    )  # la vecchia provvigione è stata sostituita, non duplicata
    assert fake_cs.repo.docs[0]["amount"] == 50


def test_update_order_cambio_mandante_ricalcola_bonus_per_entrambi(monkeypatch):
    service, order_repo, fake_cs = build_service(monkeypatch)
    order = run(service.create_order(USER, _order_payload(mandante_id="m1")))
    fake_cs.bonus_calls.clear()  # ignora la chiamata fatta alla creazione

    updated_payload = _order_payload(mandante_id="m2")
    run(service.update_order(USER, order["id"], updated_payload))

    # La provvigione ora appartiene a m2, con l'aliquota di m2 (20%, non più 10%)
    assert fake_cs.repo.docs[0]["mandante_id"] == "m2"
    assert fake_cs.repo.docs[0]["amount"] == 200 * 0.20
    # I bonus vanno ricalcolati per ENTRAMBI i mandanti: m1 potrebbe aver perso
    # uno scaglione, m2 potrebbe averne raggiunto uno nuovo.
    assert set(fake_cs.bonus_calls) == {"m1", "m2"}


def test_annullamento_ordine_rimuove_provvigione_senza_cancellare_ordine(monkeypatch):
    service, order_repo, fake_cs = build_service(monkeypatch)
    order = run(service.create_order(USER, _order_payload()))
    assert len(fake_cs.repo.docs) == 1

    run(
        service.update_order_status(
            USER, order["id"], OrderStatusIn(status="annullato")
        )
    )

    assert len(fake_cs.repo.docs) == 0
    stored = run(order_repo.find_one(order["id"], "u1"))
    assert stored is not None  # l'ordine resta, solo la provvigione è sparita
    assert stored["status"] == "annullato"


def test_riattivazione_ordine_annullato_rigenera_provvigione(monkeypatch):
    service, order_repo, fake_cs = build_service(monkeypatch)
    order = run(service.create_order(USER, _order_payload()))
    run(
        service.update_order_status(
            USER, order["id"], OrderStatusIn(status="annullato")
        )
    )
    assert len(fake_cs.repo.docs) == 0

    run(
        service.update_order_status(
            USER, order["id"], OrderStatusIn(status="confermato")
        )
    )

    assert len(fake_cs.repo.docs) == 1
    assert fake_cs.repo.docs[0]["order_id"] == order["id"]


def test_update_status_parziale_non_tocca_campi_omessi(monkeypatch):
    service, order_repo, _ = build_service(monkeypatch)
    order = run(service.create_order(USER, _order_payload()))

    run(
        service.update_order_status(
            USER, order["id"], OrderStatusIn(payment_status="pagato")
        )
    )

    stored = run(order_repo.find_one(order["id"], "u1"))
    assert stored["payment_status"] == "pagato"
    assert stored["status"] == "confermato"  # invariato: non era nella richiesta


def test_get_order_include_provvigione_collegata(monkeypatch):
    service, order_repo, fake_cs = build_service(monkeypatch)
    order = run(service.create_order(USER, _order_payload()))

    fetched = run(service.get_order(USER, order["id"]))

    assert fetched["commission"] is not None
    assert fetched["commission"]["order_id"] == order["id"]


# ---------- Validazione ownership di client_id/mandante_id ----------


def test_create_order_rifiuta_client_id_di_un_altro_utente(monkeypatch):
    service, order_repo, _ = build_service(monkeypatch)
    with pytest.raises(NotFoundError):
        run(
            service.create_order(USER, _order_payload(client_id="c-di-un-altro-utente"))
        )
    assert order_repo.docs == {}


def test_create_order_rifiuta_mandante_id_di_un_altro_utente(monkeypatch):
    service, order_repo, _ = build_service(monkeypatch)
    with pytest.raises(NotFoundError):
        run(
            service.create_order(
                USER, _order_payload(mandante_id="m-di-un-altro-utente")
            )
        )
    assert order_repo.docs == {}


def test_update_order_rifiuta_client_id_di_un_altro_utente(monkeypatch):
    service, order_repo, _ = build_service(monkeypatch)
    order = run(service.create_order(USER, _order_payload()))

    with pytest.raises(NotFoundError):
        run(
            service.update_order(
                USER, order["id"], _order_payload(client_id="c-di-un-altro-utente")
            )
        )

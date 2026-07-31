"""
Verifica che OfferService.create_offer/update_offer rifiutino un client_id o
mandante_id che non appartiene all'utente. Prima di questa modifica venivano
accettati e salvati così come arrivavano dal payload, senza alcuna verifica
di ownership (a differenza di update_client/get_client, che verificano
sempre) — un id di un altro utente indovinato o enumerato veniva comunque
scritto sull'offerta.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_offer_service_ownership.py -v
"""
import sys
import asyncio

import pytest

sys.path.insert(0, ".")

from core.exceptions import NotFoundError
from models.offer import OfferIn
from services.offer_service import OfferService


def run(coro):
    return asyncio.run(coro)


class FakeOfferRepo:
    def __init__(self):
        self.docs = {}

    async def insert(self, doc):
        self.docs[doc["id"]] = doc
        return doc

    async def update(self, oid, user_id, data):
        self.docs[oid].update(data)

    async def find_one(self, oid, user_id):
        d = self.docs.get(oid)
        return dict(d) if d and d["user_id"] == user_id else None


class FakeLookupRepo:
    def __init__(self, docs_by_id):
        self.docs_by_id = docs_by_id

    async def find_one(self, rid, user_id):
        return self.docs_by_id.get(rid)


USER = {"id": "u1"}
CLIENTI = {"c1": {"id": "c1", "user_id": "u1", "company_name": "Cliente Uno"}}
MANDANTI = {"m1": {"id": "m1", "user_id": "u1", "name": "Mandante Uno"}}


def build_service():
    offer_repo = FakeOfferRepo()
    service = OfferService(
        repo=offer_repo,
        mandante_repo=FakeLookupRepo(MANDANTI),
        client_repo=FakeLookupRepo(CLIENTI),
    )
    return service, offer_repo


def _offer_payload(**overrides):
    base = dict(
        client_id="c1", mandante_id="m1", title="Offerta test",
        items=[{"description": "Prodotto A", "quantity": 1, "unit_price": 100, "discount": 0}],
    )
    base.update(overrides)
    return OfferIn(**base)


def test_create_offer_con_client_id_e_mandante_id_validi_funziona():
    service, offer_repo = build_service()
    offer = run(service.create_offer(USER, _offer_payload()))
    assert offer["client_id"] == "c1"
    assert len(offer_repo.docs) == 1


def test_create_offer_rifiuta_client_id_di_un_altro_utente():
    service, offer_repo = build_service()
    with pytest.raises(NotFoundError):
        run(service.create_offer(USER, _offer_payload(client_id="c-di-un-altro-utente")))
    assert offer_repo.docs == {}


def test_create_offer_rifiuta_mandante_id_di_un_altro_utente():
    service, offer_repo = build_service()
    with pytest.raises(NotFoundError):
        run(service.create_offer(USER, _offer_payload(mandante_id="m-di-un-altro-utente")))
    assert offer_repo.docs == {}


def test_update_offer_rifiuta_client_id_di_un_altro_utente():
    service, offer_repo = build_service()
    offer = run(service.create_offer(USER, _offer_payload()))

    with pytest.raises(NotFoundError):
        run(service.update_offer(USER, offer["id"], _offer_payload(client_id="c-di-un-altro-utente")))


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

"""
Verifica CommissionService.create_manual_commission/update_manual_commission/
delete_manual_commission: più righe manuali possono coesistere sullo stesso
periodo (nessun vincolo di unicità, vedi manual_commission_repository.py),
create genera un id, update/delete operano su quello, non più su period.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_manual_commission_service_crud.py -v
"""
import sys
import asyncio

import pytest
from core.exceptions import NotFoundError

sys.path.insert(0, ".")

from services.commission_service import CommissionService


def run(coro):
    return asyncio.run(coro)


class FakeManualRepo:
    def __init__(self):
        self.docs = {}

    async def insert(self, doc):
        self.docs[doc["id"]] = dict(doc)
        return doc

    async def find_many(self, user_id):
        return [d for d in self.docs.values() if d["user_id"] == user_id]

    async def update(self, cid, user_id, fields):
        existing = self.docs.get(cid)
        if not existing or existing["user_id"] != user_id:
            return False
        existing.update(fields)
        return True

    async def delete(self, cid, user_id):
        existing = self.docs.get(cid)
        if existing and existing["user_id"] == user_id:
            del self.docs[cid]


USER = {"id": "user-1"}
OTHER_USER = {"id": "user-2"}


def build_service():
    return CommissionService(repo=None, mandante_repo=None, manual_repo=FakeManualRepo())


def test_create_genera_un_id_e_salva_lutente():
    service = build_service()
    doc = run(service.create_manual_commission(USER, {"period": "2026-08", "amount": 300}))
    assert doc["id"]
    assert doc["user_id"] == "user-1"
    assert doc["amount"] == 300


def test_create_permette_righe_multiple_sullo_stesso_periodo():
    service = build_service()
    run(service.create_manual_commission(USER, {"period": "2026-08", "amount": 300, "mandante_id": "m-A"}))
    run(service.create_manual_commission(USER, {"period": "2026-08", "amount": 150, "mandante_id": "m-B"}))
    docs = run(service.list_manual_commissions(USER))
    assert len(docs) == 2
    assert sum(d["amount"] for d in docs) == 450


def test_update_modifica_la_riga_indicata():
    service = build_service()
    doc = run(service.create_manual_commission(USER, {"period": "2026-08", "amount": 300}))
    run(service.update_manual_commission(USER, doc["id"], {"period": "2026-08", "amount": 500}))
    docs = run(service.list_manual_commissions(USER))
    assert docs[0]["amount"] == 500


def test_update_di_un_id_inesistente_solleva_not_found():
    service = build_service()
    with pytest.raises(NotFoundError):
        run(service.update_manual_commission(USER, "non-esiste", {"amount": 100}))


def test_update_non_permette_di_modificare_la_riga_di_un_altro_utente():
    service = build_service()
    doc = run(service.create_manual_commission(OTHER_USER, {"period": "2026-08", "amount": 300}))
    with pytest.raises(NotFoundError):
        run(service.update_manual_commission(USER, doc["id"], {"amount": 999}))


def test_delete_rimuove_solo_la_riga_indicata():
    service = build_service()
    doc1 = run(service.create_manual_commission(USER, {"period": "2026-08", "amount": 300}))
    doc2 = run(service.create_manual_commission(USER, {"period": "2026-08", "amount": 150}))
    run(service.delete_manual_commission(USER, doc1["id"]))
    docs = run(service.list_manual_commissions(USER))
    assert len(docs) == 1
    assert docs[0]["id"] == doc2["id"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

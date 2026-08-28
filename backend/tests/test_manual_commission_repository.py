"""
Verifica ManualCommissionRepository: le provvigioni inserite manualmente
dall'utente sono una lista libera (più righe possono coesistere nello
stesso mese, es. un premio per un mandante e una rettifica per un altro),
che si sommano al totale calcolato dagli ordini (vedi
services/commission_service.py) per coprire provvigioni non tracciate
tramite il flusso ordini del CRM.

Usa un finto collection MongoDB che replica insert_one/update_one/delete_one
sul campo "id" (nessun indice composto univoco, a differenza della vecchia
struttura upsert-per-mese) — stesso approccio già validato per gli altri
repository di questo progetto.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_manual_commission_repository.py -v
"""

import asyncio
import sys

import pytest

sys.path.insert(0, ".")

from repositories.manual_commission_repository import ManualCommissionRepository


def run(coro):
    return asyncio.run(coro)


class FakeUpdateResult:
    def __init__(self, matched_count):
        self.matched_count = matched_count


class FakeMongoCollection:
    def __init__(self):
        self.docs = {}  # id -> dict

    def find(self, query, _projection=None):
        matches = [d for d in self.docs.values() if d["user_id"] == query["user_id"]]
        return _FakeCursor(matches)

    async def insert_one(self, doc):
        self.docs[doc["id"]] = dict(doc)

    async def update_one(self, query, update):
        existing = self.docs.get(query["id"])
        if not existing or existing["user_id"] != query["user_id"]:
            return FakeUpdateResult(matched_count=0)
        existing.update(update.get("$set", {}))
        return FakeUpdateResult(matched_count=1)

    async def delete_one(self, query):
        existing = self.docs.get(query["id"])
        if existing and existing["user_id"] == query["user_id"]:
            del self.docs[query["id"]]


class _FakeCursor:
    def __init__(self, items):
        self._items = items

    async def to_list(self, limit):
        return self._items[:limit]


def build_repo():
    repo = ManualCommissionRepository()
    repo.collection = FakeMongoCollection()
    return repo


def make_doc(cid, user_id, period, amount, **extra):
    return {"id": cid, "user_id": user_id, "period": period, "amount": amount, **extra}


def test_insert_crea_il_documento():
    repo = build_repo()
    run(repo.insert(make_doc("m-1", "user-1", "2026-08", 450)))
    docs = run(repo.find_many("user-1"))
    assert len(docs) == 1
    assert docs[0]["period"] == "2026-08"
    assert docs[0]["amount"] == 450
    assert docs[0]["created_at"] is not None
    assert docs[0]["updated_at"] is not None


def test_piu_righe_coesistono_sullo_stesso_mese():
    """Il caso che l'indice univoco precedente impediva: due righe manuali
    diverse nello stesso periodo (es. un premio per un mandante e una
    rettifica per un altro)."""
    repo = build_repo()
    run(
        repo.insert(
            make_doc("m-1", "user-1", "2026-08", 300, mandante_id="m-A", tipo="bonus")
        )
    )
    run(
        repo.insert(
            make_doc(
                "m-2", "user-1", "2026-08", 150, mandante_id="m-B", tipo="rettifica"
            )
        )
    )
    docs = run(repo.find_many("user-1"))
    assert len(docs) == 2
    assert {d["id"] for d in docs} == {"m-1", "m-2"}
    assert sum(d["amount"] for d in docs) == 450


def test_update_modifica_la_riga_esistente():
    repo = build_repo()
    run(repo.insert(make_doc("m-1", "user-1", "2026-08", 450)))
    ok = run(repo.update("m-1", "user-1", {"amount": 600, "period": "2026-08"}))
    assert ok is True
    docs = run(repo.find_many("user-1"))
    assert docs[0]["amount"] == 600


def test_update_created_at_non_cambia():
    repo = build_repo()
    run(repo.insert(make_doc("m-1", "user-1", "2026-08", 450)))
    created_at_originale = run(repo.find_many("user-1"))[0]["created_at"]
    run(repo.update("m-1", "user-1", {"amount": 600}))
    created_at_dopo = run(repo.find_many("user-1"))[0]["created_at"]
    assert created_at_originale == created_at_dopo


def test_update_di_un_id_inesistente_ritorna_false():
    repo = build_repo()
    ok = run(repo.update("non-esiste", "user-1", {"amount": 100}))
    assert ok is False


def test_update_non_tocca_la_riga_di_un_altro_utente():
    repo = build_repo()
    run(repo.insert(make_doc("m-1", "user-2", "2026-08", 450)))
    ok = run(repo.update("m-1", "user-1", {"amount": 999}))
    assert ok is False
    docs = run(repo.find_many("user-2"))
    assert docs[0]["amount"] == 450


def test_mesi_diversi_restano_indipendenti():
    repo = build_repo()
    run(repo.insert(make_doc("m-1", "user-1", "2026-07", 100)))
    run(repo.insert(make_doc("m-2", "user-1", "2026-08", 200)))
    docs = run(repo.find_many("user-1"))
    assert {d["period"]: d["amount"] for d in docs} == {"2026-07": 100, "2026-08": 200}


def test_find_many_non_restituisce_dati_di_un_altro_utente():
    repo = build_repo()
    run(repo.insert(make_doc("m-1", "user-1", "2026-08", 450)))
    run(repo.insert(make_doc("m-2", "user-2", "2026-08", 999)))
    docs = run(repo.find_many("user-1"))
    assert len(docs) == 1
    assert docs[0]["amount"] == 450


def test_delete_rimuove_il_documento():
    repo = build_repo()
    run(repo.insert(make_doc("m-1", "user-1", "2026-08", 450)))
    run(repo.delete("m-1", "user-1"))
    assert run(repo.find_many("user-1")) == []


def test_delete_di_un_id_mai_creato_non_fallisce():
    repo = build_repo()
    run(repo.delete("non-esiste", "user-1"))  # non deve sollevare eccezioni


def test_delete_non_tocca_la_riga_di_un_altro_utente():
    repo = build_repo()
    run(repo.insert(make_doc("m-1", "user-2", "2026-08", 450)))
    run(repo.delete("m-1", "user-1"))
    docs = run(repo.find_many("user-2"))
    assert len(docs) == 1


def test_mandante_id_assente_di_default():
    repo = build_repo()
    run(repo.insert(make_doc("m-1", "user-1", "2026-08", 450)))
    docs = run(repo.find_many("user-1"))
    assert docs[0].get("mandante_id") is None


def test_mandante_id_salvato_se_fornito():
    repo = build_repo()
    run(
        repo.insert(make_doc("m-1", "user-1", "2026-08", 450, mandante_id="mandante-1"))
    )
    docs = run(repo.find_many("user-1"))
    assert docs[0]["mandante_id"] == "mandante-1"


def test_campi_aggiuntivi_salvati_se_forniti():
    repo = build_repo()
    run(
        repo.insert(
            make_doc(
                "m-1",
                "user-1",
                "2026-08",
                450,
                client_id="client-1",
                descrizione="Accordo fuori sistema",
                stato="incassato",
                note="Pagato in contanti",
                tipo="rettifica",
            )
        )
    )
    docs = run(repo.find_many("user-1"))
    assert docs[0]["client_id"] == "client-1"
    assert docs[0]["descrizione"] == "Accordo fuori sistema"
    assert docs[0]["stato"] == "incassato"
    assert docs[0]["note"] == "Pagato in contanti"
    assert docs[0]["tipo"] == "rettifica"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

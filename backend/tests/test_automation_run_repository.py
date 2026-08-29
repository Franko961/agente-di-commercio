"""
Verifica AutomationRunRepository.try_claim(): la prenotazione atomica che
sostituisce il vecchio schema "controlla, poi esegui, poi registra" — con
più repliche del backend in esecuzione, quello schema lasciava una finestra
in cui due istanze potevano superare il controllo entrambe prima che una
delle due registrasse il risultato, eseguendo l'azione (invio email,
creazione appuntamento...) due volte.

Usa un finto collection MongoDB che replica fedelmente le due garanzie su
cui si basa try_claim: un insert_one che solleva DuplicateKeyError se la
chiave (automation_id, target_id) esiste già (come farebbe l'indice
univoco reale), e un update_one il cui matched_count riflette se il filtro
$or ha trovato o meno un documento da aggiornare.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_automation_run_repository.py -v
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone

import pytest
from pymongo.errors import DuplicateKeyError

sys.path.insert(0, ".")

from repositories.automation_run_repository import AutomationRunRepository


def run(coro):
    return asyncio.run(coro)


def _iso(dt):
    return dt.isoformat()


class _UpdateResult:
    def __init__(self, matched_count):
        self.matched_count = matched_count


class _DeleteResult:
    def __init__(self, deleted_count):
        self.deleted_count = deleted_count


class FakeMongoCollection:
    """Replica le due operazioni MongoDB usate da try_claim, comprese le
    garanzie di cui la logica si fida: insert_one solleva DuplicateKeyError
    su chiave duplicata (come farebbe l'indice univoco reale su
    (automation_id, target_id)); update_one applica $set solo al primo
    documento che soddisfa il filtro (incluso un $or), e il matched_count
    del risultato riflette se ha trovato o meno un documento."""

    def __init__(self):
        self.docs = {}  # (automation_id, target_id) -> dict

    async def insert_one(self, doc):
        key = (doc["automation_id"], doc["target_id"])
        if key in self.docs:
            raise DuplicateKeyError("chiave duplicata (automation_id, target_id)")
        self.docs[key] = dict(doc)

    async def update_one(self, query, update):
        key = (query["automation_id"], query["target_id"])
        existing = self.docs.get(key)
        if existing is None:
            return _UpdateResult(matched_count=0)

        or_conditions = query.get("$or", [])
        matches = False
        for cond in or_conditions:
            ok = True
            for field, expected in cond.items():
                if isinstance(expected, dict) and "$lt" in expected:
                    ok = ok and (
                        existing.get(field) is not None
                        and existing[field] < expected["$lt"]
                    )
                else:
                    ok = ok and existing.get(field) == expected
            if ok:
                matches = True
                break

        if not matches:
            return _UpdateResult(matched_count=0)

        existing.update(update["$set"])
        return _UpdateResult(matched_count=1)

    async def delete_many(self, query):
        to_delete = [
            k
            for k, v in self.docs.items()
            if all(v.get(f) == val for f, val in query.items())
        ]
        for k in to_delete:
            del self.docs[k]
        return _DeleteResult(deleted_count=len(to_delete))

    def find(self, query, _projection=None):
        matches = [
            dict(v)
            for v in self.docs.values()
            if all(v.get(f) == val for f, val in query.items())
        ]
        return _FindCursor(matches)


class _FindCursor:
    def __init__(self, docs):
        self.docs = docs

    def sort(self, field, direction=-1):
        self.docs = sorted(
            self.docs, key=lambda d: d.get(field) or "", reverse=(direction == -1)
        )
        return self

    async def to_list(self, limit):
        return self.docs[:limit]


def build_repo():
    repo = AutomationRunRepository()
    repo.collection = FakeMongoCollection()
    return repo


def test_nessun_record_precedente_vince_la_prenotazione():
    repo = build_repo()
    claimed = run(repo.try_claim("auto-1", "user-1", "offer", "target-1"))
    assert claimed is True
    doc = repo.collection.docs[("auto-1", "target-1")]
    assert doc["status"] == "processing"


def test_seconda_prenotazione_sulla_stessa_coppia_fallisce_se_gia_in_corso():
    """Il caso centrale del fix: una seconda istanza che tenta la
    prenotazione mentre la prima è ancora 'processing' (fresca, non
    scaduta) deve perdere — non deve mai eseguire l'azione una seconda
    volta."""
    repo = build_repo()
    prima = run(repo.try_claim("auto-1", "user-1", "offer", "target-1"))
    seconda = run(repo.try_claim("auto-1", "user-1", "offer", "target-1"))
    assert prima is True
    assert seconda is False


def test_record_in_errore_puo_essere_riprenotato():
    repo = build_repo()
    repo.collection.docs[("auto-1", "target-1")] = {
        "automation_id": "auto-1",
        "target_id": "target-1",
        "status": "error",
        "attempts": 1,
        "updated_at": _iso(datetime.now(timezone.utc)),
    }
    claimed = run(repo.try_claim("auto-1", "user-1", "offer", "target-1"))
    assert claimed is True


def test_record_fallito_permanentemente_non_viene_mai_riprenotato():
    repo = build_repo()
    repo.collection.docs[("auto-1", "target-1")] = {
        "automation_id": "auto-1",
        "target_id": "target-1",
        "status": "failed_permanent",
        "attempts": 5,
        "updated_at": _iso(datetime.now(timezone.utc)),
    }
    claimed = run(repo.try_claim("auto-1", "user-1", "offer", "target-1"))
    assert claimed is False


def test_processing_fresco_non_viene_riprenotato():
    """Un'altra istanza sta ancora eseguendo (claimed_at recente): non deve
    essere possibile prenotare di nuovo lo stesso target nel frattempo."""
    repo = build_repo()
    repo.collection.docs[("auto-1", "target-1")] = {
        "automation_id": "auto-1",
        "target_id": "target-1",
        "status": "processing",
        "claimed_at": _iso(datetime.now(timezone.utc) - timedelta(seconds=5)),
    }
    claimed = run(
        repo.try_claim("auto-1", "user-1", "offer", "target-1", stale_after_seconds=300)
    )
    assert claimed is False


def test_processing_scaduto_viene_riprenotato():
    """Un'istanza è crashata a metà esecuzione (claimed_at vecchio, mai
    arrivata a scrivere il risultato finale): il target non deve restare
    bloccato per sempre, va ripreso al ciclo successivo."""
    repo = build_repo()
    repo.collection.docs[("auto-1", "target-1")] = {
        "automation_id": "auto-1",
        "target_id": "target-1",
        "status": "processing",
        "claimed_at": _iso(datetime.now(timezone.utc) - timedelta(seconds=600)),
    }
    claimed = run(
        repo.try_claim("auto-1", "user-1", "offer", "target-1", stale_after_seconds=300)
    )
    assert claimed is True


def test_ok_senza_cooldown_non_viene_mai_riprenotato():
    repo = build_repo()
    repo.collection.docs[("auto-1", "target-1")] = {
        "automation_id": "auto-1",
        "target_id": "target-1",
        "status": "ok",
        "updated_at": _iso(datetime.now(timezone.utc) - timedelta(days=365)),
    }
    claimed = run(
        repo.try_claim("auto-1", "user-1", "offer", "target-1", cooldown_days=None)
    )
    assert claimed is False


def test_ok_con_cooldown_non_ancora_trascorso_non_viene_riprenotato():
    repo = build_repo()
    repo.collection.docs[("auto-1", "target-1")] = {
        "automation_id": "auto-1",
        "target_id": "target-1",
        "status": "ok",
        "updated_at": _iso(datetime.now(timezone.utc) - timedelta(days=2)),
    }
    claimed = run(
        repo.try_claim("auto-1", "user-1", "offer", "target-1", cooldown_days=7)
    )
    assert claimed is False


def test_ok_con_cooldown_trascorso_viene_riprenotato():
    repo = build_repo()
    repo.collection.docs[("auto-1", "target-1")] = {
        "automation_id": "auto-1",
        "target_id": "target-1",
        "status": "ok",
        "updated_at": _iso(datetime.now(timezone.utc) - timedelta(days=8)),
    }
    claimed = run(
        repo.try_claim("auto-1", "user-1", "offer", "target-1", cooldown_days=7)
    )
    assert claimed is True


def test_prenotazioni_su_target_diversi_sono_indipendenti():
    repo = build_repo()
    a = run(repo.try_claim("auto-1", "user-1", "offer", "target-1"))
    b = run(repo.try_claim("auto-1", "user-1", "offer", "target-2"))
    assert a is True
    assert b is True


def test_delete_by_automation_rimuove_solo_le_esecuzioni_dello_stesso_utente():
    """Bug di isolamento multi-tenant: automation_id da solo non basta a
    filtrare la cancellazione. Se un id di automazione (magari indovinato o
    riusato per collisione) corrisponde anche a un'esecuzione di un ALTRO
    utente, quella non deve essere toccata — solo user_id="user-1" deve
    perdere i propri record per "auto-1"."""
    repo = build_repo()
    repo.collection.docs[("auto-1", "target-1")] = {
        "automation_id": "auto-1",
        "target_id": "target-1",
        "user_id": "user-1",
        "status": "ok",
    }
    repo.collection.docs[("auto-1", "target-2")] = {
        "automation_id": "auto-1",
        "target_id": "target-2",
        "user_id": "user-2",
        "status": "ok",
    }

    run(repo.delete_by_automation("auto-1", "user-1"))

    remaining = list(repo.collection.docs.values())
    assert len(remaining) == 1
    assert remaining[0]["user_id"] == "user-2"


def test_delete_by_automation_con_user_id_sbagliato_non_cancella_nulla():
    repo = build_repo()
    repo.collection.docs[("auto-1", "target-1")] = {
        "automation_id": "auto-1",
        "target_id": "target-1",
        "user_id": "user-1",
        "status": "ok",
    }

    run(repo.delete_by_automation("auto-1", "user-di-un-altro-account"))

    assert len(repo.collection.docs) == 1


def test_find_many_by_automation_filtra_anche_per_user_id():
    """Bug di isolamento multi-tenant: automation_id da solo non basta a
    filtrare la lettura dello storico esecuzioni. Se un automation_id
    (magari indovinato o riusato per collisione) corrisponde anche a
    un'esecuzione di un ALTRO utente, quella non deve comparire nel
    risultato — solo le esecuzioni di user_id="user-1" per "auto-1"."""
    repo = build_repo()
    repo.collection.docs[("auto-1", "target-1")] = {
        "automation_id": "auto-1",
        "target_id": "target-1",
        "user_id": "user-1",
        "status": "ok",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    repo.collection.docs[("auto-1", "target-2")] = {
        "automation_id": "auto-1",
        "target_id": "target-2",
        "user_id": "user-2",
        "status": "ok",
        "updated_at": "2026-01-02T00:00:00+00:00",
    }

    result = run(repo.find_many_by_automation("auto-1", "user-1"))

    assert len(result) == 1
    assert result[0]["user_id"] == "user-1"


def test_find_many_by_automation_con_user_id_sbagliato_non_trova_nulla():
    repo = build_repo()
    repo.collection.docs[("auto-1", "target-1")] = {
        "automation_id": "auto-1",
        "target_id": "target-1",
        "user_id": "user-1",
        "status": "ok",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }

    result = run(repo.find_many_by_automation("auto-1", "user-di-un-altro-account"))

    assert result == []


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

"""
Verifica JobLockRepository.try_acquire()/extend(): il lock distribuito che
protegge i cicli periodici di services/startup_service.py (sync Google
Calendar, reset demo, alert anomalie, pulizia richieste demo/contatti,
finalizzazione abbonamenti, recupero azioni AI bloccate) dall'essere
eseguiti contemporaneamente da più repliche Railway.

Usa un finto collection MongoDB che replica le due garanzie su cui si basa
try_acquire: un insert_one che solleva DuplicateKeyError se la chiave (_id)
esiste già (come farebbe l'unicità implicita di _id), e un update_one il
cui matched_count riflette se il filtro (incluso il confronto su
locked_until) ha trovato o meno un documento da aggiornare — stesso
approccio già validato in test_automation_run_repository.py.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_job_lock_repository.py -v
"""
import sys
import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from pymongo.errors import DuplicateKeyError

sys.path.insert(0, ".")

from repositories.job_lock_repository import JobLockRepository


def run(coro):
    return asyncio.run(coro)


def _iso(dt):
    return dt.isoformat()


class _UpdateResult:
    def __init__(self, matched_count):
        self.matched_count = matched_count


class FakeMongoCollection:
    def __init__(self):
        self.docs = {}  # job_name -> dict

    async def insert_one(self, doc):
        key = doc["_id"]
        if key in self.docs:
            raise DuplicateKeyError("chiave duplicata (_id)")
        self.docs[key] = dict(doc)

    async def update_one(self, query, update):
        key = query["_id"]
        existing = self.docs.get(key)
        if existing is None:
            return _UpdateResult(matched_count=0)

        locked_until_filter = query.get("locked_until")
        if locked_until_filter is not None:
            expected_lt = locked_until_filter["$lt"]
            if not (existing.get("locked_until") is not None and existing["locked_until"] < expected_lt):
                return _UpdateResult(matched_count=0)

        existing.update(update["$set"])
        return _UpdateResult(matched_count=1)


def build_repo():
    repo = JobLockRepository()
    repo.collection = FakeMongoCollection()
    return repo


def test_nessun_lock_precedente_vince_lacquisizione():
    repo = build_repo()
    acquired = run(repo.try_acquire("demo_reset", ttl_seconds=60))
    assert acquired is True
    assert "demo_reset" in repo.collection.docs


def test_seconda_replica_sullo_stesso_job_perde_se_lock_fresco():
    """Il caso centrale del fix: due repliche svegliano lo stesso ciclo
    quasi simultaneamente — solo la prima deve vincere il lock ed
    eseguire, la seconda deve saltare il giro."""
    repo = build_repo()
    prima = run(repo.try_acquire("google_calendar_sync", ttl_seconds=270))
    seconda = run(repo.try_acquire("google_calendar_sync", ttl_seconds=270))
    assert prima is True
    assert seconda is False


def test_lock_scaduto_puo_essere_riacquisito():
    """Il lock si libera da solo prima del giro successivo (ttl_seconds <
    intervallo del ciclo): un'altra replica deve poter vincere il round
    successivo senza bisogno di un unlock esplicito."""
    repo = build_repo()
    repo.collection.docs["stuck_ai_action_cleanup"] = {
        "_id": "stuck_ai_action_cleanup",
        "locked_until": _iso(datetime.now(timezone.utc) - timedelta(seconds=5)),
    }
    acquired = run(repo.try_acquire("stuck_ai_action_cleanup", ttl_seconds=45))
    assert acquired is True


def test_lock_ancora_valido_non_viene_rubato():
    repo = build_repo()
    repo.collection.docs["stuck_ai_action_cleanup"] = {
        "_id": "stuck_ai_action_cleanup",
        "locked_until": _iso(datetime.now(timezone.utc) + timedelta(seconds=30)),
    }
    acquired = run(repo.try_acquire("stuck_ai_action_cleanup", ttl_seconds=45))
    assert acquired is False


def test_lock_su_job_diversi_sono_indipendenti():
    repo = build_repo()
    a = run(repo.try_acquire("demo_reset", ttl_seconds=60))
    b = run(repo.try_acquire("cancel_finalize", ttl_seconds=60))
    assert a is True
    assert b is True


def test_extend_allunga_la_scadenza_di_un_lock_gia_posseduto():
    """Usato dal ciclo di alert anomalie per trasformare il lock in un
    cooldown condiviso fra repliche dopo un invio riuscito: il lock deve
    restare 'occupato' ben oltre il suo ttl originale."""
    repo = build_repo()
    run(repo.try_acquire("health_alert", ttl_seconds=60))

    run(repo.extend("health_alert", ttl_seconds=3600))

    locked_until = datetime.fromisoformat(repo.collection.docs["health_alert"]["locked_until"])
    assert locked_until > datetime.now(timezone.utc) + timedelta(seconds=3000)

    ancora_bloccato = run(repo.try_acquire("health_alert", ttl_seconds=60))
    assert ancora_bloccato is False


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

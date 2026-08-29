"""
Verifica JobLockRepository.try_acquire()/extend(): il lock distribuito che
protegge i cicli periodici di services/startup/ (sync Google
Calendar, reset demo, alert anomalie, pulizia richieste demo/contatti,
finalizzazione abbonamenti, recupero azioni AI bloccate) dall'essere
eseguiti contemporaneamente da più repliche Railway.

Copre anche il limite tecnico segnalato su extend(): senza un controllo di
proprietà, un'istanza la cui esecuzione dura più del ttl_seconds con cui
aveva acquisito il lock potrebbe estenderlo anche dopo che è scaduto ed è
stato legittimamente riconquistato da un'altra istanza, "rubandolo"
indietro. try_acquire ritorna un owner_id univoco per ogni prenotazione
vinta; extend richiede lo stesso owner_id e non ha effetto se non
corrisponde più (vedi test_extend_fallisce_se_il_lock_e_stato_riassegnato).

Usa un finto collection MongoDB che replica le garanzie su cui si basa il
repository: un insert_one che solleva DuplicateKeyError se la chiave (_id)
esiste già (come farebbe l'unicità implicita di _id), e un update_one il
cui matched_count riflette se OGNI campo del filtro (inclusi il confronto
su locked_until e l'uguaglianza su owner_id) ha trovato un documento
corrispondente — stesso approccio già validato in
test_automation_run_repository.py.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_job_lock_repository.py -v
"""

import asyncio
import sys
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

        for field, expected in query.items():
            if field == "_id":
                continue
            if isinstance(expected, dict) and "$lt" in expected:
                if not (
                    existing.get(field) is not None
                    and existing[field] < expected["$lt"]
                ):
                    return _UpdateResult(matched_count=0)
            elif existing.get(field) != expected:
                return _UpdateResult(matched_count=0)

        existing.update(update["$set"])
        return _UpdateResult(matched_count=1)


def build_repo():
    repo = JobLockRepository()
    repo.collection = FakeMongoCollection()
    return repo


def test_nessun_lock_precedente_vince_lacquisizione():
    repo = build_repo()
    owner = run(repo.try_acquire("demo_reset", ttl_seconds=60))
    assert owner is not None
    assert repo.collection.docs["demo_reset"]["owner_id"] == owner


def test_seconda_replica_sullo_stesso_job_perde_se_lock_fresco():
    """Il caso centrale del lock: due repliche svegliano lo stesso ciclo
    quasi simultaneamente — solo la prima deve vincere il lock ed
    eseguire, la seconda deve saltare il giro."""
    repo = build_repo()
    prima = run(repo.try_acquire("google_calendar_sync", ttl_seconds=270))
    seconda = run(repo.try_acquire("google_calendar_sync", ttl_seconds=270))
    assert prima is not None
    assert seconda is None


def test_owner_id_diverso_ad_ogni_prenotazione_vinta():
    """Anche la stessa istanza che riconquista lo stesso job_name in un
    giro successivo deve ottenere un owner_id diverso: è la prenotazione
    ad avere un'identità, non il processo — vedi il commento su extend()
    per il perché."""
    repo = build_repo()
    prima = run(repo.try_acquire("demo_reset", ttl_seconds=1))
    repo.collection.docs["demo_reset"]["locked_until"] = _iso(
        datetime.now(timezone.utc) - timedelta(seconds=1)
    )
    seconda = run(repo.try_acquire("demo_reset", ttl_seconds=60))
    assert seconda is not None
    assert seconda != prima


def test_lock_scaduto_puo_essere_riacquisito():
    """Il lock si libera da solo prima del giro successivo (ttl_seconds <
    intervallo del ciclo): un'altra replica deve poter vincere il round
    successivo senza bisogno di un unlock esplicito."""
    repo = build_repo()
    repo.collection.docs["stuck_ai_action_cleanup"] = {
        "_id": "stuck_ai_action_cleanup",
        "owner_id": "vecchio-owner",
        "locked_until": _iso(datetime.now(timezone.utc) - timedelta(seconds=5)),
    }
    owner = run(repo.try_acquire("stuck_ai_action_cleanup", ttl_seconds=45))
    assert owner is not None
    assert owner != "vecchio-owner"


def test_lock_ancora_valido_non_viene_rubato():
    repo = build_repo()
    repo.collection.docs["stuck_ai_action_cleanup"] = {
        "_id": "stuck_ai_action_cleanup",
        "owner_id": "altro-owner",
        "locked_until": _iso(datetime.now(timezone.utc) + timedelta(seconds=30)),
    }
    owner = run(repo.try_acquire("stuck_ai_action_cleanup", ttl_seconds=45))
    assert owner is None


def test_lock_su_job_diversi_sono_indipendenti():
    repo = build_repo()
    a = run(repo.try_acquire("demo_reset", ttl_seconds=60))
    b = run(repo.try_acquire("cancel_finalize", ttl_seconds=60))
    assert a is not None
    assert b is not None


def test_extend_allunga_la_scadenza_di_un_lock_gia_posseduto():
    """Usato dal ciclo di alert anomalie per trasformare il lock in un
    cooldown condiviso fra repliche dopo un invio riuscito: il lock deve
    restare 'occupato' ben oltre il suo ttl originale."""
    repo = build_repo()
    owner = run(repo.try_acquire("health_alert", ttl_seconds=60))

    extended = run(repo.extend("health_alert", owner, ttl_seconds=3600))
    assert extended is True

    locked_until = datetime.fromisoformat(
        repo.collection.docs["health_alert"]["locked_until"]
    )
    assert locked_until > datetime.now(timezone.utc) + timedelta(seconds=3000)

    ancora_bloccato = run(repo.try_acquire("health_alert", ttl_seconds=60))
    assert ancora_bloccato is None


def test_extend_fallisce_se_il_lock_e_stato_riassegnato_ad_altra_istanza():
    """Il limite tecnico segnalato: un'istanza A vince il lock, ma la sua
    esecuzione dura più del proprio ttl_seconds — nel frattempo il lock
    scade ed è legittimamente riconquistato da un'istanza B. La extend()
    tardiva di A (che userebbe ancora il PROPRIO owner_id, ormai superato)
    non deve avere alcun effetto: il filtro su owner_id la fa fallire,
    lasciando intatta la prenotazione di B."""
    repo = build_repo()
    owner_a = run(repo.try_acquire("health_alert", ttl_seconds=60))

    # Il lock di A scade, e B lo riconquista legittimamente.
    repo.collection.docs["health_alert"]["locked_until"] = _iso(
        datetime.now(timezone.utc) - timedelta(seconds=1)
    )
    owner_b = run(repo.try_acquire("health_alert", ttl_seconds=900))
    assert owner_b is not None
    assert owner_b != owner_a

    locked_until_prima = repo.collection.docs["health_alert"]["locked_until"]

    # A, ignaro di aver perso il lock, prova comunque a estenderlo con il
    # PROPRIO (ormai superato) owner_id.
    extended = run(repo.extend("health_alert", owner_a, ttl_seconds=3600))

    assert extended is False
    assert repo.collection.docs["health_alert"]["owner_id"] == owner_b
    assert repo.collection.docs["health_alert"]["locked_until"] == locked_until_prima


def test_extend_con_owner_id_inesistente_non_ha_effetto():
    repo = build_repo()
    run(repo.try_acquire("health_alert", ttl_seconds=60))
    extended = run(repo.extend("health_alert", "owner-mai-esistito", ttl_seconds=3600))
    assert extended is False


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

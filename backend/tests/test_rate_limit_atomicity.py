"""
Verifica il fix della corsa (TOCTOU) in check_and_record (core/rate_limit.py):
prima "conta poi eventualmente inserisci" erano due operazioni Mongo
separate — due chiamate concorrenti sulla stessa (kind, key) potevano
entrambe leggere lo stesso conteggio sotto soglia PRIMA che una delle due
registrasse il proprio tentativo, superando così max_attempts in una
singola raffica (es. tentativi di login in parallelo, o il pulsante
"richiedi export" premuto più volte in rapida successione).

Il fake qui sotto non reinterpreta la sintassi della pipeline di
aggiornamento (verificata direttamente contro MongoDB Atlas reale durante
lo sviluppo — sequenza corretta, e 10/20 chiamate concorrenti reali con
asyncio.gather su una chiave mai vista prima concedono esattamente
max_attempts volte, un solo documento creato, nessun duplicato). Simula
invece il comportamento osservabile equivalente che MongoDB garantisce
(filtro-poi-eventuale-append come operazione atomica), per testare la
logica lato Python di check_and_record — incluso il retry su
DuplicateKeyError — senza dipendere da una connessione reale ad ogni
esecuzione della suite.

Esegui con:
    JWT_SECRET=test python -m pytest tests/test_rate_limit_atomicity.py -v
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone

import pytest
from pymongo.errors import DuplicateKeyError

sys.path.insert(0, ".")

from core.rate_limit import check_and_record


def run(coro):
    return asyncio.run(coro)


class FakeAtomicRateLimitCollection:
    """Simula find_one_and_update(upsert=True, return_document=AFTER) con lo
    stesso comportamento osservabile della pipeline reale: un solo documento
    per (kind, key), attempts filtrati per la finestra e appesi SOLO se
    ancora sotto max_attempts — eseguito come un singolo passo sincrono per
    chiamata, così due `await` concorrenti sullo stesso event loop non
    possono mai interlacciarsi a metà (lo stesso principio di atomicità che
    MongoDB garantisce lato server)."""

    def __init__(self):
        self.docs = {}  # (kind, key) -> {"attempts": [...], "last_updated": ...}
        self.fail_next_upsert_for = None  # (kind, key) su cui simulare una corsa

    async def find_one_and_update(
        self, filter_, pipeline, upsert=False, return_document=None
    ):
        key = (filter_["kind"], filter_["key"])
        is_new = key not in self.docs

        if is_new and self.fail_next_upsert_for == key:
            self.fail_next_upsert_for = None  # solo la prima volta, come una vera corsa
            raise DuplicateKeyError("chiave duplicata (kind, key)")

        doc = self.docs.setdefault(key, {"attempts": []})

        # Replica il comportamento delle due tappe della pipeline reale:
        # ricava since_iso/now_iso/max_attempts dagli stage stessi (li
        # abbiamo costruiti noi in check_and_record, quindi la forma è nota).
        since_iso = pipeline[0]["$set"]["attempts"]["$filter"]["cond"]["$gte"][1]
        cond_stage = pipeline[1]["$set"]["attempts"]["$cond"]
        max_attempts = cond_stage[0]["$lt"][1]
        now_iso = cond_stage[1]["$concatArrays"][1][0]

        filtered = [a for a in doc["attempts"] if a >= since_iso]
        if len(filtered) < max_attempts:
            filtered = filtered + [now_iso]
        doc["attempts"] = filtered
        doc["last_updated"] = datetime.now(timezone.utc)
        return dict(doc)


def _iso(dt):
    return dt.isoformat()


def test_concede_fino_a_max_attempts_poi_rifiuta():
    coll = FakeAtomicRateLimitCollection()
    import core.rate_limit as m

    m_orig = m.COLLECTION
    m.COLLECTION = coll
    try:
        results = [
            run(check_and_record("test_kind", "k1", max_attempts=3, window_minutes=15))
            for _ in range(5)
        ]
    finally:
        m.COLLECTION = m_orig

    assert results == [True, True, True, False, False]


def test_i_tentativi_rifiutati_non_allungano_la_finestra():
    """Un tentativo negato non deve essere registrato: altrimenti un
    attaccante che continua a martellare terrebbe la finestra sempre viva
    all'infinito, invece di lasciarla scadere."""
    coll = FakeAtomicRateLimitCollection()
    import core.rate_limit as m

    m_orig = m.COLLECTION
    m.COLLECTION = coll
    try:
        for _ in range(5):
            run(check_and_record("test_kind", "k2", max_attempts=2, window_minutes=15))
        doc = coll.docs[("test_kind", "k2")]
    finally:
        m.COLLECTION = m_orig

    assert len(doc["attempts"]) == 2


def test_tentativi_fuori_dalla_finestra_vengono_filtrati_via():
    coll = FakeAtomicRateLimitCollection()
    old = _iso(datetime.now(timezone.utc) - timedelta(minutes=30))
    coll.docs[("test_kind", "k3")] = {"attempts": [old, old, old]}

    import core.rate_limit as m

    m_orig = m.COLLECTION
    m.COLLECTION = coll
    try:
        result = run(
            check_and_record("test_kind", "k3", max_attempts=3, window_minutes=15)
        )
    finally:
        m.COLLECTION = m_orig

    # I 3 tentativi vecchi sono fuori dalla finestra di 15 minuti: il nuovo
    # tentativo deve essere concesso come se la chiave fosse pulita.
    assert result is True
    assert len(coll.docs[("test_kind", "k3")]["attempts"]) == 1


def test_chiavi_diverse_sono_indipendenti():
    coll = FakeAtomicRateLimitCollection()
    import core.rate_limit as m

    m_orig = m.COLLECTION
    m.COLLECTION = coll
    try:
        for _ in range(2):
            run(check_and_record("test_kind", "k4", max_attempts=2, window_minutes=15))
        result_altra_chiave = run(
            check_and_record("test_kind", "k5", max_attempts=2, window_minutes=15)
        )
    finally:
        m.COLLECTION = m_orig

    assert result_altra_chiave is True


def test_corsa_su_chiave_nuova_viene_ritentata_dopo_duplicatekeyerror():
    """Il caso che l'indice univoco (kind, key) protegge: due chiamate
    concorrenti su una chiave MAI vista prima possono entrambe tentare di
    crearla, la seconda perde con DuplicateKeyError — check_and_record deve
    ritentare invece di propagare l'errore all'utente come un fallimento."""
    coll = FakeAtomicRateLimitCollection()
    coll.fail_next_upsert_for = ("test_kind", "k6")

    import core.rate_limit as m

    m_orig = m.COLLECTION
    m.COLLECTION = coll
    try:
        result = run(
            check_and_record("test_kind", "k6", max_attempts=3, window_minutes=15)
        )
    finally:
        m.COLLECTION = m_orig

    assert result is True
    assert len(coll.docs[("test_kind", "k6")]["attempts"]) == 1


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

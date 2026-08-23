"""
Verifica il fix della corsa nell'idempotenza dei webhook Stripe/PayPal
(_claim_webhook_event_once in subscription_service.py): prima "cerca poi
eventualmente inserisci" erano due operazioni Mongo separate — due
consegne quasi simultanee dello stesso evento (entrambi i provider
dichiarano esplicitamente di poterlo fare) potevano passare il controllo
find_one prima che una delle due scrivesse, elaborando lo stesso evento
due volte. Ora un solo insert_one, che fallisce da solo con
DuplicateKeyError sul secondo tentativo grazie all'indice univoco su
event_id — un'unica operazione atomica, nessuna finestra residua.

Esegui con:
    JWT_SECRET=test python -m pytest tests/test_webhook_idempotency_race.py -v
"""
import sys
import asyncio
import threading

import pytest
from pymongo.errors import DuplicateKeyError

sys.path.insert(0, ".")

from services.subscription_service import _claim_webhook_event_once


def run(coro):
    return asyncio.run(coro)


class FakeUniqueIndexCollection:
    """Replica la garanzia che conta: un indice univoco reale su event_id
    fa fallire con DuplicateKeyError qualunque insert_one successivo al
    primo per lo stesso event_id — protetto da un lock, come farebbe
    MongoDB lato server per due scritture sullo stesso documento."""

    def __init__(self):
        self._seen = set()
        self._lock = threading.Lock()

    async def insert_one(self, doc):
        with self._lock:
            if doc["event_id"] in self._seen:
                raise DuplicateKeyError("chiave duplicata (event_id)")
            self._seen.add(doc["event_id"])


def test_prima_chiamata_reclama_levento():
    coll = FakeUniqueIndexCollection()
    result = run(_claim_webhook_event_once(coll, "evt-1", "checkout.session.completed"))
    assert result is True


def test_seconda_chiamata_sullo_stesso_evento_viene_rifiutata():
    coll = FakeUniqueIndexCollection()
    run(_claim_webhook_event_once(coll, "evt-2", "checkout.session.completed"))

    result = run(_claim_webhook_event_once(coll, "evt-2", "checkout.session.completed"))

    assert result is False


def test_eventi_diversi_sono_indipendenti():
    coll = FakeUniqueIndexCollection()
    r1 = run(_claim_webhook_event_once(coll, "evt-3", "a"))
    r2 = run(_claim_webhook_event_once(coll, "evt-4", "b"))

    assert r1 is True
    assert r2 is True


def test_consegne_concorrenti_dello_stesso_evento_solo_una_lo_reclama():
    """Il caso centrale del fix: N chiamate 'simultanee' sullo stesso
    event_id (due consegne quasi contemporanee dello stesso webhook) devono
    risultare in ESATTAMENTE una sola reclamata come prima."""
    coll = FakeUniqueIndexCollection()

    async def main():
        return await asyncio.gather(*[
            _claim_webhook_event_once(coll, "evt-race", "checkout.session.completed")
            for _ in range(20)
        ])

    results = run(main())

    assert sum(1 for r in results if r) == 1
    assert sum(1 for r in results if not r) == 19


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

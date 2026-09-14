"""
Verifica ClientService.create_client: il campo "_first_action" (letto dal
frontend per l'evento GA4 "first_real_action", vedi activation_service)
deve comparire solo quando mark_first_action_if_needed segnala che questo
è davvero il primo cliente/lead/ordine mai creato dall'utente.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_client_service_create_first_action.py -v
"""

import asyncio
import sys

sys.path.insert(0, ".")

from models.client import ClientIn
from services.client_service import ClientService


def run(coro):
    return asyncio.run(coro)


class FakeClientRepo:
    def __init__(self):
        self.docs = {}

    async def insert(self, doc):
        self.docs[doc["id"]] = doc
        return doc


def _payload(**overrides):
    base = dict(company_name="Bar Rossi")
    base.update(overrides)
    return ClientIn(**base)


def test_create_client_espone_first_action_solo_quando_e_il_primo():
    calls = []

    async def stub_mark_first_action(user_id):
        calls.append(user_id)
        return len(calls) == 1

    service = ClientService(repo=FakeClientRepo(), mark_first_action=stub_mark_first_action)

    first = run(service.create_client({"id": "user-1"}, _payload()))
    second = run(service.create_client({"id": "user-1"}, _payload(company_name="Bar Bianchi")))

    assert first["_first_action"] is True
    assert "_first_action" not in second


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))

"""
Verifica services.ai_service.tools.crm_writer._add_client: il documento
scritto non deve contenere campi assenti dal modello Client
(models/client.py: ClientIn) — stesso bug shape di _add_lead
(test_ai_add_lead_status.py), trovato da una code review per analogia il
2026-09-12: "segment"/"status" erano scritti hardcoded senza corrispondere
a nessun campo di ClientIn. client_repository.insert() fa un insert_one()
grezzo, senza validazione Pydantic, quindi l'errore non falliva: il
cliente veniva creato con due campi morti, ignorati dal resto del sistema
(a differenza del bug lead, qui senza sintomi visibili oggi perché nulla
li legge — ma stesso rischio di drift silenzioso).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_ai_add_client_fields.py -v
"""

import asyncio
import sys

sys.path.insert(0, ".")

from models.client import ClientIn
from services.ai_service.tools.crm_writer import _add_client


def run(coro):
    return asyncio.run(coro)


class FakeClientRepo:
    def __init__(self):
        self.inserted = None

    async def insert(self, doc):
        self.inserted = doc
        return doc


def test_add_client_non_scrive_campi_fantasma_segment_status():
    repo = FakeClientRepo()

    run(_add_client(repo, {"company_name": "Bar Rossi"}, "user-1"))

    assert "segment" not in repo.inserted
    assert "status" not in repo.inserted


def test_add_client_scrive_solo_campi_del_modello_reale():
    repo = FakeClientRepo()

    run(
        _add_client(
            repo,
            {"company_name": "Bar Rossi", "contact_name": "Mario Rossi"},
            "user-1",
        )
    )

    model_fields = set(ClientIn.model_fields.keys())
    doc_fields = set(repo.inserted.keys())
    # id/user_id/created_at/mandante_ids sono aggiunti dal tool stesso
    # (non fanno parte di ClientIn, che descrive solo l'input utente) —
    # esclusi dal confronto, il resto deve essere un sottoinsieme valido.
    extra = doc_fields - model_fields - {"id", "user_id", "created_at"}
    assert extra == set()


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))

"""
Verifica services.ai_service.tools.crm_writer._add_lead: il documento
scritto deve avere uno status valido (uno dei LEAD_STATUSES) ed esporre
"estimated_value", non "value" — un bug reale trovato il 2026-09-12
(segnalazione di Franco: "ho chiesto all'AI di aggiungere un lead, non
riesco a visualizzarlo nella sezione lead e pipeline").

Prima della fix il tool scriveva "status": "aperto" (non in LEAD_STATUSES)
e "stage": "nuovo" (campo mai esistito nel modello Lead) — lead_repository
.insert() fa un insert_one() grezzo, senza validazione Pydantic, quindi
l'errore non falliva mai: il lead veniva creato per davvero, ma restava
invisibile in ogni colonna della pipeline Kanban (frontend/src/pages/
Leads.jsx filtra strettamente `l.status === col.id`).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_ai_add_lead_status.py -v
"""

import asyncio
import sys

sys.path.insert(0, ".")

from models.lead import LEAD_STATUSES
from services.ai_service.tools.crm_writer import _add_lead


def run(coro):
    return asyncio.run(coro)


class FakeLeadRepo:
    def __init__(self):
        self.inserted = None

    async def insert(self, doc):
        self.inserted = doc
        return doc


def test_add_lead_scrive_uno_status_valido():
    repo = FakeLeadRepo()

    run(
        _add_lead(
            repo,
            {"company_name": "Bar Rossi", "contact_name": "Mario Rossi", "value": 1500},
            "user-1",
        )
    )

    assert repo.inserted is not None
    assert repo.inserted["status"] in LEAD_STATUSES
    assert repo.inserted["status"] == "nuovo"
    # Il bug esatto trovato: "aperto" non è (e non deve tornare a essere)
    # un valore valido di LEAD_STATUSES.
    assert "aperto" not in LEAD_STATUSES


def test_add_lead_usa_estimated_value_non_value():
    repo = FakeLeadRepo()

    run(_add_lead(repo, {"company_name": "Bar Rossi", "value": 1500}, "user-1"))

    assert repo.inserted["estimated_value"] == 1500
    assert "value" not in repo.inserted


def test_add_lead_non_scrive_piu_il_campo_stage_fantasma():
    """ "stage" non è mai stato un campo del modello Lead (models/lead.py):
    scritto dal tool ma ignorato dal resto del sistema — solo rumore nel
    documento salvato."""
    repo = FakeLeadRepo()

    run(_add_lead(repo, {"company_name": "Bar Rossi"}, "user-1"))

    assert "stage" not in repo.inserted


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))

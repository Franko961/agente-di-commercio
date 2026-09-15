"""
Verifica services.ai_service.tools.crm_writer._add_leads (tool bulk
"add_leads"), aggiunto dopo un bug reale (2026-09-15): Franco ha chiesto
all'assistente di inserire 12 lead incollati in chat, l'AI ha risposto
"fatto" ma nessuno era stato creato davvero — il tool add_lead accetta un
solo lead per chiamata, e farne 12 nello stesso turno dipende dal modello
che riesce a emettere 12 tool_use nello stesso budget di token (rischioso).
add_leads risolve inserendo tutto in un'unica chiamata, riusando
lead_repository.insert_many (già esistente, già usato altrove).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_ai_bulk_leads.py -v
"""

import asyncio
import sys

sys.path.insert(0, ".")

from services.ai_service.catalog import MAX_BULK_LEADS
from services.ai_service.tools.crm_writer import _add_leads


def run(coro):
    return asyncio.run(coro)


class FakeLeadRepo:
    def __init__(self):
        self.inserted_many = None

    async def insert_many(self, docs):
        self.inserted_many = docs


def test_add_leads_inserisce_tutti_i_lead_con_status_e_campi_corretti():
    repo = FakeLeadRepo()

    result = run(
        _add_leads(
            repo,
            {
                "leads": [
                    {"company_name": "Bar Rossi", "value": 1500},
                    {
                        "company_name": "Trattoria Verdi",
                        "contact_name": "Mario Verdi",
                        "email": "mario@verdi.it",
                    },
                ]
            },
            "user-1",
        )
    )

    assert repo.inserted_many is not None
    assert len(repo.inserted_many) == 2
    for doc in repo.inserted_many:
        assert doc["user_id"] == "user-1"
        assert doc["status"] == "nuovo"
        assert "id" in doc and "created_at" in doc
    assert repo.inserted_many[0]["company_name"] == "Bar Rossi"
    assert repo.inserted_many[0]["estimated_value"] == 1500
    assert "value" not in repo.inserted_many[0]
    assert repo.inserted_many[1]["contact_name"] == "Mario Verdi"
    assert "2 lead aggiunti" in result
    assert "Bar Rossi" in result and "Trattoria Verdi" in result


def test_add_leads_scarta_voci_senza_company_name():
    repo = FakeLeadRepo()

    result = run(
        _add_leads(
            repo,
            {"leads": [{"company_name": "Bar Rossi"}, {"contact_name": "Senza nome"}]},
            "user-1",
        )
    )

    assert len(repo.inserted_many) == 1
    assert repo.inserted_many[0]["company_name"] == "Bar Rossi"
    assert "1 lead aggiunti" in result


def test_add_leads_lista_vuota_non_inserisce_nulla():
    repo = FakeLeadRepo()

    result = run(_add_leads(repo, {"leads": []}, "user-1"))

    assert repo.inserted_many is None
    assert result.startswith("❌")


def test_add_leads_tutte_le_voci_senza_nome_non_inserisce_nulla():
    repo = FakeLeadRepo()

    result = run(
        _add_leads(repo, {"leads": [{"contact_name": "Senza nome"}]}, "user-1")
    )

    assert repo.inserted_many is None
    assert result.startswith("❌")


def test_add_leads_rifiuta_batch_oltre_il_massimo():
    repo = FakeLeadRepo()
    many = [{"company_name": f"Azienda {i}"} for i in range(MAX_BULK_LEADS + 1)]

    result = run(_add_leads(repo, {"leads": many}, "user-1"))

    assert repo.inserted_many is None
    assert result.startswith("❌")
    assert str(MAX_BULK_LEADS) in result


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))

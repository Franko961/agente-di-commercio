"""
Verifica lead_service: in particolare, che last_interaction_at venga
aggiornato ad ogni modifica/cambio di stato/registrazione di contatto —
il dato che risolve il bug per cui il trigger "lead inattivo" delle
automazioni usava solo created_at, segnalando come inattivo un lead
creato molto tempo fa ma contattato di recente.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_lead_service.py -v
"""

import asyncio
import sys

import pytest

sys.path.insert(0, ".")

from core.exceptions import NotFoundError
from models.lead import LeadIn
from services.lead_service import LeadService


def run(coro):
    return asyncio.run(coro)


class FakeLeadRepo:
    def __init__(self):
        self.docs = {}

    async def find_many(self, user_id):
        return [d for d in self.docs.values() if d["user_id"] == user_id]

    async def find_one(self, lid, user_id):
        d = self.docs.get(lid)
        return dict(d) if d and d["user_id"] == user_id else None

    async def insert(self, doc):
        self.docs[doc["id"]] = doc
        return doc

    async def update(self, lid, user_id, data):
        if lid in self.docs and self.docs[lid]["user_id"] == user_id:
            self.docs[lid].update(data)

    async def update_status(self, lid, user_id, status, now_iso_str):
        if lid in self.docs and self.docs[lid]["user_id"] == user_id:
            self.docs[lid].update(
                {
                    "status": status,
                    "updated_at": now_iso_str,
                    "last_interaction_at": now_iso_str,
                }
            )

    async def log_contact(self, lid, user_id, now_iso_str, notes=None):
        if lid not in self.docs or self.docs[lid]["user_id"] != user_id:
            return False
        data = {
            "last_contact_at": now_iso_str,
            "last_interaction_at": now_iso_str,
            "updated_at": now_iso_str,
        }
        if notes is not None:
            data["notes"] = notes
        self.docs[lid].update(data)
        return True

    async def delete(self, lid, user_id):
        self.docs.pop(lid, None)


def _payload(**overrides):
    base = dict(
        company_name="Bianchi Spa",
        contact_name="",
        email="",
        phone="",
        source="",
        estimated_value=0.0,
        status="nuovo",
        notes="",
    )
    base.update(overrides)
    return LeadIn(**base)


def build_service():
    return LeadService(repo=FakeLeadRepo())


def test_creazione_imposta_last_interaction_at():
    service = build_service()
    lead = run(service.create_lead({"id": "user-1"}, _payload()))
    assert lead["last_interaction_at"] is not None
    assert lead["last_interaction_at"] == lead["created_at"]


def test_modifica_aggiorna_last_interaction_at():
    service = build_service()
    lead = run(service.create_lead({"id": "user-1"}, _payload()))
    original_interaction = lead["last_interaction_at"]

    run(
        service.update_lead(
            {"id": "user-1"},
            lead["id"],
            _payload(notes="richiamare la prossima settimana"),
        )
    )

    updated = service.repo.docs[lead["id"]]
    assert updated["notes"] == "richiamare la prossima settimana"
    assert updated["last_interaction_at"] >= original_interaction


def test_cambio_stato_aggiorna_last_interaction_at():
    service = build_service()
    lead = run(service.create_lead({"id": "user-1"}, _payload()))

    run(service.update_status({"id": "user-1"}, lead["id"], "contattato"))

    updated = service.repo.docs[lead["id"]]
    assert updated["status"] == "contattato"
    assert updated["last_interaction_at"] is not None


def test_log_contact_aggiorna_last_contact_e_last_interaction():
    service = build_service()
    lead = run(service.create_lead({"id": "user-1"}, _payload()))

    run(
        service.log_contact(
            {"id": "user-1"}, lead["id"], "chiamato, richiamare tra 3 giorni"
        )
    )

    updated = service.repo.docs[lead["id"]]
    assert updated["last_contact_at"] is not None
    assert updated["last_interaction_at"] == updated["last_contact_at"]
    assert "chiamato, richiamare tra 3 giorni" in updated["notes"]


def test_log_contact_senza_nota_non_tocca_le_note_esistenti():
    service = build_service()
    lead = run(service.create_lead({"id": "user-1"}, _payload(notes="nota originale")))

    run(service.log_contact({"id": "user-1"}, lead["id"], ""))

    updated = service.repo.docs[lead["id"]]
    assert updated["notes"] == "nota originale"
    assert updated["last_contact_at"] is not None


def test_log_contact_su_lead_inesistente_solleva_not_found():
    service = build_service()
    with pytest.raises(NotFoundError):
        run(service.log_contact({"id": "user-1"}, "id-inesistente", "nota"))


def test_log_contact_non_tocca_lead_di_un_altro_utente():
    service = build_service()
    lead = run(service.create_lead({"id": "user-1"}, _payload()))
    with pytest.raises(NotFoundError):
        run(service.log_contact({"id": "user-2"}, lead["id"], "nota"))


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

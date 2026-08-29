from typing import Optional

from core.exceptions import NotFoundError
from core.utils import gen_id, now_iso
from repositories.lead_repository import lead_repository


class LeadService:
    def __init__(self, repo=lead_repository):
        self.repo = repo

    async def list_leads(self, user: dict) -> list:
        return await self.repo.find_many(user["id"])

    async def create_lead(self, user: dict, payload) -> dict:
        now = now_iso()
        doc = {
            "id": gen_id(),
            "user_id": user["id"],
            **payload.model_dump(),
            "created_at": now,
            "updated_at": now,
            "last_interaction_at": now,
        }
        return await self.repo.insert(doc)

    async def update_lead(self, user: dict, lid: str, payload) -> None:
        # Modificare un lead (note, dati di contatto, ecc.) è di per sé
        # un'interazione: aggiorna last_interaction_at, il dato su cui si
        # basa il trigger "lead inattivo" delle automazioni. Prima veniva
        # usato solo created_at, che restava fermo alla data di creazione
        # anche per un lead contattato ieri.
        now = now_iso()
        data = payload.model_dump()
        data["updated_at"] = now
        data["last_interaction_at"] = now
        await self.repo.update(lid, user["id"], data)

    async def update_status(self, user: dict, lid: str, status: str) -> None:
        await self.repo.update_status(lid, user["id"], status, now_iso())

    async def log_contact(self, user: dict, lid: str, note: Optional[str] = "") -> None:
        """Registra esplicitamente un contatto avvenuto (chiamata, email,
        incontro) con il lead — l'azione da usare quando si vuole segnalare
        un'interazione reale senza necessariamente cambiare altri dati."""
        now = now_iso()
        new_notes = None
        if note:
            existing = await self.repo.find_one(lid, user["id"])
            if not existing:
                raise NotFoundError("Lead non trovato")
            prefix = f"[{now[:10]}] {note}"
            new_notes = f"{existing.get('notes', '')}\n{prefix}".strip()
        ok = await self.repo.log_contact(lid, user["id"], now, new_notes)
        if not ok:
            raise NotFoundError("Lead non trovato")

    async def delete_lead(self, user: dict, lid: str) -> None:
        await self.repo.delete(lid, user["id"])


lead_service = LeadService()

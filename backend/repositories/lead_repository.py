from typing import Optional

from core.database import db


class LeadRepository:
    collection = db.leads

    async def find_many(self, user_id: str) -> list:
        return await self.collection.find({"user_id": user_id}, {"_id": 0}).to_list(
            2000
        )

    async def find_one(self, lid: str, user_id: str) -> Optional[dict]:
        return await self.collection.find_one(
            {"id": lid, "user_id": user_id}, {"_id": 0}
        )

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def insert_many(self, docs: list) -> None:
        if docs:
            await self.collection.insert_many(docs)

    async def update(self, lid: str, user_id: str, data: dict) -> None:
        await self.collection.update_one(
            {"id": lid, "user_id": user_id}, {"$set": data}
        )

    async def update_status(
        self, lid: str, user_id: str, status: str, now_iso_str: str
    ) -> None:
        # Cambiare stato (spostare il lead nella pipeline) è di per sé
        # un'interazione: aggiorna anche last_interaction_at, non solo lo
        # stato — altrimenti un lead mosso ogni giorno nel kanban ma senza
        # mai un salvataggio via form risulterebbe comunque "inattivo".
        await self.collection.update_one(
            {"id": lid, "user_id": user_id},
            {
                "$set": {
                    "status": status,
                    "updated_at": now_iso_str,
                    "last_interaction_at": now_iso_str,
                }
            },
        )

    async def log_contact(
        self, lid: str, user_id: str, now_iso_str: str, notes: Optional[str] = None
    ) -> bool:
        """Registra un contatto avvenuto davvero (chiamata/email/incontro):
        aggiorna last_contact_at E last_interaction_at (un contatto è
        sempre anche un'interazione, il contrario non è detto — es.
        correggere un numero di telefono è un'interazione ma non un
        contatto). Ritorna False se il lead non esiste/non è dell'utente."""
        data = {
            "last_contact_at": now_iso_str,
            "last_interaction_at": now_iso_str,
            "updated_at": now_iso_str,
        }
        if notes is not None:
            data["notes"] = notes
        result = await self.collection.update_one(
            {"id": lid, "user_id": user_id}, {"$set": data}
        )
        return result.matched_count > 0

    async def delete(self, lid: str, user_id: str) -> None:
        await self.collection.delete_one({"id": lid, "user_id": user_id})


lead_repository = LeadRepository()

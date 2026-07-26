from typing import Optional

from core.database import db


class AutomationRunRepository:
    """Traccia, per ogni coppia (automazione, entità target — es. una
    specifica offerta/cliente/lead), l'esito dell'ultima esecuzione: serve
    sia a evitare di rieseguire la stessa azione più volte per la stessa
    condizione (dedup), sia a contare i tentativi falliti consecutivi per
    poter smettere di ritentare dopo una soglia (vedi AUTOMATION_MAX_ATTEMPTS
    in core/config.py)."""

    collection = db.automation_runs

    async def find_one(self, automation_id: str, target_id: str) -> Optional[dict]:
        return await self.collection.find_one(
            {"automation_id": automation_id, "target_id": target_id}, {"_id": 0}
        )

    async def upsert(self, automation_id: str, user_id: str, target_type: str, target_id: str, data: dict) -> None:
        await self.collection.update_one(
            {"automation_id": automation_id, "target_id": target_id},
            {"$set": {
                "automation_id": automation_id,
                "user_id": user_id,
                "target_type": target_type,
                "target_id": target_id,
                **data,
            }},
            upsert=True,
        )

    async def find_many_by_automation(self, automation_id: str, limit: int = 200) -> list:
        return await self.collection.find({"automation_id": automation_id}, {"_id": 0}) \
            .sort("updated_at", -1).to_list(limit)

    async def delete_by_automation(self, automation_id: str) -> None:
        """Ripulisce lo storico esecuzioni quando l'automazione stessa viene
        cancellata, per non lasciare record orfani in questa collection."""
        await self.collection.delete_many({"automation_id": automation_id})


automation_run_repository = AutomationRunRepository()

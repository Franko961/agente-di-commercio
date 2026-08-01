from core.database import db
from core.utils import now_iso


class ManualCommissionRepository:
    """Provvigioni inserite manualmente dall'utente, una per (utente, mese
    'YYYY-MM'): si sommano al totale calcolato dagli ordini per coprire
    provvigioni non tracciate tramite il flusso ordini del CRM (es. un
    accordo concluso fuori sistema) — vedi services/commission_service.py.
    Indice univoco su (user_id, period) creato in startup_service.py:
    upsert() si affida a quello per restare un solo documento per mese,
    anche in caso di due richieste quasi simultanee sullo stesso periodo."""

    collection = db.manual_commissions

    async def find_many(self, user_id: str) -> list:
        return await self.collection.find({"user_id": user_id}, {"_id": 0}).to_list(500)

    async def upsert(self, user_id: str, period: str, amount: float) -> dict:
        now = now_iso()
        doc = {"user_id": user_id, "period": period, "amount": amount, "updated_at": now}
        await self.collection.update_one(
            {"user_id": user_id, "period": period},
            {"$set": doc, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        return doc

    async def delete(self, user_id: str, period: str) -> None:
        await self.collection.delete_one({"user_id": user_id, "period": period})


manual_commission_repository = ManualCommissionRepository()

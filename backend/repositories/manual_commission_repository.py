from core.database import db
from core.utils import now_iso


class ManualCommissionRepository:
    """Provvigioni inserite manualmente dall'utente: una lista libera per
    utente (più righe possono coesistere nello stesso mese — es. un premio
    per un mandante e una rettifica per un altro), si sommano al totale
    calcolato dagli ordini per coprire provvigioni non tracciate tramite il
    flusso ordini del CRM (es. un accordo concluso fuori sistema) — vedi
    services/commission_service.py. Nessun indice univoco composto: l'unica
    chiave è id (come per le provvigioni reali in commission_repository),
    indice su user_id in services/startup/indexes.py solo per le query, non univoco."""

    collection = db.manual_commissions

    async def find_many(self, user_id: str) -> list:
        return await self.collection.find({"user_id": user_id}, {"_id": 0}).to_list(500)

    async def insert(self, doc: dict) -> dict:
        doc = {**doc, "created_at": now_iso(), "updated_at": now_iso()}
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def update(self, cid: str, user_id: str, fields: dict) -> bool:
        result = await self.collection.update_one(
            {"id": cid, "user_id": user_id},
            {"$set": {**fields, "updated_at": now_iso()}},
        )
        return result.matched_count > 0

    async def delete(self, cid: str, user_id: str) -> None:
        await self.collection.delete_one({"id": cid, "user_id": user_id})


manual_commission_repository = ManualCommissionRepository()

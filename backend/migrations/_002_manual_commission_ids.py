"""Migrazione una tantum: i documenti creati PRIMA dell'introduzione del CRUD
per id (quando l'upsert era per (user_id, period), vedi il vecchio
manual_commission_repository.py) non hanno mai avuto un campo id. Da quando
l'unicità su (user_id, period) è stata tolta (vedi
services.startup.indexes.create_indexes), due righe senza id potrebbero finire
a condividere lo stesso fallback sintetico in
commission_service.normalize_manual_commission (f"manual:{period}"), una
collisione prima impossibile perché l'indice univoco garantiva un solo
documento per mese. Backfillare qui un id reale su ogni documento esistente
chiude il problema alla radice."""

from core.database import db
from core.utils import gen_id


async def run() -> None:
    async for doc in db.manual_commissions.find({"id": {"$exists": False}}, {"_id": 1}):
        await db.manual_commissions.update_one(
            {"_id": doc["_id"]}, {"$set": {"id": gen_id()}}
        )

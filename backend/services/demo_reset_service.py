import logging

from core.database import db
from services.gdpr_service import USER_SCOPED_COLLECTIONS
from services.storage_service import storage_delete
from services.seed_service import seed_service

logger = logging.getLogger(__name__)


class DemoResetService:
    """Ripulisce e riseminata periodicamente i dati di ogni account demo
    condiviso (is_demo=True).

    Strategia: l'account demo è sola lettura sui dati del CRM — chi lo
    visita può esplorare i dati seminati, ma create/update/delete su
    clienti, offerte, ordini, documenti, automazioni, ecc. sono bloccati a
    monte da forbid_demo_write (core/security.py) su ogni rotta scrivente, e
    la connessione Google Calendar è bloccata allo stesso modo (vedi
    google_calendar_service.get_auth_url/handle_oauth_callback), non solo i
    dati CRM interni. Questo reset periodico NON è quindi la difesa
    principale contro le modifiche dei visitatori (quella è
    forbid_demo_write): è una rete di sicurezza residua — copre eventuali
    scritture sfuggite a una protezione futura non ancora applicata a una
    nuova rotta, e riporta comunque i dati seminati a uno stato pulito nel
    tempo. Il documento utente stesso (login, is_demo, email) NON viene
    toccato, solo tutti i dati collegati — a differenza della cancellazione
    account GDPR, di cui riusa la stessa lista di collection e la stessa
    pulizia S3."""

    async def reset_all_demo_accounts(self) -> int:
        demo_users = await db.users.find({"is_demo": True}, {"_id": 0, "id": 1}).to_list(50)
        for u in demo_users:
            await self._reset_one(u["id"])
        return len(demo_users)

    async def _reset_one(self, user_id: str) -> None:
        # Cancella davvero i file dei documenti caricati su S3, non solo i
        # record — altrimenti si accumulerebbero indefinitamente ad ogni
        # ciclo, esattamente il problema che il reset dovrebbe risolvere.
        documents = await db.documents.find({"user_id": user_id}, {"_id": 0, "storage_path": 1}).to_list(20000)
        for doc in documents:
            storage_path = doc.get("storage_path")
            if not storage_path:
                continue
            try:
                storage_delete(storage_path)
            except Exception as e:
                logger.warning(f"Reset demo: impossibile cancellare file S3 {storage_path}: {e}")

        for collection_name in USER_SCOPED_COLLECTIONS.values():
            await db[collection_name].delete_many({"user_id": user_id})

        # seed_demo si ferma subito se trova già dati (count(user_id) > 0 su
        # mandanti): funziona solo perché la collection è stata appena
        # svuotata sopra, altrimenti non riseminerebbe nulla.
        await seed_service.seed_demo(user_id)
        logger.info(f"Reset periodico account demo completato per user {user_id}")


demo_reset_service = DemoResetService()

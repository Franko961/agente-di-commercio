import logging
from core.utils import gen_id, now_iso
from repositories.appointment_repository import appointment_repository

logger = logging.getLogger(__name__)


class AppointmentService:
    def __init__(self, repo=appointment_repository):
        self.repo = repo

    async def list_appointments(self, user: dict) -> list:
        return await self.repo.find_many(user["id"])

    async def create_appointment(self, user: dict, payload) -> dict:
        doc = {"id": gen_id(), "user_id": user["id"], **payload.model_dump(), "created_at": now_iso()}
        doc = await self.repo.insert(doc)
        await self._push_to_google_calendar_safe(user["id"], doc, action="create")
        return doc

    async def create_many(self, user: dict, payloads: list) -> list:
        # In sequenza (non asyncio.gather) e non su repo.insert_many: ogni
        # appuntamento va creato con lo stesso percorso di create_appointment
        # per ottenere un "id" locale prima del push verso Google Calendar
        # (push_create lo usa per salvare il google_event_id di ritorno) — un
        # insert_many bulk grezzo salterebbe del tutto la sincronizzazione.
        return [await self.create_appointment(user, payload) for payload in payloads]

    async def update_appointment(self, user: dict, aid: str, payload) -> None:
        await self.repo.update(aid, user["id"], payload.model_dump())
        updated = await self.repo.find_one(aid, user["id"])
        if updated:
            await self._push_to_google_calendar_safe(user["id"], updated, action="update")

    async def delete_appointment(self, user: dict, aid: str) -> None:
        existing = await self.repo.find_one(aid, user["id"])
        await self.repo.delete(aid, user["id"])
        if existing and existing.get("google_event_id"):
            await self._push_to_google_calendar_safe(
                user["id"], existing, action="delete", google_event_id=existing["google_event_id"]
            )

    async def _push_to_google_calendar_safe(self, user_id: str, appointment: dict, action: str, google_event_id=None) -> None:
        # Import qui (non in cima al file) per evitare un ciclo di import tra i due servizi.
        from services.google_calendar_service import google_calendar_service
        try:
            if action == "create":
                await google_calendar_service.push_create(user_id, appointment)
            elif action == "update":
                await google_calendar_service.push_update(user_id, appointment)
            elif action == "delete":
                await google_calendar_service.push_delete(user_id, google_event_id)
        except Exception as e:
            # La sincronizzazione con Google non deve mai far fallire l'operazione su Salesfly.
            logger.error(f"Sync Google Calendar ({action}) fallita per user {user_id}: {e}")


appointment_service = AppointmentService()

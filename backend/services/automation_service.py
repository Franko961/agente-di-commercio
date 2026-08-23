from core.utils import gen_id, now_iso
from repositories.automation_repository import automation_repository
from repositories.automation_run_repository import automation_run_repository
from repositories.automation_notification_repository import automation_notification_repository


class AutomationService:
    def __init__(self, repo=automation_repository, run_repo=automation_run_repository,
                 notification_repo=automation_notification_repository):
        self.repo = repo
        self.run_repo = run_repo
        self.notification_repo = notification_repo

    async def list_automations(self, user: dict) -> list:
        return await self.repo.find_many(user["id"])

    async def create_automation(self, user: dict, payload) -> dict:
        doc = {"id": gen_id(), "user_id": user["id"], **payload.model_dump(), "created_at": now_iso()}
        return await self.repo.insert(doc)

    async def update_automation(self, user: dict, aid: str, payload) -> None:
        await self.repo.update(aid, user["id"], payload.model_dump())

    async def delete_automation(self, user: dict, aid: str) -> None:
        await self.repo.delete(aid, user["id"])
        # Ripulisce anche lo storico esecuzioni legato a questa automazione,
        # altrimenti resterebbero record orfani in automation_runs.
        await self.run_repo.delete_by_automation(aid, user["id"])

    # ------------------------------------------------------------------
    # Notifiche in-app generate dal motore (automation_engine)
    # ------------------------------------------------------------------
    async def list_notifications(self, user: dict, unread_only: bool = False) -> list:
        return await self.notification_repo.find_many(user["id"], unread_only=unread_only)

    async def mark_notification_read(self, user: dict, nid: str) -> None:
        await self.notification_repo.mark_read(nid, user["id"])

    async def list_runs(self, user: dict, aid: str) -> list:
        """Storico delle esecuzioni di una specifica automazione (ultima
        esecuzione per ciascuna entita' target), utile per capire perche'
        una regola non sembra aver fatto nulla."""
        automation = next((a for a in await self.repo.find_many(user["id"]) if a["id"] == aid), None)
        if not automation:
            return []
        return await self.run_repo.find_many_by_automation(aid, user["id"])


automation_service = AutomationService()

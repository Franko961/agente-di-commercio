import logging

from core.utils import gen_id, now_iso
from repositories.email_log_repository import email_log_repository

logger = logging.getLogger(__name__)


class EmailLogService:
    def __init__(self, repo=email_log_repository):
        self.repo = repo

    async def send_mock(self, user: dict, payload) -> dict:
        """MOCKED email sender - logs to db.email_logs only. No real delivery."""
        log = {
            "id": gen_id(),
            "user_id": user["id"],
            **payload.model_dump(),
            "status": "logged",
            "mocked": True,
            "created_at": now_iso(),
        }
        await self.repo.insert(log)
        logger.info(f"[MOCK EMAIL] To: {payload.to} | Subject: {payload.subject}")
        return {"ok": True, "mocked": True, "id": log["id"]}

    async def list_logs(self, user: dict) -> list:
        return await self.repo.find_many(user["id"])


email_log_service = EmailLogService()

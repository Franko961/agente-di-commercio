import os
from fastapi import HTTPException

from core.config import PLANS
from repositories.admin_repository import admin_repository

ALLOWED_USER_UPDATE_FIELDS = {"plan", "subscription_status", "role"}


class AdminService:
    def __init__(self, repo=admin_repository):
        self.repo = repo

    async def make_admin(self, email: str, secret: str) -> dict:
        """Promuove un utente ad admin. Richiede ADMIN_SECRET."""
        expected_secret = os.environ.get("ADMIN_SECRET", "")
        if not expected_secret or secret != expected_secret:
            raise HTTPException(403, "Secret non valido")
        email = email.lower().strip()
        if not email:
            raise HTTPException(400, "Email mancante")
        promoted = await self.repo.promote_by_email(email)
        if not promoted:
            raise HTTPException(404, f"Utente {email} non trovato")
        return {"ok": True, "message": f"{email} è ora admin"}

    async def get_stats(self) -> dict:
        total = await self.repo.count_agents()
        active = await self.repo.count_agents({"subscription_status": "active"})
        trial = await self.repo.count_agents({"subscription_status": "trial"})
        cancelled = await self.repo.count_agents({"subscription_status": "cancelled"})
        base = await self.repo.count_agents({"plan": "base", "subscription_status": "active"})
        pro = await self.repo.count_agents({"plan": "pro", "subscription_status": "active"})
        mrr = (base * PLANS["base"]["price_eur"]) + (pro * PLANS["pro"]["price_eur"])
        return {
            "total_users": total,
            "active": active,
            "trial": trial,
            "cancelled": cancelled,
            "plan_base": base,
            "plan_pro": pro,
            "mrr": round(mrr, 2),
            "arr": round(mrr * 12, 2),
        }

    async def list_users(self, page: int = 1, limit: int = 50) -> dict:
        users = await self.repo.find_agents(page, limit)
        total = await self.repo.count_agents()
        return {"users": users, "total": total, "page": page}

    async def update_user(self, uid: str, payload: dict) -> None:
        update = {k: v for k, v in payload.items() if k in ALLOWED_USER_UPDATE_FIELDS}
        if not update:
            raise HTTPException(400, "Nessun campo valido")
        await self.repo.update_user(uid, update)

    async def delete_user(self, uid: str) -> None:
        await self.repo.delete_user(uid)


admin_service = AdminService()

import os
import secrets
from datetime import datetime, timezone
from fastapi import HTTPException

from core.config import PLANS
from core.database import db
from core.rate_limit import check_and_record
from repositories.admin_repository import admin_repository

ALLOWED_USER_UPDATE_FIELDS = {"plan", "subscription_status", "role"}


class AdminService:
    def __init__(self, repo=admin_repository):
        self.repo = repo

    async def _record_audit(self, actor: str, action: str, target_user_id: str = None, detail: dict = None) -> None:
        """Traccia ogni azione amministrativa distruttiva/sensibile (chi,
        cosa, su chi, quando) — distinto dal registro azioni AI già
        esistente, che riguarda le azioni CRM fatte dagli agenti, non quelle
        di amministrazione della piattaforma."""
        try:
            await db.admin_audit_log.insert_one({
                "actor": actor,
                "action": action,
                "target_user_id": target_user_id,
                "detail": detail or {},
                "created_at": datetime.now(timezone.utc),
            })
        except Exception:
            pass  # l'audit log non deve mai far fallire l'azione amministrativa reale

    async def make_admin(self, email: str, secret: str, ip_address: str = None) -> dict:
        """Promuove un utente ad admin. Richiede ADMIN_SECRET.

        Endpoint non autenticato per natura (serve a creare il PRIMO admin,
        prima che esista una sessione con privilegi): la sicurezza dipende
        interamente dalla segretezza di ADMIN_SECRET. Per questo:
        - il confronto usa secrets.compare_digest (a tempo costante), non
          '!=', per non lasciare trapelare quanti caratteri iniziali del
          secret sono corretti tramite differenze di tempo di risposta;
        - i tentativi sono limitati per email e per IP (stesso principio già
          applicato a forgot-password in auth_service), per non lasciare la
          porta aperta a un tentativo di forza bruta illimitato su un
          secret eventualmente debole.
        """
        email = email.lower().strip()
        if email:
            email_ok = await check_and_record("make_admin_email", email, max_attempts=5, window_minutes=60)
            if not email_ok:
                raise HTTPException(429, "Troppi tentativi, riprova più tardi")
        if ip_address:
            ip_ok = await check_and_record("make_admin_ip", ip_address, max_attempts=10, window_minutes=60)
            if not ip_ok:
                raise HTTPException(429, "Troppi tentativi, riprova più tardi")

        expected_secret = os.environ.get("ADMIN_SECRET", "")
        if not expected_secret or not secrets.compare_digest(secret, expected_secret):
            await self._record_audit("bootstrap (ADMIN_SECRET)", "make_admin_failed", detail={"email": email, "ip": ip_address})
            raise HTTPException(403, "Secret non valido")
        if not email:
            raise HTTPException(400, "Email mancante")
        promoted = await self.repo.promote_by_email(email)
        if not promoted:
            raise HTTPException(404, f"Utente {email} non trovato")
        await self._record_audit("bootstrap (ADMIN_SECRET)", "make_admin", detail={"email": email, "ip": ip_address})
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

    async def update_user(self, uid: str, payload: dict, admin: dict = None) -> None:
        update = {k: v for k, v in payload.items() if k in ALLOWED_USER_UPDATE_FIELDS}
        if not update:
            raise HTTPException(400, "Nessun campo valido")
        await self.repo.update_user(uid, update)
        await self._record_audit(
            admin.get("email", admin.get("id")) if admin else "sconosciuto",
            "update_user", target_user_id=uid, detail=update,
        )

    async def delete_user(self, uid: str, admin: dict = None) -> None:
        await self.repo.delete_user(uid)
        await self._record_audit(
            admin.get("email", admin.get("id")) if admin else "sconosciuto",
            "delete_user", target_user_id=uid,
        )

    async def get_audit_log(self, page: int = 1, limit: int = 50) -> dict:
        skip = (page - 1) * limit
        entries = await db.admin_audit_log.find({}, {"_id": 0}).sort("created_at", -1).skip(skip).to_list(limit)
        total = await db.admin_audit_log.count_documents({})
        return {"entries": entries, "total": total, "page": page}


admin_service = AdminService()

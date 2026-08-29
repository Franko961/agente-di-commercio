import os
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException

from core.config import PLANS
from core.database import db
from core.rate_limit import check_and_record
from core.security import EXTRA_MODULE_KEYS, MODULE_KEYS, create_impersonation_token
from models.admin import IMPERSONATION_CATEGORIES
from repositories.admin_repository import admin_repository
from repositories.user_repository import user_repository
from services.gdpr_service import gdpr_service

ALLOWED_USER_UPDATE_FIELDS = {
    "plan",
    "subscription_status",
    "role",
    "disabled_modules",
    "enabled_extra_modules",
}


class AdminService:
    def __init__(self, repo=admin_repository):
        self.repo = repo

    async def _record_audit(
        self,
        actor: str,
        action: str,
        target_user_id: Optional[str] = None,
        detail: Optional[dict] = None,
    ) -> None:
        """Traccia ogni azione amministrativa distruttiva/sensibile (chi,
        cosa, su chi, quando) — distinto dal registro azioni AI già
        esistente, che riguarda le azioni CRM fatte dagli agenti, non quelle
        di amministrazione della piattaforma."""
        try:
            await db.admin_audit_log.insert_one(
                {
                    "actor": actor,
                    "action": action,
                    "target_user_id": target_user_id,
                    "detail": detail or {},
                    "created_at": datetime.now(timezone.utc),
                }
            )
        except Exception:
            pass  # l'audit log non deve mai far fallire l'azione amministrativa reale

    async def make_admin(
        self, email: str, secret: str, ip_address: Optional[str] = None
    ) -> dict:
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
            email_ok = await check_and_record(
                "make_admin_email", email, max_attempts=5, window_minutes=60
            )
            if not email_ok:
                raise HTTPException(429, "Troppi tentativi, riprova più tardi")
        if ip_address:
            ip_ok = await check_and_record(
                "make_admin_ip", ip_address, max_attempts=10, window_minutes=60
            )
            if not ip_ok:
                raise HTTPException(429, "Troppi tentativi, riprova più tardi")

        expected_secret = os.environ.get("ADMIN_SECRET", "")
        if not expected_secret or not secrets.compare_digest(secret, expected_secret):
            await self._record_audit(
                "bootstrap (ADMIN_SECRET)",
                "make_admin_failed",
                detail={"email": email, "ip": ip_address},
            )
            raise HTTPException(403, "Secret non valido")
        if not email:
            raise HTTPException(400, "Email mancante")
        promoted = await self.repo.promote_by_email(email)
        if not promoted:
            raise HTTPException(404, f"Utente {email} non trovato")
        await self._record_audit(
            "bootstrap (ADMIN_SECRET)",
            "make_admin",
            detail={"email": email, "ip": ip_address},
        )
        return {"ok": True, "message": f"{email} è ora admin"}

    async def get_stats(self) -> dict:
        total = await self.repo.count_agents()
        active = await self.repo.count_agents({"subscription_status": "active"})
        trial = await self.repo.count_agents({"subscription_status": "trial"})
        cancelled = await self.repo.count_agents({"subscription_status": "cancelled"})
        base = await self.repo.count_agents(
            {"plan": "base", "subscription_status": "active"}
        )
        pro = await self.repo.count_agents(
            {"plan": "pro", "subscription_status": "active"}
        )
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

    async def update_user(
        self, uid: str, payload: dict, admin: Optional[dict] = None
    ) -> None:
        update = {k: v for k, v in payload.items() if k in ALLOWED_USER_UPDATE_FIELDS}
        if not update:
            raise HTTPException(400, "Nessun campo valido")
        if "disabled_modules" in update:
            modules = update["disabled_modules"]
            if not isinstance(modules, list) or any(
                m not in MODULE_KEYS for m in modules
            ):
                raise HTTPException(400, "disabled_modules non valido")
        if "enabled_extra_modules" in update:
            modules = update["enabled_extra_modules"]
            if not isinstance(modules, list) or any(
                m not in EXTRA_MODULE_KEYS for m in modules
            ):
                raise HTTPException(400, "enabled_extra_modules non valido")
        await self.repo.update_user(uid, update)
        await self._record_audit(
            str(admin.get("email", admin.get("id"))) if admin else "sconosciuto",
            "update_user",
            target_user_id=uid,
            detail=update,
        )

    async def delete_user(self, uid: str, admin: Optional[dict] = None) -> None:
        # Riusa lo stesso nucleo di cancellazione della cancellazione
        # self-service (services/gdpr_service._erase_user_data): prima
        # cancellava solo il documento utente, lasciando un eventuale
        # abbonamento Stripe/PayPal attivo a fatturare per sempre (nessun
        # account a cui ricollegarlo) e tutti i dati/file del cliente
        # orfani — la stessa identica azione concettuale trattata in modo
        # molto più superficiale a seconda di chi la avviava.
        await gdpr_service._erase_user_data(uid)
        await self._record_audit(
            str(admin.get("email", admin.get("id"))) if admin else "sconosciuto",
            "delete_user",
            target_user_id=uid,
        )

    async def impersonate_user(
        self,
        uid: str,
        admin: dict,
        mode: str = "view",
        reason: Optional[str] = None,
        category: Optional[str] = None,
    ) -> tuple:
        """Genera un token che autentica chi chiama come l'utente uid,
        per poter entrare nel suo gestionale quando serve assistenza (es.
        una richiesta telefonica di modificare qualcosa). Ritorna
        (token, email_utente_target).

        Controlli oltre a require_admin (già applicato dal router):
        - non ha senso "impersonificare" se stessi;
        - un admin non impersonifica un altro admin — restrizione di
          sicurezza aggiuntiva, anche se in pratica list_users/find_agents
          esclude già gli admin dall'elenco mostrato in UI (filtra
          role="agent"), quindi questo caso non dovrebbe essere raggiungibile
          dall'interfaccia stessa;
        - mode deve essere "view" (default, sola lettura — vedi
          core.security.forbid_demo_write) o "edit" (scrittura consentita);
        - category è SEMPRE obbligatoria (anche in sola lettura): anche un
          accesso che non modifica nulla deve dichiarare almeno il motivo di
          massima nell'audit log, non solo chi/su chi/quando;
        - mode "edit" richiede IN PIÙ un motivo testuale libero non vuoto:
          un accesso con permessi di scrittura merita un dettaglio preciso
          (chi ha modificato cosa e perché), non solo una categoria
          generica."""
        if uid == admin["id"]:
            raise HTTPException(400, "Non puoi impersonificare te stesso")
        target = await user_repository.find_by_id(uid)
        if not target:
            raise HTTPException(404, "Utente non trovato")
        if target.get("role") == "admin":
            raise HTTPException(
                403, "Non è possibile impersonificare un altro amministratore"
            )
        if mode not in ("view", "edit"):
            raise HTTPException(400, "Modalità non valida")
        if category not in IMPERSONATION_CATEGORIES:
            raise HTTPException(400, "Indica una categoria valida per l'accesso")
        reason = (reason or "").strip()
        if mode == "edit" and not reason:
            raise HTTPException(400, "Indica un motivo per accedere in modifica")

        token = create_impersonation_token(admin["id"], uid, target["email"], mode=mode)
        detail = {"target_email": target["email"], "mode": mode, "category": category}
        if mode == "edit":
            detail["reason"] = reason
        await self._record_audit(
            str(admin.get("email", admin.get("id"))),
            "impersonate_user",
            target_user_id=uid,
            detail=detail,
        )
        return token, target["email"]

    async def record_impersonation_exit(
        self,
        actor: str,
        target_user_id: str,
        target_email: str,
        mode: str,
        started_at: Optional[datetime] = None,
    ) -> None:
        """Traccia la FINE di una sessione di impersonificazione (vedi
        impersonate_user per l'inizio): senza questo, l'audit log diceva solo
        quando una sessione era cominciata, mai quando è finita o quanto è
        durata — chiamato da POST /api/auth/exit-impersonation."""
        ended_at = datetime.now(timezone.utc)
        duration_seconds = None
        if started_at:
            duration_seconds = round((ended_at - started_at).total_seconds())
        await self._record_audit(
            actor,
            "exit_impersonation",
            target_user_id=target_user_id,
            detail={
                "target_email": target_email,
                "mode": mode,
                "started_at": started_at.isoformat() if started_at else None,
                "ended_at": ended_at.isoformat(),
                "duration_seconds": duration_seconds,
            },
        )

    async def get_audit_log(self, page: int = 1, limit: int = 50) -> dict:
        skip = (page - 1) * limit
        entries = (
            await db.admin_audit_log.find({}, {"_id": 0})
            .sort("created_at", -1)
            .skip(skip)
            .to_list(limit)
        )
        total = await db.admin_audit_log.count_documents({})
        return {"entries": entries, "total": total, "page": page}


admin_service = AdminService()

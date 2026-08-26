from fastapi import HTTPException

from core.config import PLANS
from core.utils import local_month_start_utc_iso


async def enforce_ai_message_quota(repo, user: dict) -> None:
    """Blocca la chat AI se l'utente ha esaurito il limite mensile di
    messaggi del proprio piano (vedi PLANS['ai_monthly_message_limit'] in
    core/config.py — None significa nessun limite, es. piano Pro).
    Gli admin non sono mai soggetti al limite, coerentemente con l'esenzione
    già applicata al gate del trial in core/security.get_current_user."""
    if user.get("role") == "admin":
        return
    plan = PLANS.get(user.get("plan", "base"), PLANS["base"])
    limit = plan.get("ai_monthly_message_limit")
    if limit is None:
        return
    used = await repo.count_since(user["id"], local_month_start_utc_iso())
    if used >= limit:
        raise HTTPException(
            402,
            f"Hai raggiunto il limite di {limit} messaggi AI del piano {plan['name']} per questo mese. "
            "Passa al piano Pro per messaggi illimitati.",
        )

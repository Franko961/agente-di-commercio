from datetime import datetime, timezone
from typing import List
from core.utils import gen_id, now_iso
from repositories.commission_repository import commission_repository
from repositories.mandante_repository import mandante_repository


def calc_offer_total(items: List[dict]) -> float:
    total = 0.0
    for it in items:
        sub = it.get("quantity", 1) * it.get("unit_price", 0) * (1 - it.get("discount", 0) / 100)
        total += sub
    return round(total, 2)


def get_commission_rate(mandante: dict, sale_type: str) -> float:
    """Restituisce l'aliquota da applicare in base al tipo di vendita (nuovo/rinnovo).
    Se il mandante non ha un'aliquota specifica impostata per quel tipo, usa quella standard."""
    if sale_type == "rinnovo" and mandante.get("commission_rate_renewal") is not None:
        return mandante["commission_rate_renewal"]
    if sale_type == "nuovo" and mandante.get("commission_rate_new") is not None:
        return mandante["commission_rate_new"]
    return mandante.get("commission_rate", 5.0)


class CommissionService:
    def __init__(self, repo=commission_repository, mandante_repo=mandante_repository):
        self.repo = repo
        self.mandante_repo = mandante_repo

    async def check_and_award_bonus(self, user_id: str, mandante_id: str):
        """Controlla lo scaglione piu alto della scala premi raggiunto dal mandante
        e mantiene una sola provvigione bonus corrispondente (non cumulativa):
        ogni nuovo scaglione raggiunto sostituisce quello precedente, non si somma."""
        mandante = await self.mandante_repo.find_one(mandante_id, user_id)
        if not mandante:
            return
        tiers = mandante.get("bonus_tiers", [])
        if not tiers:
            return

        commissions = await self.repo.find_many(user_id)
        commissions = [c for c in commissions if c.get("mandante_id") == mandante_id]

        def _base_amount(c):
            if c.get("base_amount") is not None:
                return c["base_amount"]
            rate = c.get("rate") or mandante.get("commission_rate", 5)
            return c.get("amount", 0) / (rate / 100) if rate else 0.0

        fatturato = sum(_base_amount(c) for c in commissions if c.get("sale_type") != "bonus")
        sorted_tiers = sorted(tiers, key=lambda t: t["threshold"])
        earned = [t for t in sorted_tiers if fatturato >= t["threshold"]]

        existing_bonus = [c for c in commissions if c.get("sale_type") == "bonus"]

        if not earned:
            for c in existing_bonus:
                await self.repo.delete(c["id"], user_id)
            return

        highest = earned[-1]

        to_remove = [c for c in existing_bonus if c.get("bonus_tier_threshold") != highest["threshold"]]
        for c in to_remove:
            await self.repo.delete(c["id"], user_id)

        already_correct = any(c.get("bonus_tier_threshold") == highest["threshold"] for c in existing_bonus)
        if already_correct:
            return

        bonus_comm = {
            "id": gen_id(), "user_id": user_id, "offer_id": None,
            "client_id": None, "mandante_id": mandante_id,
            "amount": round(highest.get("bonus", 0), 2), "rate": None, "base_amount": None,
            "sale_type": "bonus", "status": "maturato",
            "bonus_tier_threshold": highest["threshold"],
            "period": datetime.now(timezone.utc).strftime("%Y-%m"),
            "created_at": now_iso(),
        }
        await self.repo.insert(bonus_comm)

    async def list_commissions(self, user: dict) -> list:
        return await self.repo.find_many(user["id"])

    async def bonus_summary(self, user: dict) -> list:
        """Calcola i bonus raggiunti per ogni mandante in base al fatturato delle provvigioni."""
        mandanti = await self.mandante_repo.find_many(user["id"])
        commissions = await self.repo.find_many(user["id"])

        result = []
        for m in mandanti:
            tiers = m.get("bonus_tiers", [])
            if not tiers:
                continue

            def _base_amount(c: dict) -> float:
                if c.get("base_amount") is not None:
                    return c["base_amount"]
                rate = c.get("rate") or m.get("commission_rate", 5)
                return c.get("amount", 0) / (rate / 100) if rate else 0.0

            fatturato = sum(
                _base_amount(c) for c in commissions
                if c.get("mandante_id") == m["id"] and c.get("sale_type") != "bonus"
            )
            sorted_tiers = sorted(tiers, key=lambda t: t["threshold"])
            earned_tiers = [t for t in sorted_tiers if fatturato >= t["threshold"]]
            total_bonus = earned_tiers[-1]["bonus"] if earned_tiers else 0
            next_tier = next((t for t in sorted_tiers if fatturato < t["threshold"]), None)
            await self.check_and_award_bonus(user["id"], m["id"])
            result.append({
                "mandante_id": m["id"],
                "mandante_name": m["name"],
                "brand_color": m.get("brand_color", "#0A192F"),
                "fatturato": round(fatturato, 2),
                "total_bonus": round(total_bonus, 2),
                "earned_tiers": earned_tiers,
                "next_tier": next_tier,
                "tiers": sorted_tiers,
            })
        return result

    async def update_status(self, user: dict, cid: str, status: str) -> None:
        await self.repo.update_status(cid, user["id"], status)

    async def delete_commission(self, user: dict, cid: str) -> None:
        await self.repo.delete(cid, user["id"])


commission_service = CommissionService()


async def check_and_award_bonus(user_id: str, mandante_id: str):
    """Wrapper a livello di modulo, per compatibilità con il codice ancora nel monolite
    (AI assistant, firma offerta, seed data) che chiama questa funzione direttamente."""
    await commission_service.check_and_award_bonus(user_id, mandante_id)

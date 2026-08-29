from typing import List, Optional

from core.exceptions import NotFoundError
from core.utils import gen_id, now_iso, now_local
from repositories.commission_repository import commission_repository
from repositories.mandante_repository import mandante_repository
from repositories.manual_commission_repository import manual_commission_repository


def calc_offer_total(items: List[dict]) -> float:
    total = 0.0
    for it in items:
        sub = (
            it.get("quantity", 1)
            * it.get("unit_price", 0)
            * (1 - it.get("discount", 0) / 100)
        )
        total += sub
    return round(total, 2)


def get_commission_rate(mandante: dict, sale_type: str) -> float:
    """Restituisce l'aliquota da applicare in base al tipo di vendita (nuovo/rinnovo).
    Se il mandante non ha un'aliquota specifica impostata per quel tipo, usa quella standard.
    """
    if sale_type == "rinnovo" and mandante.get("commission_rate_renewal") is not None:
        return mandante["commission_rate_renewal"]
    if sale_type == "nuovo" and mandante.get("commission_rate_new") is not None:
        return mandante["commission_rate_new"]
    return mandante.get("commission_rate", 5.0)


def tiers_to_pay(tiers: List[dict], fatturato: float) -> List[dict]:
    """Determina quali scaglioni della scala premi vanno effettivamente pagati:
    - Il primo scaglione (soglia più bassa, es. 2000€) è fisso: se raggiunto, il suo
      bonus si somma sempre agli altri.
    - Tra gli scaglioni successivi, NON si sommano tra loro: conta solo il bonus dello
      scaglione più alto raggiunto, che si aggiunge al bonus del primo scaglione.
    Esempio: scaglioni 2000->500, 3000->360, 5000->600. Raggiunti 5000€ -> paga
    500 (base) + 600 (il più alto tra gli altri) = 1100. Il 360 non si somma.
    """
    if not tiers:
        return []
    sorted_tiers = sorted(tiers, key=lambda t: t["threshold"])
    base_tier = sorted_tiers[0]
    other_tiers = sorted_tiers[1:]

    to_pay = []
    if fatturato >= base_tier["threshold"]:
        to_pay.append(base_tier)

    earned_others = [t for t in other_tiers if fatturato >= t["threshold"]]
    if earned_others:
        to_pay.append(earned_others[-1])  # solo il più alto raggiunto tra gli "altri"

    return to_pay


class CommissionService:
    def __init__(
        self,
        repo=commission_repository,
        mandante_repo=mandante_repository,
        manual_repo=manual_commission_repository,
    ):
        self.repo = repo
        self.mandante_repo = mandante_repo
        self.manual_repo = manual_repo

    async def check_and_award_bonus(self, user_id: str, mandante_id: str):
        """Mantiene le provvigioni bonus corrette secondo la regola della scala premi:
        il primo scaglione (soglia più bassa) è fisso e si somma sempre; tra gli scaglioni
        successivi conta solo il più alto raggiunto (non si sommano tra loro). Vedi
        tiers_to_pay() per il dettaglio. Se il fatturato scende sotto uno scaglione già
        pagato, la provvigione bonus corrispondente viene rimossa."""
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

        fatturato = sum(
            _base_amount(c) for c in commissions if c.get("sale_type") != "bonus"
        )
        to_pay = tiers_to_pay(tiers, fatturato)
        to_pay_thresholds = {t["threshold"] for t in to_pay}

        existing_bonus = [c for c in commissions if c.get("sale_type") == "bonus"]

        # Rimuove le provvigioni bonus che non vanno più pagate
        to_remove = [
            c
            for c in existing_bonus
            if c.get("bonus_tier_threshold") not in to_pay_thresholds
        ]
        for c in to_remove:
            await self.repo.delete(c["id"], user_id)
        to_remove_ids = {c["id"] for c in to_remove}

        existing_thresholds = {
            c.get("bonus_tier_threshold")
            for c in existing_bonus
            if c["id"] not in to_remove_ids
        }

        # Crea la provvigione bonus per ogni scaglione da pagare che non ce l'ha ancora
        for tier in to_pay:
            if tier["threshold"] in existing_thresholds:
                continue
            bonus_comm = {
                "id": gen_id(),
                "user_id": user_id,
                "offer_id": None,
                "client_id": None,
                "mandante_id": mandante_id,
                "amount": round(tier.get("bonus", 0), 2),
                "rate": None,
                "base_amount": None,
                "sale_type": "bonus",
                "status": "maturato",
                "bonus_tier_threshold": tier["threshold"],
                # "period" identifica il mese in cui il bonus è stato
                # raggiunto: va calcolato in ora italiana, altrimenti un
                # bonus raggiunto nell'ora dopo la mezzanotte italiana
                # verrebbe etichettato ancora con il mese precedente (vedi
                # core/utils.now_local).
                "period": now_local().strftime("%Y-%m"),
                "created_at": now_iso(),
            }
            await self.repo.insert(bonus_comm)

    async def list_commissions(
        self, user: dict, mandante_id: Optional[str] = None
    ) -> list:
        return await self.repo.find_many(user["id"], mandante_id)

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
                _base_amount(c)
                for c in commissions
                if c.get("mandante_id") == m["id"] and c.get("sale_type") != "bonus"
            )
            sorted_tiers = sorted(tiers, key=lambda t: t["threshold"])
            earned_tiers = [t for t in sorted_tiers if fatturato >= t["threshold"]]
            total_bonus = sum(t["bonus"] for t in tiers_to_pay(tiers, fatturato))
            next_tier = next(
                (t for t in sorted_tiers if fatturato < t["threshold"]), None
            )
            await self.check_and_award_bonus(user["id"], m["id"])
            result.append(
                {
                    "mandante_id": m["id"],
                    "mandante_name": m["name"],
                    "brand_color": m.get("brand_color", "#0A192F"),
                    "fatturato": round(fatturato, 2),
                    "total_bonus": round(total_bonus, 2),
                    "earned_tiers": earned_tiers,
                    "next_tier": next_tier,
                    "tiers": sorted_tiers,
                }
            )
        return result

    async def update_status(self, user: dict, cid: str, status: Optional[str]) -> None:
        await self.repo.update_status(cid, user["id"], status)

    async def delete_commission(self, user: dict, cid: str) -> None:
        await self.repo.delete(cid, user["id"])

    async def list_manual_commissions(self, user: dict) -> list:
        return await self.manual_repo.find_many(user["id"])

    async def create_manual_commission(self, user: dict, fields: dict) -> dict:
        doc = {"id": gen_id(), "user_id": user["id"], **fields}
        return await self.manual_repo.insert(doc)

    async def update_manual_commission(
        self, user: dict, cid: str, fields: dict
    ) -> None:
        ok = await self.manual_repo.update(cid, user["id"], fields)
        if not ok:
            raise NotFoundError("Provvigione manuale non trovata")

    async def delete_manual_commission(self, user: dict, cid: str) -> None:
        await self.manual_repo.delete(cid, user["id"])

    async def get_effective_commissions(
        self,
        user: dict,
        mandante_id: Optional[str] = None,
        client_id: Optional[str] = None,
    ) -> list:
        """Provvigioni "vere" per dashboard/obiettivi/briefing AI/export/
        report: unisce quelle calcolate dagli ordini con quelle inserite
        manualmente, normalizzate nella stessa forma (vedi
        normalize_manual_commission). Una manuale senza mandante_id (o senza
        client_id) non è attribuibile a nessun mandante/cliente specifico:
        quando è passato un filtro corrispondente va esclusa, altrimenti si
        sommerebbe a un totale a cui non è riconducibile — stessa regola già
        applicata lato frontend in Commissions.jsx."""
        user_id = user["id"]
        real = await self.repo.find_many(user_id, mandante_id)
        manual = await self.manual_repo.find_many(user_id)
        if mandante_id:
            manual = [m for m in manual if m.get("mandante_id") == mandante_id]
        if client_id:
            real = [c for c in real if c.get("client_id") == client_id]
            manual = [m for m in manual if m.get("client_id") == client_id]
        normalized_manual = [normalize_manual_commission(user_id, m) for m in manual]
        return [
            {**c, "source": c.get("source", "order")} for c in real
        ] + normalized_manual


def normalize_manual_commission(user_id: str, m: dict) -> dict:
    """Adatta una provvigione manuale alla stessa forma di una calcolata
    dagli ordini, per poterle sommare/filtrare insieme a quelle reali —
    usata sia da CommissionService.get_effective_commissions sia dai
    consumer che interrogano manual_commission_repository/db.manual_commissions
    direttamente (dashboard_service, ai_service, automation_engine): questi
    ultimi non passano da commission_service, quindi la funzione resta
    indipendente da un'istanza del service. created_at è sintetico
    (mezzogiorno UTC del primo giorno di period, non il momento in cui la
    riga è stata salvata): i consumer confrontano il mese tramite
    local_month_str(created_at), non tramite period — usare l'orario reale
    di salvataggio farebbe contare una provvigione manuale di un mese
    passato nel mese corrente. Mezzogiorno (non mezzanotte) evita qualunque
    ambiguità di fuso: resta lo stesso giorno di calendario in ora italiana
    in ogni caso (CET o CEST). id: fallback sintetico usato SOLO da fixture
    di test prive di id — ogni documento reale ne ha sempre uno (creato da
    CommissionService.create_manual_commission, oppure backfillato dalla
    migrazione una tantum in startup_service.run_startup per i documenti
    creati prima che id esistesse). Il fallback resta basato su period per
    semplicità nei test, ma non deve mai essere raggiunto su dati reali:
    con period non più univoco, righe diverse senza id vi collidrebbero."""
    return {
        "id": m.get("id") or f"manual:{m['period']}",
        "user_id": user_id,
        "period": m["period"],
        "amount": m.get("amount", 0),
        "mandante_id": m.get("mandante_id"),
        "client_id": m.get("client_id"),
        "status": m.get("stato") or "maturato",
        "sale_type": m.get("tipo") or "ordinaria",
        "descrizione": m.get("descrizione"),
        "note": m.get("note"),
        "rate": None,
        "base_amount": None,
        "created_at": f"{m['period']}-01T12:00:00+00:00",
        "source": "manual",
    }


commission_service = CommissionService()


async def check_and_award_bonus(user_id: str, mandante_id: str):
    """Wrapper a livello di modulo, per compatibilità con il codice ancora nel monolite
    (AI assistant, firma offerta, seed data) che chiama questa funzione direttamente."""
    await commission_service.check_and_award_bonus(user_id, mandante_id)

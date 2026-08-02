import uuid
from datetime import datetime, timezone
from core.exceptions import NotFoundError
from core.database import db
from repositories.client_repository import client_repository
from repositories.mandante_repository import mandante_repository
from services.commission_service import normalize_manual_commission

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class ClientService:
    def __init__(self, repo=client_repository, mandante_repo=mandante_repository):
        self.repo = repo
        self.mandante_repo = mandante_repo

    async def list_clients(self, user: dict, zone=None, sector=None, potential=None, q=None, mandante_id=None):
        filters = {}
        if zone: filters["zone"] = zone
        if sector: filters["sector"] = sector
        if potential: filters["potential"] = potential
        if q:
            filters["$or"] = [
                {"company_name": {"$regex": q, "$options": "i"}},
                {"contact_name": {"$regex": q, "$options": "i"}},
                {"city": {"$regex": q, "$options": "i"}},
            ]
        return await self.repo.find_many(user["id"], filters, mandante_id)

    async def create_client(self, user: dict, payload) -> dict:
        doc = {"id": str(uuid.uuid4()), "user_id": user["id"], **payload.model_dump(), "created_at": _now_iso()}
        return await self.repo.insert(doc)

    async def get_client(self, user: dict, cid: str) -> dict:
        c = await self.repo.find_one(cid, user["id"])
        if not c:
            raise NotFoundError("Cliente non trovato")
        offers = await db.offers.find({"client_id": cid, "user_id": user["id"]}, {"_id": 0}).to_list(500)
        appts = await db.appointments.find({"client_id": cid, "user_id": user["id"]}, {"_id": 0}).to_list(500)
        docs = await db.documents.find({"client_id": cid, "user_id": user["id"]}, {"_id": 0}).to_list(500)
        commissions = await db.commissions.find({"client_id": cid, "user_id": user["id"]}, {"_id": 0}).to_list(500)
        # Le provvigioni manuali con questo client_id contano come vere
        # anche nel dettaglio cliente — vedi normalize_manual_commission.
        manual_raw = await db.manual_commissions.find({"client_id": cid, "user_id": user["id"]}, {"_id": 0}).to_list(500)
        manual_commissions = [normalize_manual_commission(user["id"], m) for m in manual_raw]
        commissions = [{**cm, "source": cm.get("source", "order")} for cm in commissions] + manual_commissions
        return {"client": c, "offers": offers, "appointments": appts, "documents": docs, "commissions": commissions}

    async def update_client(self, user: dict, cid: str, payload) -> None:
        ok = await self.repo.update(cid, user["id"], payload.model_dump())
        if not ok:
            raise NotFoundError("Cliente non trovato")

    async def delete_client(self, user: dict, cid: str) -> None:
        await self.repo.delete(cid, user["id"])

    async def bulk_import(self, user: dict, payload) -> dict:
        """Importa in blocco clienti da un file caricato direttamente
        dall'utente (CSV/Excel, già trasformato in righe dal frontend) —
        il percorso self-service, senza passare dall'assistente AI.

        Deduplica per partita IVA quando presente, altrimenti per la coppia
        (ragione sociale, città) case-insensitive: sia contro i clienti già
        nel CRM sia tra le righe dello stesso file, così ricaricare per
        errore lo stesso file (o un file che si sovrappone parzialmente a
        un'importazione precedente) non crea doppioni."""
        user_id = user["id"]
        existing = await self.repo.find_many(user_id, {})
        existing_vat = {c["vat_number"].strip().upper() for c in existing if (c.get("vat_number") or "").strip()}
        existing_name_city = {
            (c.get("company_name", "").strip().lower(), (c.get("city") or "").strip().lower())
            for c in existing
        }

        # Tutti i mandanti recuperati una sola volta e messi in mappa, invece
        # di una query per riga per risolvere ogni mandante_names — con un
        # file da centinaia di clienti sarebbe una query per riga (vedi la
        # stessa lezione già applicata altrove in dashboard_service).
        mandanti = await self.mandante_repo.find_many(user_id)
        mandanti_by_name = {m["name"].strip().lower(): m["id"] for m in mandanti}

        to_insert = []
        skipped = []
        seen_vat = set()
        seen_name_city = set()

        for idx, item in enumerate(payload.clients, start=1):
            if not item.company_name.strip():
                skipped.append({"row": idx, "company_name": item.company_name, "reason": "ragione sociale mancante"})
                continue

            vat = (item.vat_number or "").strip().upper()
            name_city = (item.company_name.strip().lower(), (item.city or "").strip().lower())

            if vat and (vat in existing_vat or vat in seen_vat):
                skipped.append({"row": idx, "company_name": item.company_name, "reason": "partita IVA già presente"})
                continue
            if not vat and name_city in existing_name_city.union(seen_name_city):
                skipped.append({"row": idx, "company_name": item.company_name, "reason": "ragione sociale e città già presenti"})
                continue

            # Nomi mandante non riconosciuti vengono semplicemente ignorati
            # (non bloccano l'import dell'intera riga per un nome scritto in
            # modo leggermente diverso da quello nel CRM).
            mandante_ids = []
            for raw_name in (item.mandante_names or "").replace(";", ",").split(","):
                raw_name = raw_name.strip()
                if raw_name and raw_name.lower() in mandanti_by_name:
                    mandante_ids.append(mandanti_by_name[raw_name.lower()])

            doc = {
                "id": str(uuid.uuid4()), "user_id": user_id,
                "company_name": item.company_name.strip(),
                "contact_name": item.contact_name or "",
                "email": item.email or "",
                "phone": item.phone or "",
                "vat_number": item.vat_number or "",
                "address": item.address or "",
                "city": item.city or "",
                "province": item.province or "",
                "zone": item.zone or "",
                "sector": item.sector or "",
                "potential": item.potential or "medio",
                "lat": None, "lng": None,
                "notes": item.notes or "",
                "mandante_ids": mandante_ids,
                "created_at": _now_iso(),
            }
            to_insert.append(doc)
            if vat:
                seen_vat.add(vat)
            else:
                seen_name_city.add(name_city)

        await self.repo.insert_many(to_insert)
        return {"imported": len(to_insert), "skipped": skipped, "total": len(payload.clients)}


client_service = ClientService()

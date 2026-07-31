import csv
import io
from typing import List
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from core.database import db
from core.rate_limit import check_and_record

# Caratteri che Excel/Google Sheets interpretano come inizio di una formula
# quando aprono un file CSV: un valore testuale come '=HYPERLINK(...)' o
# '=cmd|...' finito in un nome cliente, una nota, o un qualunque campo
# testuale libero verrebbe eseguito come formula da chi apre il file
# esportato — che potrebbe non essere la stessa persona che ha inserito
# quel dato (es. l'export viene girato al proprio mandante o commercialista).
# Vulnerabilità nota come "CSV Injection"/"Formula Injection" (OWASP).
_FORMULA_TRIGGER_CHARS = ("=", "+", "-", "@")


def _sanitize_csv_cell(value):
    """Antepone un apostrofo ai valori testuali che iniziano con un
    carattere che attiverebbe l'interpretazione come formula — la stessa
    convenzione che usa Excel per forzare un valore a essere trattato come
    testo, invisibile nella visualizzazione normale della cella. Si applica
    solo alle stringhe: i valori numerici (importi, conteggi) restano
    intatti, non essendo mai a rischio di questa vulnerabilità."""
    if isinstance(value, str) and value.startswith(_FORMULA_TRIGGER_CHARS):
        return "'" + value
    return value


def csv_response(rows: List[dict], headers: List[str], filename: str) -> StreamingResponse:
    buf = io.StringIO()
    buf.write("\ufeff")  # UTF-8 BOM for Excel
    writer = csv.DictWriter(buf, fieldnames=headers, delimiter=";", extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow({h: _sanitize_csv_cell(r.get(h, "")) for h in headers})
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class ExportService:
    async def _enforce_rate_limit(self, user: dict) -> None:
        """Ogni export legge fino a 5000 documenti su una o più collection
        (offerte/provvigioni uniscono anche clienti e mandanti): senza un
        limite, richiamarlo di continuo è un modo economico per generare
        carico pesante sul database — stessa protezione già applicata
        all'export equivalente lato GDPR (services/gdpr_service.py)."""
        ok = await check_and_record("csv_export", user["id"], max_attempts=20, window_minutes=10)
        if not ok:
            raise HTTPException(429, "Troppe esportazioni richieste, riprova tra qualche minuto")

    async def export_clients(self, user: dict) -> StreamingResponse:
        await self._enforce_rate_limit(user)
        clients = await db.clients.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)
        headers = ["company_name", "contact_name", "email", "phone", "vat_number",
                   "address", "city", "province", "zone", "sector", "potential", "notes"]
        return csv_response(clients, headers, "clienti.csv")

    async def export_offers(self, user: dict) -> StreamingResponse:
        await self._enforce_rate_limit(user)
        offers = await db.offers.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)
        clients = {c["id"]: c for c in await db.clients.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)}
        mandanti = {m["id"]: m for m in await db.mandanti.find({"user_id": user["id"]}, {"_id": 0}).to_list(500)}
        rows = []
        for o in offers:
            rows.append({
                "title": o.get("title"),
                "client": clients.get(o.get("client_id"), {}).get("company_name", ""),
                "mandante": mandanti.get(o.get("mandante_id"), {}).get("name", ""),
                "total": o.get("total", 0),
                "status": o.get("status"),
                "items_count": len(o.get("items", [])),
                "expires_at": (o.get("expires_at") or "")[:10],
                "created_at": (o.get("created_at") or "")[:10],
            })
        headers = ["title", "client", "mandante", "total", "status", "items_count", "expires_at", "created_at"]
        return csv_response(rows, headers, "offerte.csv")

    async def export_commissions(self, user: dict) -> StreamingResponse:
        await self._enforce_rate_limit(user)
        commissions = await db.commissions.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)
        clients = {c["id"]: c for c in await db.clients.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)}
        mandanti = {m["id"]: m for m in await db.mandanti.find({"user_id": user["id"]}, {"_id": 0}).to_list(500)}
        rows = []
        for c in commissions:
            rows.append({
                "period": c.get("period"),
                "client": clients.get(c.get("client_id"), {}).get("company_name", ""),
                "mandante": mandanti.get(c.get("mandante_id"), {}).get("name", ""),
                "amount": c.get("amount", 0),
                "rate": c.get("rate", 0),
                "status": c.get("status"),
            })
        headers = ["period", "client", "mandante", "amount", "rate", "status"]
        return csv_response(rows, headers, "provvigioni.csv")

    async def export_leads(self, user: dict) -> StreamingResponse:
        await self._enforce_rate_limit(user)
        leads = await db.leads.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)
        headers = ["company_name", "contact_name", "email", "phone", "source",
                   "estimated_value", "status", "notes", "created_at"]
        return csv_response(leads, headers, "lead.csv")


export_service = ExportService()

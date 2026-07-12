import csv
import io
from typing import List
from fastapi.responses import StreamingResponse
from core.database import db


def csv_response(rows: List[dict], headers: List[str], filename: str) -> StreamingResponse:
    buf = io.StringIO()
    buf.write("\ufeff")  # UTF-8 BOM for Excel
    writer = csv.DictWriter(buf, fieldnames=headers, delimiter=";", extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow({h: r.get(h, "") for h in headers})
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class ExportService:
    async def export_clients(self, user: dict) -> StreamingResponse:
        clients = await db.clients.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)
        headers = ["company_name", "contact_name", "email", "phone", "vat_number",
                   "address", "city", "province", "zone", "sector", "potential", "notes"]
        return csv_response(clients, headers, "clienti.csv")

    async def export_offers(self, user: dict) -> StreamingResponse:
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
        leads = await db.leads.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)
        headers = ["company_name", "contact_name", "email", "phone", "source",
                   "estimated_value", "status", "notes", "created_at"]
        return csv_response(leads, headers, "lead.csv")


export_service = ExportService()

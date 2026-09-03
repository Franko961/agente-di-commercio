import csv
import io
from datetime import date, timedelta
from typing import List, Optional

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from core.database import db
from core.exceptions import NotFoundError, ValidationAppError
from core.rate_limit import check_and_record
from core.utils import local_date_str, now_local
from repositories.mandante_repository import mandante_repository
from services.commission_service import commission_service, normalize_manual_commission
from services.mandante_report_service import build_mandante_report_pdf

# Caratteri che Excel/Google Sheets interpretano come inizio di una formula
# quando aprono un file CSV: un valore testuale come '=HYPERLINK(...)' o
# '=cmd|...' finito in un nome cliente, una nota, o un qualunque campo
# testuale libero verrebbe eseguito come formula da chi apre il file
# esportato — che potrebbe non essere la stessa persona che ha inserito
# quel dato (es. l'export viene girato al proprio mandante o commercialista).
# Vulnerabilità nota come "CSV Injection"/"Formula Injection" (OWASP).
# Identica su un vero .xlsx (vedi sanitize_cell_text più sotto, usata anche
# da attendance_xlsx_export.py): non è un problema specifico del CSV.
_FORMULA_TRIGGER_CHARS = ("=", "+", "-", "@")


def sanitize_cell_text(value):
    """Antepone un apostrofo ai valori testuali che iniziano con un
    carattere che attiverebbe l'interpretazione come formula — la stessa
    convenzione che usa Excel per forzare un valore a essere trattato come
    testo, invisibile nella visualizzazione normale della cella. Si applica
    solo alle stringhe: i valori numerici (importi, conteggi) restano
    intatti, non essendo mai a rischio di questa vulnerabilità."""
    if isinstance(value, str) and value.startswith(_FORMULA_TRIGGER_CHARS):
        return "'" + value
    return value


def csv_response(
    rows: List[dict], headers: List[str], filename: str
) -> StreamingResponse:
    buf = io.StringIO()
    buf.write("\ufeff")  # UTF-8 BOM for Excel
    writer = csv.DictWriter(
        buf, fieldnames=headers, delimiter=";", extrasaction="ignore"
    )
    writer.writeheader()
    for r in rows:
        writer.writerow({h: sanitize_cell_text(r.get(h, "")) for h in headers})
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def xlsx_response(wb, filename: str) -> StreamingResponse:
    """Serializza un openpyxl Workbook già costruito (vedi
    attendance_xlsx_export.py) in una risposta scaricabile — equivalente
    xlsx di csv_response qui sopra. Un BytesIO passato direttamente a
    StreamingResponse verrebbe iterato riga per riga (split su ogni byte
    b'\\n'), corrompendo un formato binario come .xlsx: va racchiuso in un
    iterabile a blocco unico, stesso accorgimento già usato da csv_response."""
    buf = io.BytesIO()
    wb.save(buf)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def pdf_response(pdf_bytes: bytes, filename: str) -> StreamingResponse:
    """Equivalente PDF di xlsx_response/csv_response qui sopra — stesso
    accorgimento del blocco unico (i PDF sono binari come gli xlsx)."""
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _parse_report_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValidationAppError(f"{field_name} non valida: usa il formato YYYY-MM-DD")


class ExportService:
    async def _enforce_rate_limit(self, user: dict) -> None:
        """Ogni export legge fino a 5000 documenti su una o più collection
        (offerte/provvigioni uniscono anche clienti e mandanti): senza un
        limite, richiamarlo di continuo è un modo economico per generare
        carico pesante sul database — stessa protezione già applicata
        all'export equivalente lato GDPR (services/gdpr_service.py)."""
        ok = await check_and_record(
            "csv_export", user["id"], max_attempts=20, window_minutes=10
        )
        if not ok:
            raise HTTPException(
                429, "Troppe esportazioni richieste, riprova tra qualche minuto"
            )

    async def export_clients(self, user: dict) -> StreamingResponse:
        await self._enforce_rate_limit(user)
        clients = await db.clients.find({"user_id": user["id"]}, {"_id": 0}).to_list(
            5000
        )
        headers = [
            "company_name",
            "contact_name",
            "email",
            "phone",
            "vat_number",
            "address",
            "city",
            "province",
            "zone",
            "sector",
            "potential",
            "notes",
        ]
        return csv_response(clients, headers, "clienti.csv")

    async def export_offers(self, user: dict) -> StreamingResponse:
        await self._enforce_rate_limit(user)
        offers = await db.offers.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)
        clients = {
            c["id"]: c
            for c in await db.clients.find({"user_id": user["id"]}, {"_id": 0}).to_list(
                5000
            )
        }
        mandanti = {
            m["id"]: m
            for m in await db.mandanti.find(
                {"user_id": user["id"]}, {"_id": 0}
            ).to_list(500)
        }
        rows = []
        for o in offers:
            rows.append(
                {
                    "title": o.get("title"),
                    "client": clients.get(o.get("client_id"), {}).get(
                        "company_name", ""
                    ),
                    "mandante": mandanti.get(o.get("mandante_id"), {}).get("name", ""),
                    "total": o.get("total", 0),
                    "status": o.get("status"),
                    "items_count": len(o.get("items", [])),
                    "expires_at": (o.get("expires_at") or "")[:10],
                    "created_at": (o.get("created_at") or "")[:10],
                }
            )
        headers = [
            "title",
            "client",
            "mandante",
            "total",
            "status",
            "items_count",
            "expires_at",
            "created_at",
        ]
        return csv_response(rows, headers, "offerte.csv")

    async def export_commissions(self, user: dict) -> StreamingResponse:
        await self._enforce_rate_limit(user)
        commissions = await db.commissions.find(
            {"user_id": user["id"]}, {"_id": 0}
        ).to_list(5000)
        # Le provvigioni inserite manualmente sono provvigioni vere a tutti
        # gli effetti (vedi commission_service.normalize_manual_commission):
        # vanno esportate insieme a quelle calcolate dagli ordini, marcate
        # come tali nella colonna "origine".
        manual_commissions_raw = await db.manual_commissions.find(
            {"user_id": user["id"]}, {"_id": 0}
        ).to_list(500)
        manual_commissions = [
            normalize_manual_commission(user["id"], m) for m in manual_commissions_raw
        ]
        clients = {
            c["id"]: c
            for c in await db.clients.find({"user_id": user["id"]}, {"_id": 0}).to_list(
                5000
            )
        }
        mandanti = {
            m["id"]: m
            for m in await db.mandanti.find(
                {"user_id": user["id"]}, {"_id": 0}
            ).to_list(500)
        }
        rows = []
        for c in commissions + manual_commissions:
            rows.append(
                {
                    "period": c.get("period"),
                    "client": clients.get(c.get("client_id"), {}).get(
                        "company_name", ""
                    ),
                    "mandante": mandanti.get(c.get("mandante_id"), {}).get("name", ""),
                    "amount": c.get("amount", 0),
                    "rate": c.get("rate") if c.get("rate") is not None else "",
                    "status": c.get("status"),
                    "origine": "manuale" if c.get("source") == "manual" else "ordine",
                }
            )
        headers = [
            "period",
            "client",
            "mandante",
            "amount",
            "rate",
            "status",
            "origine",
        ]
        return csv_response(rows, headers, "provvigioni.csv")

    async def export_mandante_report(
        self,
        user: dict,
        mandante_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> StreamingResponse:
        """Report PDF riepilogativo delle provvigioni di UN mandante in un
        intervallo di date, pensato per essere mandato al mandante stesso —
        vedi services/mandante_report_service.py per il contenuto/layout e
        per la nota sul perché non è un documento fiscale."""
        await self._enforce_rate_limit(user)

        mandante = await mandante_repository.find_one(mandante_id, user["id"])
        if not mandante:
            raise NotFoundError("Mandante non trovato")

        # Date non specificate: dal primo giorno del mese corrente a oggi —
        # non l'intero mese corrente, che per un report generato a metà
        # mese includerebbe giorni futuri senza senso (nessuna provvigione
        # può ancora esistere per una data non ancora trascorsa).
        today = now_local().date()
        parsed_from = (
            _parse_report_date(date_from, "date_from")
            if date_from
            else today.replace(day=1)
        )
        parsed_to = _parse_report_date(date_to, "date_to") if date_to else today
        if parsed_from > parsed_to:
            raise ValidationAppError("date_from non può essere successiva a date_to")
        # Limite ampio ma non illimitato: un intervallo assurdo (es. 50 anni)
        # non ha senso per un report "per questo mandante in questo periodo"
        # e costringerebbe comunque a caricare/ordinare l'intero storico.
        if (parsed_to - parsed_from) > timedelta(days=5 * 365):
            raise ValidationAppError("L'intervallo di date non può superare 5 anni")

        commissions = await commission_service.get_effective_commissions(
            user, mandante_id=mandante_id
        )
        commissions = [
            c
            for c in commissions
            if parsed_from.isoformat()
            <= local_date_str(c.get("created_at"))
            <= parsed_to.isoformat()
        ]
        clients = {
            c["id"]: c
            for c in await db.clients.find({"user_id": user["id"]}, {"_id": 0}).to_list(
                5000
            )
        }

        pdf_bytes = build_mandante_report_pdf(
            user,
            mandante,
            commissions,
            clients,
            parsed_from.isoformat(),
            parsed_to.isoformat(),
        )
        safe_name = (
            "".join(
                ch if ch.isalnum() or ch in "-_" else "-" for ch in mandante["name"]
            ).strip("-")
            or "mandante"
        )
        filename = (
            f"report-{safe_name}-{parsed_from.isoformat()}_{parsed_to.isoformat()}.pdf"
        )
        return pdf_response(pdf_bytes, filename)

    async def export_leads(self, user: dict) -> StreamingResponse:
        await self._enforce_rate_limit(user)
        leads = await db.leads.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)
        headers = [
            "company_name",
            "contact_name",
            "email",
            "phone",
            "source",
            "estimated_value",
            "status",
            "notes",
            "created_at",
        ]
        return csv_response(leads, headers, "lead.csv")


export_service = ExportService()

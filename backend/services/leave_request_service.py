import html
import logging

from fastapi import HTTPException

from core.utils import gen_id, now_iso
from core.exceptions import NotFoundError, ValidationAppError
from core.config import FRONTEND_URL
from core.rate_limit import check_and_record
from repositories.leave_request_repository import leave_request_repository
from repositories.employee_repository import employee_repository
from repositories.user_repository import user_repository
from services.email_service import send_email
from services.export_service import csv_response

logger = logging.getLogger(__name__)

LEAVE_TYPE_LABELS = {"ferie": "Ferie", "permesso": "Permesso", "malattia": "Malattia"}


class LeaveRequestService:
    def __init__(self, repo=leave_request_repository, employees=employee_repository, users=user_repository):
        self.repo = repo
        self.employees = employees
        self.users = users

    async def submit(self, payload, ip_address: str = None) -> dict:
        """Endpoint pubblico (nessun login, vedi routers/leave_requests.py):
        il dipendente invia la richiesta tramite il proprio link personale,
        senza dover accedere al gestionale."""
        if ip_address:
            ok = await check_and_record("leave_request_ip", ip_address, max_attempts=10, window_minutes=60)
            if not ok:
                raise HTTPException(429, "Troppe richieste da questo indirizzo, riprova più tardi.")

        employee = await self.employees.find_by_token(payload.employee_token)
        if not employee or not employee.get("active", True):
            raise NotFoundError("Link non valido")

        if payload.date_to < payload.date_from:
            raise ValidationAppError("La data di fine non può precedere quella di inizio")

        doc = {
            "id": gen_id(),
            "user_id": employee["user_id"],
            "employee_id": employee["id"],
            # Denormalizzato apposta: se il dipendente viene in seguito
            # eliminato, la richiesta resta leggibile nello storico invece
            # di mostrare un riferimento orfano.
            "employee_name": employee["name"],
            "type": payload.type,
            "date_from": payload.date_from.isoformat(),
            "date_to": payload.date_to.isoformat(),
            "note": (payload.note or "").strip(),
            "status": "in_attesa",
            "created_at": now_iso(),
            "decided_at": None,
        }
        await self.repo.insert(doc)

        manager = await self.users.find_by_id(employee["user_id"])
        if manager and manager.get("email"):
            await send_email(
                to=manager["email"],
                subject=f"Nuova richiesta di {LEAVE_TYPE_LABELS.get(payload.type, payload.type)} — {employee['name']}",
                html=self._manager_email_html(doc),
            )

        return {"ok": True}

    async def list_requests(self, user: dict, status: str = None) -> list:
        return await self.repo.find_many(user["id"], status)

    async def decide(self, user: dict, rid: str, status: str) -> None:
        request = await self.repo.find_one(rid, user["id"])
        if not request:
            raise NotFoundError("Richiesta non trovata")
        if request["status"] != "in_attesa":
            raise ValidationAppError("Questa richiesta è già stata decisa")

        await self.repo.update(rid, user["id"], {"status": status, "decided_at": now_iso()})

        employee = await self.employees.find_one(request["employee_id"], user["id"])
        if employee and employee.get("email"):
            await send_email(
                to=employee["email"],
                subject=f"La tua richiesta di {LEAVE_TYPE_LABELS.get(request['type'], request['type'])} è stata {status}",
                html=self._employee_email_html(request, status),
            )

    async def calendar(self, user: dict, month: str) -> list:
        """month in formato AAAA-MM: restituisce le richieste APPROVATE che
        si sovrappongono almeno in parte a quel mese, per popolare la vista
        calendario presenze."""
        date_from = f"{month}-01"
        date_to = f"{month}-31"  # confronto testuale ISO: "31" oltre la fine del mese non è un problema, nessun giorno reale lo supera
        return await self.repo.find_overlapping(user["id"], date_from, date_to, status="approvata")

    async def export_csv(self, user: dict):
        ok = await check_and_record("csv_export", user["id"], max_attempts=20, window_minutes=10)
        if not ok:
            raise HTTPException(429, "Troppe esportazioni richieste, riprova tra qualche minuto")
        rows = await self.repo.find_many(user["id"])
        for r in rows:
            r["type_label"] = LEAVE_TYPE_LABELS.get(r["type"], r["type"])
        headers = ["employee_name", "type_label", "date_from", "date_to", "status", "note", "created_at"]
        return csv_response(rows, headers, "assenze.csv")

    @staticmethod
    def _manager_email_html(doc: dict) -> str:
        # employee_name e note arrivano in ultima analisi da un form pubblico
        # non autenticato (il nome è impostato dal manager stesso in fase di
        # creazione del dipendente, ma la nota la scrive il dipendente):
        # HTML-escaped per lo stesso motivo di contact_request_service.py.
        name = html.escape(doc["employee_name"])
        type_label = html.escape(LEAVE_TYPE_LABELS.get(doc["type"], doc["type"]))
        note = html.escape(doc["note"]) if doc["note"] else ""
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; color: #1a1a1a;">
          <h3 style="color:#0A192F;">Nuova richiesta di {type_label}</h3>
          <table style="width:100%; border-collapse: collapse; font-size: 14px;">
            <tr><td style="padding:4px 0; color:#52525B;">Dipendente</td><td><strong>{name}</strong></td></tr>
            <tr><td style="padding:4px 0; color:#52525B;">Dal</td><td>{doc['date_from']}</td></tr>
            <tr><td style="padding:4px 0; color:#52525B;">Al</td><td>{doc['date_to']}</td></tr>
          </table>
          {f'<div style="margin-top:16px; padding:12px 16px; background:#F9F9F8; border:1px solid #E4E4E1; border-radius:8px; font-size:14px; white-space:pre-wrap;">{note}</div>' if note else ''}
          <p style="font-size:13px; color:#52525B; margin-top:16px;">Approva o rifiuta dalla sezione Personale di SalesFly.</p>
        </div>
        """

    @staticmethod
    def _employee_email_html(doc: dict, status: str) -> str:
        type_label = html.escape(LEAVE_TYPE_LABELS.get(doc["type"], doc["type"]))
        esito = "approvata ✅" if status == "approvata" else "rifiutata ❌"
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; color: #1a1a1a;">
          <h3 style="color:#0A192F;">La tua richiesta è stata {esito}</h3>
          <table style="width:100%; border-collapse: collapse; font-size: 14px;">
            <tr><td style="padding:4px 0; color:#52525B;">Tipo</td><td><strong>{type_label}</strong></td></tr>
            <tr><td style="padding:4px 0; color:#52525B;">Dal</td><td>{doc['date_from']}</td></tr>
            <tr><td style="padding:4px 0; color:#52525B;">Al</td><td>{doc['date_to']}</td></tr>
          </table>
        </div>
        """


leave_request_service = LeaveRequestService()

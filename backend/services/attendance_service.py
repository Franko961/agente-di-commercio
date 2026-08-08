from fastapi import HTTPException

from core.utils import gen_id, now_iso
from core.exceptions import NotFoundError, ValidationAppError
from core.security import hash_reset_token, module_enabled
from core.rate_limit import check_and_record
from repositories.attendance_repository import attendance_repository
from repositories.employee_repository import employee_repository
from repositories.user_repository import user_repository


class AttendanceService:
    """Rilevazione presenze v1: solo timbratura ingresso/uscita con
    timestamp lato server (now_iso(), il dipendente non può dichiarare
    un orario diverso da quello reale) — deliberatamente SENZA
    geolocalizzazione. Il tracciamento della posizione dei dipendenti in
    Italia ricade sotto l'art. 4 dello Statuto dei Lavoratori (Legge
    300/1970) e richiede un accordo sindacale o l'autorizzazione
    dell'Ispettorato del Lavoro prima di poter essere attivato
    legalmente — fuori scope per questa prima versione."""

    def __init__(self, repo=attendance_repository, employees=employee_repository, users=user_repository):
        self.repo = repo
        self.employees = employees
        self.users = users

    async def _employee_from_token(self, token: str) -> dict:
        """Stesso schema di leave_request_service.submit: nessuna sessione
        autenticata da cui ricavare require_module, quindi il controllo sul
        modulo Personale va ripetuto qui contro il proprietario del
        dipendente — altrimenti un link generato prima della disattivazione
        del modulo resterebbe utilizzabile per timbrare."""
        employee = await self.employees.find_by_token_hash(hash_reset_token(token))
        if not employee or not employee.get("active", True):
            raise NotFoundError("Link non valido")
        owner = await self.users.find_by_id(employee["user_id"])
        if not owner or not module_enabled(owner, "personale"):
            raise NotFoundError("Link temporaneamente non disponibile")
        return employee

    async def _check_rate_limit(self, token: str, ip_address: str = None) -> None:
        if ip_address:
            ok = await check_and_record("attendance_clock_ip", ip_address, max_attempts=40, window_minutes=60)
            if not ok:
                raise HTTPException(429, "Troppe richieste da questo indirizzo, riprova più tardi.")
        # Limite per token oltre a quello per IP: un link condiviso per
        # errore verrebbe altrimenti usato per timbrare ripetutamente da
        # IP diversi, ognuno sotto la soglia per-IP (stesso principio già
        # applicato in leave_request_service.submit).
        token_ok = await check_and_record("attendance_clock_token", token, max_attempts=20, window_minutes=60)
        if not token_ok:
            raise HTTPException(429, "Troppe richieste per questo link, riprova più tardi.")

    async def status(self, token: str) -> dict:
        """Se il dipendente è attualmente in servizio (per mostrare
        "Timbra ingresso" o "Timbra uscita" nella pagina pubblica) e da
        quando."""
        employee = await self._employee_from_token(token)
        open_session = await self.repo.find_open_session(employee["id"], employee["user_id"])
        return {
            "clocked_in": open_session is not None,
            "since": open_session["clock_in"] if open_session else None,
        }

    async def clock_in(self, token: str, ip_address: str = None) -> dict:
        await self._check_rate_limit(token, ip_address)
        employee = await self._employee_from_token(token)
        existing = await self.repo.find_open_session(employee["id"], employee["user_id"])
        if existing:
            raise ValidationAppError("Sei già in servizio: registra prima l'uscita")

        doc = {
            "id": gen_id(),
            "user_id": employee["user_id"],
            "employee_id": employee["id"],
            # Denormalizzato apposta, stesso principio di vehicle_plate in
            # vehicle_deadline_service: resta leggibile nell'elenco anche
            # se il nome del dipendente cambia in seguito.
            "employee_name": f"{employee['name']} {employee.get('surname', '')}".strip(),
            "clock_in": now_iso(),
            "clock_out": None,
            "note": "",
            "corrected_by_admin": False,
            "created_at": now_iso(),
        }
        return await self.repo.insert(doc)

    async def clock_out(self, token: str, ip_address: str = None) -> dict:
        await self._check_rate_limit(token, ip_address)
        employee = await self._employee_from_token(token)
        existing = await self.repo.find_open_session(employee["id"], employee["user_id"])
        if not existing:
            raise ValidationAppError("Nessun ingresso registrato da chiudere")

        clock_out_ts = now_iso()
        ok = await self.repo.update(existing["id"], employee["user_id"], {"clock_out": clock_out_ts})
        if not ok:
            raise NotFoundError("Sessione non trovata")
        existing["clock_out"] = clock_out_ts
        return existing

    # ---------- lato admin (scheda dipendente) ----------

    async def _validate_employee(self, user_id: str, employee_id: str) -> dict:
        employee = await self.employees.find_one(employee_id, user_id)
        if not employee:
            raise ValidationAppError("Dipendente non valido")
        return employee

    async def list_sessions(self, user: dict, employee_id: str) -> list:
        await self._validate_employee(user["id"], employee_id)
        return await self.repo.find_many(employee_id, user["id"])

    async def create_manual_session(self, user: dict, employee_id: str, payload) -> dict:
        employee = await self._validate_employee(user["id"], employee_id)
        doc = {
            "id": gen_id(),
            "user_id": user["id"],
            "employee_id": employee_id,
            "employee_name": f"{employee['name']} {employee.get('surname', '')}".strip(),
            "clock_in": payload.clock_in,
            "clock_out": payload.clock_out,
            "note": (payload.note or "").strip(),
            "corrected_by_admin": True,
            "created_at": now_iso(),
        }
        return await self.repo.insert(doc)

    async def correct_session(self, user: dict, sid: str, payload) -> None:
        ok = await self.repo.update(sid, user["id"], {
            "clock_in": payload.clock_in,
            "clock_out": payload.clock_out,
            "note": (payload.note or "").strip(),
            "corrected_by_admin": True,
        })
        if not ok:
            raise NotFoundError("Sessione non trovata")

    async def delete_session(self, user: dict, sid: str) -> None:
        await self.repo.delete(sid, user["id"])


attendance_service = AttendanceService()

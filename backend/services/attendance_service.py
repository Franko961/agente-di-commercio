import secrets
from datetime import datetime

from fastapi import HTTPException

from core.utils import gen_id, now_iso, local_date_str
from core.exceptions import NotFoundError, ValidationAppError
from core.security import hash_reset_token, hash_password, verify_password, module_enabled
from core.rate_limit import check_and_record
from repositories.attendance_repository import attendance_repository
from repositories.employee_repository import employee_repository
from repositories.user_repository import user_repository


def _generate_kiosk_token() -> tuple:
    """Stesso schema di employee_service._generate_token: un token
    casuale (mai salvato in chiaro) più il suo hash, l'unico dato
    persistito — se il QR affisso all'ingresso viene smarrito/sostituito,
    se ne rigenera uno nuovo invalidando il precedente."""
    token = secrets.token_urlsafe(24)
    return token, hash_reset_token(token)


def _generate_pin() -> str:
    """PIN numerico a 4 cifre (incluso lo zero iniziale) per identificare
    il dipendente al chiosco — vedi il docstring di AttendanceService più
    sotto per il perché non punta a una sicurezza forte."""
    return f"{secrets.randbelow(10000):04d}"


class AttendanceService:
    """Rilevazione presenze v1: timbratura ingresso/uscita con timestamp
    lato server (now_iso(), il dipendente non può dichiarare un orario
    diverso da quello reale), tramite un chiosco pubblico raggiungibile
    da un QR code UGUALE per tutti i dipendenti, affisso fisicamente
    all'ingresso dell'azienda — non dal link personale di ciascuno, che
    permetterebbe di timbrare da qualunque posto.

    Deliberatamente SENZA geolocalizzazione: il tracciamento della
    posizione dei dipendenti in Italia ricade sotto l'art. 4 dello
    Statuto dei Lavoratori (Legge 300/1970) e richiede un accordo
    sindacale o l'autorizzazione dell'Ispettorato del Lavoro prima di
    poter essere attivato legalmente. Il QR fisico ottiene un effetto
    simile (bisogna essere fisicamente lì per scansionarlo) senza
    tracciare nulla: stesso principio di un cartellino/badge condiviso
    all'ingresso, non una prova crittografica di posizione (un QR
    fotografato potrebbe in teoria essere scansionato da altrove).

    Il PIN a 4 cifre per dipendente serve solo a evitare che un collega
    timbri al posto di un altro avendo accesso fisico al QR condiviso
    ("buddy punching") — non è pensato come credenziale di sicurezza
    forte (lo spazio di 10000 combinazioni non lo permetterebbe
    comunque), per questo il rate limit sui tentativi falliti (vedi
    _employee_from_kiosk) è la difesa che conta davvero contro un
    brute-force, non la sola hashing del PIN."""

    def __init__(self, repo=attendance_repository, employees=employee_repository, users=user_repository):
        self.repo = repo
        self.employees = employees
        self.users = users

    # ---------- QR aziendale (lato admin, account-level) ----------

    async def get_kiosk_token_status(self, user: dict) -> dict:
        return {"has_token": bool(user.get("attendance_kiosk_token_hash"))}

    async def regenerate_kiosk_token(self, user: dict) -> str:
        token, token_hash = _generate_kiosk_token()
        await self.users.update_by_id(user["id"], {"attendance_kiosk_token_hash": token_hash})
        return token

    # ---------- PIN dipendente (lato admin) ----------

    async def employee_has_pin(self, user: dict, employee_id: str) -> bool:
        employee = await self.employees.find_one_with_pin_hash(employee_id, user["id"])
        return bool(employee and employee.get("pin_hash"))

    async def set_employee_pin(self, user: dict, employee_id: str) -> str:
        employee = await self.employees.find_one(employee_id, user["id"])
        if not employee:
            raise ValidationAppError("Dipendente non valido")
        pin = _generate_pin()
        await self.employees.update(employee_id, user["id"], {"pin_hash": hash_password(pin)})
        return pin

    # ---------- chiosco pubblico ----------

    async def _owner_from_kiosk_token(self, token: str) -> dict:
        owner = await self.users.find_by_attendance_kiosk_token_hash(hash_reset_token(token))
        if not owner or not module_enabled(owner, "personale"):
            raise NotFoundError("QR non valido o temporaneamente non disponibile")
        return owner

    async def list_kiosk_employees(self, token: str) -> list:
        """Solo nome e stato attuale (in servizio o no) dei dipendenti
        attivi — niente altro dato personale: questa pagina è pubblica,
        raggiungibile da chiunque scansioni il QR fisico."""
        owner = await self._owner_from_kiosk_token(token)
        employees = await self.employees.find_many(owner["id"])
        result = []
        for e in employees:
            if not e.get("active", True):
                continue
            open_session = await self.repo.find_open_session(e["id"], owner["id"])
            result.append({
                "id": e["id"],
                "name": f"{e['name']} {e.get('surname', '')}".strip(),
                "clocked_in": open_session is not None,
            })
        return result

    async def _check_rate_limit(self, token: str, employee_id: str, ip_address: str = None) -> None:
        if ip_address:
            ok = await check_and_record("attendance_kiosk_ip", ip_address, max_attempts=60, window_minutes=60)
            if not ok:
                raise HTTPException(429, "Troppe richieste da questo indirizzo, riprova più tardi.")
        # Per token azienda (un QR condiviso riceve più traffico di un
        # link personale, soglia più alta) e per singolo dipendente (qui
        # sta anche il vero freno al brute-force del PIN a 4 cifre: 10
        # tentativi ogni 15 minuti rendono impraticabile provare le
        # 10000 combinazioni in tempi ragionevoli).
        token_ok = await check_and_record("attendance_kiosk_token", token, max_attempts=60, window_minutes=60)
        if not token_ok:
            raise HTTPException(429, "Troppe richieste per questo QR, riprova più tardi.")
        pin_ok = await check_and_record("attendance_pin_attempt", employee_id, max_attempts=10, window_minutes=15)
        if not pin_ok:
            raise HTTPException(429, "Troppi tentativi con PIN errato, riprova più tardi.")

    async def _employee_from_kiosk(self, token: str, employee_id: str, pin: str) -> dict:
        owner = await self._owner_from_kiosk_token(token)
        employee = await self.employees.find_one_with_pin_hash(employee_id, owner["id"])
        if not employee or not employee.get("active", True):
            raise NotFoundError("Dipendente non valido")
        if not employee.get("pin_hash") or not verify_password(pin, employee["pin_hash"]):
            raise ValidationAppError("PIN non corretto")
        return employee

    async def clock_in_kiosk(self, token: str, employee_id: str, pin: str, ip_address: str = None) -> dict:
        await self._check_rate_limit(token, employee_id, ip_address)
        employee = await self._employee_from_kiosk(token, employee_id, pin)
        existing = await self.repo.find_open_session(employee["id"], employee["user_id"])
        if existing:
            raise ValidationAppError("Sei già in servizio: registra prima l'uscita")

        doc = {
            "id": gen_id(),
            "user_id": employee["user_id"],
            "employee_id": employee["id"],
            "employee_name": f"{employee['name']} {employee.get('surname', '')}".strip(),
            "clock_in": now_iso(),
            "clock_out": None,
            "note": "",
            "corrected_by_admin": False,
            "created_at": now_iso(),
        }
        return await self.repo.insert(doc)

    async def clock_out_kiosk(self, token: str, employee_id: str, pin: str, ip_address: str = None) -> dict:
        await self._check_rate_limit(token, employee_id, ip_address)
        employee = await self._employee_from_kiosk(token, employee_id, pin)
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

    async def calendar(self, user: dict, month: str) -> list:
        """Ore lavorate per dipendente/giorno nel mese richiesto (AAAA-MM)
        — per la griglia di gruppo (Personale → Calendario), accanto alle
        assenze già mostrate da leave_request_service.calendar.

        Solo sessioni chiuse: una sessione ancora aperta non ha una durata
        definitiva da contare (comparirebbe comunque il giorno dopo la
        chiusura). L'intera durata viene attribuita al giorno solare
        italiano di clock_in (vedi local_date_str) anche per un turno che
        sconfina a cavallo di mezzanotte — semplificazione deliberata,
        stesso principio già scelto per il conteggio ferie a giorni di
        calendario in leave_request_service."""
        sessions = await self.repo.find_all_closed(user["id"])
        totals: dict = {}
        for s in sessions:
            day = local_date_str(s["clock_in"])
            if not day.startswith(month):
                continue
            hours = (datetime.fromisoformat(s["clock_out"]) - datetime.fromisoformat(s["clock_in"])).total_seconds() / 3600
            key = (s["employee_id"], day)
            totals[key] = totals.get(key, 0) + hours
        return [
            {"employee_id": employee_id, "date": date, "hours": round(hours, 2)}
            for (employee_id, date), hours in totals.items()
        ]

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

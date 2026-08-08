import secrets
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException

from core.utils import gen_id, now_iso, now_local, local_date_str, LOCAL_TZ
from core.exceptions import NotFoundError, ValidationAppError
from core.security import hash_reset_token, hash_password, verify_password, module_enabled
from core.rate_limit import check_and_record
from repositories.attendance_repository import attendance_repository
from repositories.employee_repository import employee_repository
from repositories.user_repository import user_repository
from repositories.leave_request_repository import leave_request_repository
from services.export_service import csv_response
from services.leave_request_service import LEAVE_TYPE_LABELS


def _local_time_str(iso_ts: str) -> str:
    """Come local_date_str (core.utils), ma restituisce solo l'orario
    'HH:MM' in ora italiana — usato dall'export CSV del cartellino, dove
    l'orologio a muro (non l'istante UTC salvato) è quello che interessa
    a chi elabora le buste paga."""
    dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(LOCAL_TZ).strftime("%H:%M")


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

    def __init__(self, repo=attendance_repository, employees=employee_repository, users=user_repository,
                 leave_requests=leave_request_repository):
        self.repo = repo
        self.employees = employees
        self.users = users
        self.leave_requests = leave_requests

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
        # IP e token azienda: 300/ora, non 60 — un solo tablet fisico
        # all'ingresso genera TUTTO il traffico di un'azienda con più
        # dipendenti da un'unica IP e con un unico QR, quindi entrambi i
        # limiti si sommano sullo stesso dispositivo. Un'azienda con 40
        # dipendenti fa già 80 timbrature (40 ingressi + 40 uscite) più le
        # correzioni e i ricaricamenti dell'elenco nella stessa ora: un
        # tetto di 60 sarebbe scattato per uso legittimo, non per abuso.
        # Il vero freno al brute-force resta il limite per singolo
        # dipendente sotto: 10 tentativi ogni 15 minuti rendono
        # impraticabile provare le 10000 combinazioni del PIN a 4 cifre in
        # tempi ragionevoli, indipendentemente da quanto sono larghi i
        # limiti IP/token.
        if ip_address:
            ok = await check_and_record("attendance_kiosk_ip", ip_address, max_attempts=300, window_minutes=60)
            if not ok:
                raise HTTPException(429, "Troppe richieste da questo indirizzo, riprova più tardi.")
        token_ok = await check_and_record("attendance_kiosk_token", token, max_attempts=300, window_minutes=60)
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
        ok = await self.repo.update(existing["id"], employee["user_id"], employee["id"], {"clock_out": clock_out_ts})
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

    async def expected_hours(self, user: dict, month: str) -> list:
        """Ore ATTESE per dipendente/giorno nel mese richiesto (AAAA-MM),
        calcolate dall'orario contrattuale (work_days/shift_start_time/
        shift_end_time sulla scheda dipendente) — per il confronto con le
        ore REALI timbrate (calendar() sopra) nella griglia di gruppo.

        Solo i dipendenti con tutti e tre i campi impostati vengono
        inclusi: shift_end_time resta facoltativo su models.employee
        apposta (per non rompere chi ha configurato solo l'avviso di
        timbratura mancante), quindi qui semplicemente si salta chi non
        l'ha ancora compilato — nessuna riga, non un valore a zero, per
        distinguere "non configurato" da "zero ore attese". Un dipendente
        sospeso/cessato (o disattivato) non ha ore attese, stesso criterio
        già usato da automation_engine._eval_attendance_missing e
        today_summary — altrimenti la griglia mostrerebbe uno scostamento
        per qualcuno che non dovrebbe più lavorare.

        I giorni coperti da un'assenza APPROVATA (ferie/permesso/malattia)
        non generano ore attese: nella griglia l'effetto era già invisibile
        (la cella colorata dell'assenza sovrascrive il confronto reale/
        atteso), ma il dato restava semanticamente sbagliato — "erano
        previste ore di lavoro" quando in realtà il dipendente era
        autorizzato ad assentarsi. Rilevante per qualunque uso futuro di
        questo numero fuori dalla griglia (es. un totale mensile
        aggregato)."""
        employees = await self.employees.find_many(user["id"])
        year, mon = (int(p) for p in month.split("-"))
        days_in_month = monthrange(year, mon)[1]

        date_from = f"{month}-01"
        date_to_bound = f"{month}-31"  # confronto testuale ISO, stesso principio di leave_request_service.calendar
        leave_requests = await self.leave_requests.find_overlapping(user["id"], date_from, date_to_bound, status="approvata")
        absences_by_employee: dict = {}
        for r in leave_requests:
            absences_by_employee.setdefault(r["employee_id"], []).append((r["date_from"], r["date_to"]))

        def _is_absent(employee_id: str, day_iso: str) -> bool:
            return any(df <= day_iso <= dt for df, dt in absences_by_employee.get(employee_id, []))

        out = []
        for e in employees:
            if not e.get("active", True) or e.get("employment_status") != "attivo":
                continue
            work_days = e.get("work_days")
            start = e.get("shift_start_time")
            end = e.get("shift_end_time")
            if not work_days or not start or not end:
                continue
            start_h, start_m = (int(p) for p in start.split(":"))
            end_h, end_m = (int(p) for p in end.split(":"))
            # unpaid_break_minutes (es. pausa pranzo) sottratta dalla durata
            # del turno: senza, 09:00-18:00 risulterebbe 9 ore attese invece
            # di 8 con un'ora di pausa non retribuita (vedi models.employee).
            break_minutes = e.get("unpaid_break_minutes") or 0
            shift_hours = round((end_h * 60 + end_m - start_h * 60 - start_m - break_minutes) / 60, 2)
            for day in range(1, days_in_month + 1):
                if date(year, mon, day).weekday() not in work_days:
                    continue
                day_iso = f"{month}-{day:02d}"
                if _is_absent(e["id"], day_iso):
                    continue
                out.append({"employee_id": e["id"], "date": day_iso, "hours": shift_hours})
        return out

    async def today_summary(self, user: dict) -> dict:
        """Riepilogo timbrature di oggi per il widget 'Presenze oggi' della
        Dashboard: quanti dipendenti attivi erano attesi in turno oggi
        (stesso criterio del trigger attendance_missing — orario
        contrattuale configurato + oggi è un giorno lavorativo per loro) e
        quanti hanno già timbrato. expected_today resta 0 se nessun
        dipendente ha un orario configurato o oggi non è lavorativo per
        nessuno (es. weekend): il widget lo interpreta come 'nessuno in
        turno oggi', non come un problema.

        clocked_today è calcolato con UNA query sola su tutti i dipendenti
        (find_clocked_in_between), non un find_many() per dipendente: con
        poche decine è irrilevante, ma con centinaia diventerebbe una
        classica N+1 — oltre a scaricare l'intera cronologia di ciascun
        dipendente (find_many non ha un filtro data) solo per sapere se
        almeno una sessione ricade in oggi."""
        now = now_local()
        weekday = now.weekday()
        today_midnight_local = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_start = today_midnight_local.astimezone(timezone.utc).isoformat()
        tomorrow_start = (today_midnight_local + timedelta(days=1)).astimezone(timezone.utc).isoformat()

        employees = await self.employees.find_many(user["id"])
        clocked_employee_ids = set(await self.repo.find_clocked_in_between(user["id"], today_start, tomorrow_start))

        total_active = 0
        expected_today = 0
        clocked_today = 0
        for e in employees:
            if not e.get("active", True) or e.get("employment_status") != "attivo":
                continue
            total_active += 1
            work_days = e.get("work_days")
            shift_start = e.get("shift_start_time")
            if not (work_days and shift_start and weekday in work_days):
                continue
            expected_today += 1
            if e["id"] in clocked_employee_ids:
                clocked_today += 1
        return {"total_active": total_active, "expected_today": expected_today, "clocked_today": clocked_today}

    async def export_csv(self, user: dict, month: str):
        """Cartellino del mese richiesto (AAAA-MM): una riga per ogni
        timbratura chiusa (tipo "presenza") più una riga per ogni assenza
        APPROVATA che si sovrappone al mese (ferie/permesso/malattia) —
        quello che serve a un consulente del lavoro per elaborare le buste
        paga, in un unico file invece di dover incrociare due esportazioni
        separate. Stesso rate limit di leave_request_service.export_csv
        (bucket condiviso "csv_export": un limite complessivo di export al
        minuto per utente ha più senso di uno per singolo tipo di file)."""
        ok = await check_and_record("csv_export", user["id"], max_attempts=20, window_minutes=10)
        if not ok:
            raise HTTPException(429, "Troppe esportazioni richieste, riprova tra qualche minuto")

        rows = []
        sessions = await self.repo.find_all_closed(user["id"])
        for s in sessions:
            day = local_date_str(s["clock_in"])
            if not day.startswith(month):
                continue
            hours = (datetime.fromisoformat(s["clock_out"]) - datetime.fromisoformat(s["clock_in"])).total_seconds() / 3600
            rows.append({
                "employee_name": s.get("employee_name", ""),
                "type": "Presenza",
                "date": day,
                "date_to": "",
                "clock_in": _local_time_str(s["clock_in"]),
                "clock_out": _local_time_str(s["clock_out"]),
                "hours": round(hours, 2),
                "note": s.get("note", ""),
            })

        year, mon = (int(p) for p in month.split("-"))
        month_start = f"{month}-01"
        month_end = f"{month}-{monthrange(year, mon)[1]:02d}"
        leave_requests = await self.leave_requests.find_overlapping(user["id"], month_start, month_end, status="approvata")
        for r in leave_requests:
            rows.append({
                "employee_name": r.get("employee_name", ""),
                "type": LEAVE_TYPE_LABELS.get(r["type"], r["type"]),
                # Solo la porzione che ricade nel mese esportato, non l'intervallo
                # originale della richiesta: un'assenza a cavallo tra due mesi (es.
                # 28 luglio - 5 agosto) in un cartellino di agosto deve mostrare
                # 1-5 agosto, non l'intero intervallo — altrimenti il totale giorni
                # per mese non tornerebbe con quello che il consulente si aspetta.
                "date": max(r["date_from"], month_start),
                "date_to": min(r["date_to"], month_end),
                "clock_in": "",
                "clock_out": "",
                "hours": r.get("hours") if r.get("hours") is not None else "",
                "note": r.get("note", ""),
            })

        rows.sort(key=lambda r: (r["employee_name"], r["date"]))
        headers = ["employee_name", "type", "date", "date_to", "clock_in", "clock_out", "hours", "note"]
        return csv_response(rows, headers, f"presenze_{month}.csv")

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

    async def correct_session(self, user: dict, employee_id: str, sid: str, payload) -> None:
        ok = await self.repo.update(sid, user["id"], employee_id, {
            "clock_in": payload.clock_in,
            "clock_out": payload.clock_out,
            "note": (payload.note or "").strip(),
            "corrected_by_admin": True,
        })
        if not ok:
            raise NotFoundError("Sessione non trovata")

    async def delete_session(self, user: dict, employee_id: str, sid: str) -> None:
        await self.repo.delete(sid, user["id"], employee_id)


attendance_service = AttendanceService()

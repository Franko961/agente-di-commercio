import html
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException

from core.utils import gen_id, now_iso, now_local
from core.exceptions import NotFoundError, ValidationAppError
from core.config import FRONTEND_URL
from core.rate_limit import check_and_record
from core.security import hash_reset_token, module_enabled
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

        # Oltre al limite per IP sopra, un limite per token: un link
        # rubato/condiviso per errore verrebbe altrimenti usato per
        # inviare richieste false da IP diversi (ognuno sotto la soglia
        # per-IP), generando storico fraudolento senza che nessun singolo
        # limite scatti.
        token_ok = await check_and_record("leave_request_token", payload.employee_token, max_attempts=5, window_minutes=60)
        if not token_ok:
            raise HTTPException(429, "Troppe richieste per questo link, riprova più tardi.")

        employee = await self.employees.find_by_token_hash(hash_reset_token(payload.employee_token))
        if not employee or not employee.get("active", True):
            raise NotFoundError("Link non valido")

        # Come in employee_service.get_by_token: questo endpoint pubblico
        # non passa da require_module (nessuna sessione autenticata da
        # cui ricavarlo), quindi deve verificare da sé che il
        # proprietario non abbia nel frattempo disattivato il modulo
        # Personale — altrimenti i vecchi link resterebbero utilizzabili
        # anche a modulo spento.
        owner = await self.users.find_by_id(employee["user_id"])
        if not owner or not module_enabled(owner, "personale"):
            raise NotFoundError("Link temporaneamente non disponibile")

        if payload.date_to < payload.date_from:
            raise ValidationAppError("La data di fine non può precedere quella di inizio")

        date_from_iso = payload.date_from.isoformat()
        date_to_iso = payload.date_to.isoformat()

        existing = await self.repo.find_by_employee(employee["id"])

        # Idempotenza per doppio clic / doppio invio: una richiesta
        # identica (stesso tipo e stesse date) già in attesa di decisione
        # viene considerata lo stesso invio, non un duplicato — non ne
        # viene creata una seconda né rimandata una seconda email al
        # responsabile. Non si applica a richieste già decise: se
        # approvata/rifiutata, un nuovo invio identico è una richiesta
        # legittima (es. ripresentata dopo un rifiuto) e passa invece dal
        # controllo di sovrapposizione sotto.
        if any(
            r["status"] == "in_attesa" and r["type"] == payload.type
            and r["date_from"] == date_from_iso and r["date_to"] == date_to_iso
            for r in existing
        ):
            return {"ok": True}

        # Sovrapposizione con altre richieste dello stesso dipendente non
        # rifiutate (in attesa o già approvate), di qualunque tipo — es.
        # ferie che si sovrappongono a una malattia già approvata. Non
        # blocca l'invio: il responsabile deve solo poterlo sapere prima
        # di decidere (vedi list_requests, che ricalcola questo stesso
        # controllo ad ogni lettura, così l'avviso resta aggiornato anche
        # se una delle richieste sovrapposte viene poi rifiutata).
        overlapping = [
            r for r in existing
            if r["status"] != "rifiutata"
            and r["date_from"] <= date_to_iso and r["date_to"] >= date_from_iso
        ]

        doc = {
            "id": gen_id(),
            "user_id": employee["user_id"],
            "employee_id": employee["id"],
            # Denormalizzato apposta: se il dipendente viene in seguito
            # eliminato, la richiesta resta leggibile nello storico invece
            # di mostrare un riferimento orfano.
            "employee_name": employee["name"],
            "type": payload.type,
            "date_from": date_from_iso,
            "date_to": date_to_iso,
            "note": (payload.note or "").strip(),
            "hours": payload.hours if payload.type == "permesso" else None,
            "certificate_received": None,
            "status": "in_attesa",
            "created_at": now_iso(),
            "decided_at": None,
        }
        await self.repo.insert(doc)

        if owner.get("email"):
            sent = await send_email(
                to=owner["email"],
                subject=f"Nuova richiesta di {LEAVE_TYPE_LABELS.get(payload.type, payload.type)} — {employee['name']}",
                html=self._manager_email_html(doc, overlapping=bool(overlapping)),
            )
            if not sent:
                logger.warning(
                    f"Invio email notifica nuova richiesta assenza fallito per {owner['email']} "
                    f"(richiesta {doc['id']}): la richiesta è comunque stata salvata."
                )

        return {"ok": True}

    async def list_requests(self, user: dict, status: str = None) -> list:
        requests = await self.repo.find_many(user["id"])
        self._attach_overlap_flags(requests)
        if status:
            requests = [r for r in requests if r["status"] == status]
        return requests

    @staticmethod
    def _attach_overlap_flags(requests: list) -> None:
        """Aggiunge a ciascuna richiesta non rifiutata un campo `overlaps`
        (bool): True se si sovrappone ad almeno un'altra richiesta non
        rifiutata dello stesso dipendente, di qualunque tipo. Calcolato al
        volo ad ogni lettura (non salvato sul documento) così resta
        corretto anche quando lo stato di una delle richieste coinvolte
        cambia in seguito."""
        by_employee = {}
        for r in requests:
            if r["status"] != "rifiutata":
                by_employee.setdefault(r["employee_id"], []).append(r)
        for r in requests:
            if r["status"] == "rifiutata":
                r["overlaps"] = False
                continue
            r["overlaps"] = any(
                o["id"] != r["id"] and o["date_from"] <= r["date_to"] and o["date_to"] >= r["date_from"]
                for o in by_employee.get(r["employee_id"], [])
            )

    async def decide(self, user: dict, rid: str, status: str) -> None:
        request = await self.repo.find_one(rid, user["id"])
        if not request:
            raise NotFoundError("Richiesta non trovata")
        if request["status"] != "in_attesa":
            raise ValidationAppError("Questa richiesta è già stata decisa")

        # Aggiornamento condizionale atomico (non un update incondizionato
        # dopo il controllo sopra): tra la lettura appena fatta e questo
        # punto un'altra decisione concorrente sulla STESSA richiesta può
        # essere già passata. Solo chi vince questa query invia l'email:
        # altrimenti due decisioni quasi simultanee (es. approva/rifiuta)
        # potrebbero entrambe leggere "in_attesa" e generare due email
        # contrastanti al dipendente.
        won_race = await self.repo.decide(rid, user["id"], {"status": status, "decided_at": now_iso()})
        if not won_race:
            raise ValidationAppError("Questa richiesta è già stata decisa")

        employee = await self.employees.find_one(request["employee_id"], user["id"])
        if employee and employee.get("email"):
            sent = await send_email(
                to=employee["email"],
                subject=f"La tua richiesta di {LEAVE_TYPE_LABELS.get(request['type'], request['type'])} è stata {status}",
                html=self._employee_email_html(request, status),
            )
            if not sent:
                logger.warning(
                    f"Invio email esito richiesta assenza fallito per {employee['email']} "
                    f"(richiesta {rid}): la decisione è comunque stata registrata."
                )

    async def set_certificate_received(self, user: dict, rid: str, received: bool) -> None:
        """Solo il responsabile la imposta (a differenza di 'note', che
        scrive il dipendente in fase di invio): conferma di aver ricevuto
        il certificato medico, nessun dato sanitario collegato."""
        request = await self.repo.find_one(rid, user["id"])
        if not request:
            raise NotFoundError("Richiesta non trovata")
        if request["type"] != "malattia":
            raise ValidationAppError("Il certificato riguarda solo le richieste di malattia")
        await self.repo.update(rid, user["id"], {"certificate_received": received})

    async def employee_summary(self, user: dict, employee: dict) -> dict:
        """Riepilogo Ferie/Permessi/Malattie/KPI per la scheda dipendente:
        tutto calcolato al volo dalle richieste esistenti (nessun dato
        duplicato/da tenere sincronizzato a mano). "Presenze" è una stima
        (giorni lavorativi trascorsi nell'anno meno le assenze approvate
        a giornata intera) perché SalesFly non traccia timbrature reali —
        non include "puntualità", che richiederebbe quel dato."""
        year = now_local().year
        requests = await self.repo.find_many(user["id"])
        mine = [r for r in requests if r["employee_id"] == employee["id"]]

        def _days(r) -> int:
            d1 = datetime.strptime(r["date_from"], "%Y-%m-%d").date()
            d2 = datetime.strptime(r["date_to"], "%Y-%m-%d").date()
            return (d2 - d1).days + 1

        def _in_year(r) -> bool:
            return r["date_from"][:4] == str(year)

        ferie_approvate = [r for r in mine if r["type"] == "ferie" and r["status"] == "approvata" and _in_year(r)]
        permessi_anno = [r for r in mine if r["type"] == "permesso" and _in_year(r)]
        permessi_approvati = [r for r in permessi_anno if r["status"] == "approvata"]
        malattie_approvate = [r for r in mine if r["type"] == "malattia" and r["status"] == "approvata" and _in_year(r)]

        ferie_godute = sum(_days(r) for r in ferie_approvate)
        spettanti = employee.get("annual_vacation_days", 26)
        malattia_giorni = sum(_days(r) for r in malattie_approvate)

        today_local = now_local().date()
        start_of_year = today_local.replace(month=1, day=1)
        giorni_lavorativi_trascorsi = sum(
            1 for i in range((today_local - start_of_year).days + 1)
            if (start_of_year + timedelta(days=i)).weekday() < 5
        )
        assenze_giorni = ferie_godute + malattia_giorni
        presenze_stimate = max(giorni_lavorativi_trascorsi - assenze_giorni, 0)

        return {
            "ferie": {
                "spettanti": spettanti,
                "godute": ferie_godute,
                "residue": round(spettanti - ferie_godute, 1),
            },
            "permessi": {
                "ore_richieste": sum(r.get("hours") or 0 for r in permessi_anno),
                "ore_approvate": sum(r.get("hours") or 0 for r in permessi_approvati),
            },
            "malattie": {
                "giorni": malattia_giorni,
                "richieste": [
                    {
                        "id": r["id"], "date_from": r["date_from"], "date_to": r["date_to"],
                        "giorni": _days(r), "status": r["status"],
                        "certificate_received": r.get("certificate_received"),
                    }
                    for r in mine if r["type"] == "malattia" and _in_year(r)
                ],
            },
            "kpi": {
                "presenze_stimate": presenze_stimate,
                "assenze_giorni": assenze_giorni,
                "ferie_giorni": ferie_godute,
                "permessi_ore": sum(r.get("hours") or 0 for r in permessi_approvati),
                "malattie_giorni": malattia_giorni,
            },
            "current_status": self._current_leave_status(mine, today_local),
        }

    @staticmethod
    def _current_leave_status(requests: list, today) -> Optional[str]:
        """'in_ferie'/'in_malattia' se una richiesta APPROVATA copre la
        data odierna, altrimenti None (lo stato mostrato in quel caso è
        quello impostato manualmente su employee.employment_status)."""
        today_iso = today.isoformat()
        for r in requests:
            if r["status"] == "approvata" and r["date_from"] <= today_iso <= r["date_to"]:
                if r["type"] == "malattia":
                    return "in_malattia"
                if r["type"] == "ferie":
                    return "in_ferie"
        return None

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
    def _manager_email_html(doc: dict, overlapping: bool = False) -> str:
        # employee_name e note arrivano in ultima analisi da un form pubblico
        # non autenticato (il nome è impostato dal manager stesso in fase di
        # creazione del dipendente, ma la nota la scrive il dipendente):
        # HTML-escaped per lo stesso motivo di contact_request_service.py.
        name = html.escape(doc["employee_name"])
        type_label = html.escape(LEAVE_TYPE_LABELS.get(doc["type"], doc["type"]))
        note = html.escape(doc["note"]) if doc["note"] else ""
        warning = (
            '<div style="margin-top:16px; padding:12px 16px; background:#FFF3EC; border:1px solid #FF5A00; '
            'border-radius:8px; font-size:13px; color:#0A192F;">'
            "⚠️ Esiste già un'altra richiesta di questo dipendente che si sovrappone al periodo selezionato."
            "</div>"
            if overlapping else ""
        )
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; color: #1a1a1a;">
          <h3 style="color:#0A192F;">Nuova richiesta di {type_label}</h3>
          <table style="width:100%; border-collapse: collapse; font-size: 14px;">
            <tr><td style="padding:4px 0; color:#52525B;">Dipendente</td><td><strong>{name}</strong></td></tr>
            <tr><td style="padding:4px 0; color:#52525B;">Dal</td><td>{doc['date_from']}</td></tr>
            <tr><td style="padding:4px 0; color:#52525B;">Al</td><td>{doc['date_to']}</td></tr>
          </table>
          {f'<div style="margin-top:16px; padding:12px 16px; background:#F9F9F8; border:1px solid #E4E4E1; border-radius:8px; font-size:14px; white-space:pre-wrap;">{note}</div>' if note else ''}
          {warning}
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

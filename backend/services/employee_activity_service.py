from core.exceptions import ValidationAppError
from repositories.employee_repository import employee_repository
from repositories.leave_request_repository import leave_request_repository
from repositories.employee_document_repository import employee_document_repository
from repositories.employee_equipment_repository import employee_equipment_repository
from repositories.employee_compensation_repository import employee_compensation_repository
from repositories.employee_disciplinary_action_repository import employee_disciplinary_action_repository

_LEAVE_TYPE_LABELS = {"ferie": "Ferie", "permesso": "Permesso", "malattia": "Malattia"}
_COMPENSATION_TYPE_LABELS = {"stipendio": "Stipendio", "bonus": "Bonus", "rimborso": "Rimborso", "altro": "Altro"}
_DISCIPLINARY_TYPE_LABELS = {
    "richiamo_verbale": "Richiamo verbale",
    "lettera_richiamo": "Lettera di richiamo",
    "contestazione_disciplinare": "Contestazione disciplinare",
    "sospensione": "Sospensione",
    "altro": "Altro",
}

# Numero massimo di eventi restituiti: una scheda dipendente non ha bisogno
# di uno storico infinito a scorrimento, i più vecchi restano comunque
# consultabili nelle rispettive tab (Assenze/Documenti/Dotazione/Compensi).
MAX_EVENTS = 100


class EmployeeActivityService:
    """Timeline SOLA LETTURA ricostruita al volo dai dati già esistenti
    (nessuna collection di log dedicata): copre le assenze inviate/decise,
    i documenti caricati, la dotazione assegnata/restituita e i compensi
    registrati. Non copre le modifiche all'anagrafica né la rigenerazione
    del link personale — SalesFly non conserva oggi una data per questi
    due eventi (models/employee.py non ha un campo updated_at, e
    regenerate_token non traccia quando avviene), quindi non c'è nulla da
    cui derivarli. Aggiungerli richiederebbe un log eventi esplicito,
    deliberatamente fuori scope per questa prima versione."""

    def __init__(
        self,
        employees=employee_repository,
        leave_requests=leave_request_repository,
        documents=employee_document_repository,
        equipment=employee_equipment_repository,
        compensation=employee_compensation_repository,
        disciplinary_actions=employee_disciplinary_action_repository,
    ):
        self.employees = employees
        self.leave_requests = leave_requests
        self.documents = documents
        self.equipment = equipment
        self.compensation = compensation
        self.disciplinary_actions = disciplinary_actions

    async def get_activity(self, user: dict, employee_id: str) -> list:
        if not await self.employees.find_one(employee_id, user["id"]):
            raise ValidationAppError("Dipendente non valido")

        events = []

        requests = [r for r in await self.leave_requests.find_by_employee(employee_id) if r["user_id"] == user["id"]]
        for r in requests:
            label = _LEAVE_TYPE_LABELS.get(r["type"], r["type"])
            events.append({
                "type": "assenza_inviata",
                "at": r["created_at"],
                "detail": f"{label} {r['date_from']} → {r['date_to']}",
            })
            if r.get("decided_at") and r["status"] in ("approvata", "rifiutata"):
                events.append({
                    "type": f"assenza_{r['status']}",
                    "at": r["decided_at"],
                    "detail": f"{label} {r['date_from']} → {r['date_to']}",
                })

        for d in await self.documents.find_many(employee_id, user["id"]):
            events.append({"type": "documento_caricato", "at": d["created_at"], "detail": d["name"]})

        for e in await self.equipment.find_many(employee_id, user["id"]):
            events.append({"type": "dotazione_aggiunta", "at": e["created_at"], "detail": e["name"]})
            if e["status"] == "restituito" and e.get("returned_date"):
                # "at" usa updated_at (timestamp ISO completo, come tutti gli
                # altri eventi), non returned_date: quest'ultima è solo una
                # data di calendario "AAAA-MM-DD" (la data di restituzione
                # scelta dall'utente, non il momento in cui è stata
                # registrata) — mischiarla con timestamp completi ordinava
                # comunque bene lessicograficamente al giorno, ma restava
                # un formato diverso dal resto della timeline. Il fallback a
                # created_at copre le dotazioni create prima di questo
                # campo (mai avuto un updated_at).
                events.append({
                    "type": "dotazione_restituita",
                    "at": e.get("updated_at") or e["created_at"],
                    "detail": e["name"],
                })

        for c in await self.compensation.find_many(employee_id, user["id"]):
            label = _COMPENSATION_TYPE_LABELS.get(c["type"], c["type"])
            events.append({
                "type": "compenso_registrato",
                "at": c["created_at"],
                # Solo il tipo, non l'importo: la formattazione valuta è una
                # responsabilità del frontend (vedi fmtEur in
                # EmployeeDetailSheet.jsx), non va duplicata qui lato
                # backend con una convenzione diversa (punto invece di
                # virgola decimale).
                "detail": label,
            })

        for a in await self.disciplinary_actions.find_many(employee_id, user["id"]):
            label = _DISCIPLINARY_TYPE_LABELS.get(a["type"], a["type"])
            events.append({
                "type": "contestazione_registrata",
                "at": a["created_at"],
                "detail": f"{label} — {a['subject']}",
            })

        events.sort(key=lambda e: e["at"], reverse=True)
        return events[:MAX_EVENTS]


employee_activity_service = EmployeeActivityService()

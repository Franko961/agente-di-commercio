from datetime import date
from pydantic import BaseModel, Field
from typing import Literal, Optional
from core.validation_limits import LONG_TEXT_MAX_LENGTH

LEAVE_TYPES = ("ferie", "permesso", "malattia")

# Tipi registrabili solo dal responsabile (non dal dipendente tramite link
# pubblico): a differenza di ferie/permesso/malattia non passano da una coda
# di approvazione, sono fatti che il responsabile registra direttamente
# (vedi LeaveRequestAdminIn e leave_request_service.create_by_admin).
ADMIN_LEAVE_TYPES = ("smartworking", "trasferta", "straordinari", "reperibilita")


class LeaveRequestIn(BaseModel):
    """Payload del form pubblico (nessun login, vedi routers/leave_requests.py):
    employee_token identifica sia il dipendente sia, indirettamente, l'azienda
    (ogni dipendente appartiene a un solo account SalesFly)."""
    employee_token: str
    type: Literal["ferie", "permesso", "malattia"]
    # date (non str): pydantic rifiuta automaticamente date inesistenti
    # (es. 2026-02-31) o formati non ISO, cosa che un confronto testuale
    # su stringhe non validate non intercetta.
    date_from: date
    date_to: date
    note: Optional[str] = Field("", max_length=LONG_TEXT_MAX_LENGTH)
    # Solo per type == "permesso": un permesso è tipicamente di poche ore
    # in un solo giorno, non un'assenza a giornata intera come ferie/
    # malattia — usato per il riepilogo "ore richieste/approvate" nella
    # tab Permessi. Ignorato per gli altri tipi.
    hours: Optional[float] = Field(None, gt=0, le=24)


class LeaveRequestAdminIn(BaseModel):
    """Registrazione diretta del responsabile (già approvata, nessuna
    email): niente employee_token, l'employee_id arriva dal path."""
    type: Literal[ADMIN_LEAVE_TYPES]
    date_from: date
    date_to: date
    note: Optional[str] = Field("", max_length=LONG_TEXT_MAX_LENGTH)
    hours: Optional[float] = Field(None, gt=0, le=24)


class LeaveRequestDecision(BaseModel):
    status: Literal["approvata", "rifiutata"]


class LeaveRequestCertificate(BaseModel):
    """Solo per type == 'malattia': conferma da parte del responsabile di
    aver ricevuto il certificato medico. Deliberatamente nessun dato
    sanitario (diagnosi, codice, ecc.) — solo un booleano."""
    certificate_received: bool

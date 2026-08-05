from datetime import date
from pydantic import BaseModel, Field
from typing import Literal, Optional
from core.validation_limits import LONG_TEXT_MAX_LENGTH

LEAVE_TYPES = ("ferie", "permesso", "malattia")


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


class LeaveRequestDecision(BaseModel):
    status: Literal["approvata", "rifiutata"]

from datetime import date
from pydantic import BaseModel, EmailStr, Field
from typing import Literal, Optional
from core.validation_limits import SHORT_TEXT_MAX_LENGTH, LONG_TEXT_MAX_LENGTH, PHOTO_MAX_LENGTH

EMPLOYMENT_STATUSES = ("attivo", "sospeso", "cessato")


class EmployeeIn(BaseModel):
    name: str = Field(max_length=SHORT_TEXT_MAX_LENGTH)
    # Campo nuovo, separato da "name" apposta: "name" esisteva già prima
    # (e resta il nome, non il nominativo completo) e continua a essere
    # quello denormalizzato su leave_request.employee_name — separarlo
    # ora avrebbe richiesto una migrazione dei dati già salvati.
    surname: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    role: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    department: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    mobile: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    birth_date: Optional[date] = None
    hire_date: Optional[date] = None
    # Stato HR impostato manualmente dal responsabile — distinto da
    # "active" (il flag tecnico che governa solo il link personale, vedi
    # employee_service): "in ferie"/"in malattia" non sono qui, vengono
    # calcolati al volo dalle richieste approvate che coprono la data
    # odierna (vedi leave_request_service.current_leave_status), così
    # non richiedono di essere aggiornati a mano e non vanno mai fuori
    # sincrono con le richieste reali.
    employment_status: Literal["attivo", "sospeso", "cessato"] = "attivo"
    address: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    city: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    zip_code: Optional[str] = Field("", max_length=20)
    province: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    notes: Optional[str] = Field("", max_length=LONG_TEXT_MAX_LENGTH)
    # Giorni di ferie spettanti nell'anno, configurabile per dipendente
    # (26 è lo standard più diffuso in Italia, ma non un obbligo di legge
    # uniforme): usato per calcolare "residue" nella tab Ferie.
    annual_vacation_days: float = Field(26, ge=0, le=365)
    # Data URL base64 (stessa forma già usata per la firma delle offerte,
    # vedi models/offer.py): niente storage a parte, va ridimensionata/
    # compressa lato client prima dell'invio.
    photo: Optional[str] = Field(None, max_length=PHOTO_MAX_LENGTH)


class EmployeeActiveUpdate(BaseModel):
    active: bool

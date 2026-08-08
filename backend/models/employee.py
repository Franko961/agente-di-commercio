from datetime import date
from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import List, Literal, Optional
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
    # Orario contrattuale: work_days/shift_start_time usati per segnalare una
    # timbratura mancante (vedi automation_engine._eval_attendance_missing),
    # entrambi opzionali ma legati — o impostati insieme o nessuno dei due.
    # Un dipendente senza questi campi non viene mai monitorato apposta:
    # introdurre la segnalazione non deve generare falsi allarmi retroattivi
    # sui dipendenti già esistenti, che non hanno mai avuto un orario da
    # rispettare finché non lo si imposta esplicitamente.
    #
    # shift_end_time è DISACCOPPIATO apposta dalla stessa regola "insieme o
    # niente": richiede shift_start_time (un orario di fine senza inizio non
    # ha senso) ma NON è obbligatorio quando si impostano work_days/
    # shift_start_time — altrimenti salvare una modifica qualsiasi su un
    # dipendente che ha già solo l'orario di inizio (impostato prima che
    # esistesse questo campo, per il solo avviso di timbratura mancante)
    # fallirebbe finché non si compila anche la fine turno, un requisito che
    # l'utente non ha chiesto di soddisfare in quel momento. Usato per il
    # confronto ore attese/ore reali nella griglia di gruppo (vedi
    # attendance_service.expected_hours): senza shift_end_time il confronto
    # semplicemente non viene mostrato per quel dipendente.
    work_days: Optional[List[int]] = None  # 0=lunedì … 6=domenica (date.weekday())
    shift_start_time: Optional[str] = Field(None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    shift_end_time: Optional[str] = Field(None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")

    @model_validator(mode="after")
    def _valida_orario_contrattuale(self):
        if (self.work_days is None) != (self.shift_start_time is None):
            raise ValueError("Giorni lavorativi e orario di inizio turno vanno impostati insieme")
        if self.work_days is not None:
            if not self.work_days:
                raise ValueError("Seleziona almeno un giorno lavorativo")
            if any(d < 0 or d > 6 for d in self.work_days):
                raise ValueError("Giorno lavorativo non valido")
        if self.shift_end_time is not None:
            if self.shift_start_time is None:
                raise ValueError("L'orario di fine turno richiede anche l'orario di inizio turno")
            if self.shift_end_time <= self.shift_start_time:
                raise ValueError("L'orario di fine turno deve essere successivo a quello di inizio")
        return self


class EmployeeActiveUpdate(BaseModel):
    active: bool

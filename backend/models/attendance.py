from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from core.validation_limits import LONG_TEXT_MAX_LENGTH


class AttendanceKioskClockIn(BaseModel):
    """Payload del chiosco pubblico (QR uguale per tutti i dipendenti,
    affisso all'ingresso — vedi routers/attendance.py): il token nell'URL
    identifica l'azienda, employee_id + pin identificano CHI sta
    timbrando (scelto da un elenco, non digitato a mano) — il PIN serve
    a evitare che un collega timbri al posto di un altro avendo solo
    accesso fisico al QR."""

    employee_id: str
    pin: str = Field(pattern=r"^\d{4}$")


class AttendanceCorrectionIn(BaseModel):
    """Creazione/modifica manuale di una sessione presenze da parte del
    responsabile (vedi routers/attendance.py) — a differenza della
    timbratura del dipendente (attendance_service.clock_in/clock_out, che
    scrive sempre now_iso() lato server), qui l'orario è dichiarato a
    posteriori, quindi la sessione viene marcata corrected_by_admin.

    clock_in/clock_out sono stringhe ISO UTC già convertite lato frontend
    da un <input type="datetime-local"> (stesso pattern di
    AppointmentIn.start/end in models/appointment.py), non oggetti
    datetime: evita una doppia conversione di fuso orario tra pydantic e
    il valore già prodotto da `new Date(...).toISOString()` in JS."""

    clock_in: str
    clock_out: Optional[str] = None
    note: Optional[str] = Field("", max_length=LONG_TEXT_MAX_LENGTH)

    @model_validator(mode="after")
    def _valida_intervallo(self):
        # clock_in va validato SEMPRE, anche per una sessione ancora
        # aperta (clock_out assente): un valore non parsabile qui
        # (es. digitato/manomesso a mano) passerebbe altrimenti
        # indisturbato finché quella sessione resta aperta, per poi
        # rompere silenziosamente calendario/export/calcolo ore nel
        # momento in cui viene chiusa o letta altrove.
        try:
            ci = datetime.fromisoformat(self.clock_in.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            raise ValueError("Formato data/ora di ingresso non valido")
        if not self.clock_out:
            return self
        try:
            co = datetime.fromisoformat(self.clock_out.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            raise ValueError("Formato data/ora di uscita non valido")
        if co <= ci:
            raise ValueError("L'uscita deve essere successiva all'ingresso")
        return self

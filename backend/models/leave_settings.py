from pydantic import BaseModel
from typing import Literal

FERIE_COUNT_MODES = ("calendario", "lavorativi")


class LeaveSettingsIn(BaseModel):
    """Come contare i giorni di ferie godute/residue nel riepilogo della
    scheda dipendente (leave_request_service.employee_summary): "calendario"
    conta ogni giorno dell'intervallo (comportamento storico), "lavorativi"
    conta solo lun-ven — non esclude le festività infrasettimanali italiane,
    scelta deliberata per restare semplice. Si applica solo alle Ferie, non
    alle Malattie (quelle restano sempre a giorni di calendario, come da
    prassi INPS/certificati medici)."""
    ferie_count_mode: Literal["calendario", "lavorativi"] = "calendario"

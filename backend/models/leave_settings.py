from typing import Literal

from pydantic import BaseModel

FERIE_COUNT_MODES = ("calendario", "lavorativi", "festivita")


class LeaveSettingsIn(BaseModel):
    """Come contare i giorni di ferie godute/residue nel riepilogo della
    scheda dipendente (leave_request_service.employee_summary): "calendario"
    conta ogni giorno dell'intervallo (comportamento storico), "lavorativi"
    conta solo lun-ven — non esclude le festività infrasettimanali italiane,
    scelta deliberata per restare semplice — "festivita" conta lun-sab
    escludendo solo domenica e le festività nazionali italiane (vedi
    core.italian_holidays), per chi lavora anche il sabato ma vuole comunque
    escludere Natale/Ferragosto/ecc. Si applica solo alle Ferie, non alle
    Malattie (quelle restano sempre a giorni di calendario, come da prassi
    INPS/certificati medici)."""

    ferie_count_mode: Literal["calendario", "lavorativi", "festivita"] = "calendario"

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from core.validation_limits import LONG_TEXT_MAX_LENGTH, SHORT_TEXT_MAX_LENGTH

DISCIPLINARY_ACTION_TYPES = (
    "richiamo_verbale",
    "lettera_richiamo",
    "contestazione_disciplinare",
    "sospensione",
    "altro",
)
DISCIPLINARY_ACTION_OUTCOMES = (
    "in_attesa",
    "archiviata",
    "accolta",
    "sanzione_confermata",
    "altro",
)


class EmployeeDisciplinaryActionIn(BaseModel):
    type: Literal[DISCIPLINARY_ACTION_TYPES]
    subject: str = Field(max_length=SHORT_TEXT_MAX_LENGTH)
    description: Optional[str] = Field("", max_length=LONG_TEXT_MAX_LENGTH)
    event_date: Optional[date] = None
    # Unico campo data obbligatorio: è il fulcro del record (senza una data
    # di contestazione non c'è un provvedimento da tracciare), le altre
    # date del percorso disciplinare vengono compilate mano a mano che il
    # procedimento avanza.
    contestation_date: date
    received_date: Optional[date] = None
    justification_deadline: Optional[date] = None
    justification_submitted: bool = False
    justification_date: Optional[date] = None
    outcome: Literal[DISCIPLINARY_ACTION_OUTCOMES] = "in_attesa"
    sanction: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    notes: Optional[str] = Field("", max_length=LONG_TEXT_MAX_LENGTH)
    # Id del documento caricato tramite l'upload già esistente per i
    # documenti dipendente (vedi employee_document_service.upload_document,
    # categoria "contestazione_disciplinare") — nessuna pipeline di storage
    # duplicata, solo un riferimento.
    document_id: Optional[str] = None

    @model_validator(mode="after")
    def _valida_coerenza_giustificazioni(self):
        """Stesso principio già usato in EmployeeEquipmentIn per uno stato
        incoerente con le date: se le giustificazioni non risultano
        presentate, una data di presentazione residua (es. dopo aver
        deselezionato la spunta senza svuotare il campo) viene azzerata
        invece di rifiutata — non c'è ambiguità su cosa intendesse
        l'utente."""
        if not self.justification_submitted:
            self.justification_date = None
        return self

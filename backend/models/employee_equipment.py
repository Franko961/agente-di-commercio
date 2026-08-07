from datetime import date
from pydantic import BaseModel, Field, model_validator
from typing import Literal, Optional
from core.validation_limits import SHORT_TEXT_MAX_LENGTH, LONG_TEXT_MAX_LENGTH

EQUIPMENT_STATUSES = ("consegnato", "restituito")


class EmployeeEquipmentIn(BaseModel):
    name: str = Field(max_length=SHORT_TEXT_MAX_LENGTH)  # es. "Divisa taglia L", "DPI casco", "Telefono aziendale"
    delivered_date: Optional[date] = None
    returned_date: Optional[date] = None
    status: Literal["consegnato", "restituito"] = "consegnato"
    notes: Optional[str] = Field("", max_length=LONG_TEXT_MAX_LENGTH)

    @model_validator(mode="after")
    def _valida_coerenza_stato_date(self):
        """Impedisce le combinazioni incoerenti tra stato e date:
        - "restituito" senza returned_date: non si saprebbe QUANDO è stata
          resa, un dato che l'utente ha comunque dichiarato di conoscere
          scegliendo quello stato.
        - returned_date precedente a delivered_date: impossibile restituire
          qualcosa prima di averlo ricevuto.
        - "consegnato" con un returned_date residuo (es. la stessa dotazione
          viene rimessa in consegna dopo essere stata segnata restituita, ma
          il campo data non viene svuotato a mano): qui viene azzerato
          invece di rifiutato, perché è un refuso facile — il form non
          nasconde/disabilita il campo in base allo stato — e non c'è
          ambiguità su cosa intendesse l'utente."""
        if self.status == "consegnato":
            self.returned_date = None
            return self
        if self.status == "restituito" and not self.returned_date:
            raise ValueError('La data di restituzione è obbligatoria quando lo stato è "restituito"')
        if self.delivered_date and self.returned_date and self.returned_date < self.delivered_date:
            raise ValueError("La data di restituzione non può essere precedente alla data di consegna")
        return self

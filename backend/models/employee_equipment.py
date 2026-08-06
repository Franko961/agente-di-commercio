from datetime import date
from pydantic import BaseModel, Field
from typing import Literal, Optional
from core.validation_limits import SHORT_TEXT_MAX_LENGTH, LONG_TEXT_MAX_LENGTH

EQUIPMENT_STATUSES = ("consegnato", "restituito")


class EmployeeEquipmentIn(BaseModel):
    name: str = Field(max_length=SHORT_TEXT_MAX_LENGTH)  # es. "Divisa taglia L", "DPI casco", "Telefono aziendale"
    delivered_date: Optional[date] = None
    returned_date: Optional[date] = None
    status: Literal["consegnato", "restituito"] = "consegnato"
    notes: Optional[str] = Field("", max_length=LONG_TEXT_MAX_LENGTH)

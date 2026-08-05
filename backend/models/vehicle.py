from datetime import date
from pydantic import BaseModel, Field
from typing import Literal, Optional
from core.validation_limits import SHORT_TEXT_MAX_LENGTH, LONG_TEXT_MAX_LENGTH, MAX_EXPENSE_AMOUNT

VEHICLE_TYPES = ("furgone", "camion", "auto", "altro")
DEADLINE_TYPES = ("assicurazione", "revisione", "bollo", "altro")
COST_CATEGORIES = ("carburante", "manutenzione", "riparazione", "altro")


class VehicleIn(BaseModel):
    plate: str = Field(max_length=20)
    model: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    type: Literal["furgone", "camion", "auto", "altro"] = "furgone"
    assigned_driver: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    notes: Optional[str] = Field("", max_length=LONG_TEXT_MAX_LENGTH)


class VehicleActiveUpdate(BaseModel):
    active: bool


class VehicleDeadlineIn(BaseModel):
    vehicle_id: str
    type: Literal["assicurazione", "revisione", "bollo", "altro"]
    due_date: date
    note: Optional[str] = Field("", max_length=LONG_TEXT_MAX_LENGTH)


class VehicleCostIn(BaseModel):
    vehicle_id: str
    category: Literal["carburante", "manutenzione", "riparazione", "altro"]
    amount: float = Field(gt=0, le=MAX_EXPENSE_AMOUNT)
    date: date
    description: Optional[str] = Field("", max_length=LONG_TEXT_MAX_LENGTH)


class CargoLoadIn(BaseModel):
    vehicle_id: str
    date: date
    description: str = Field(max_length=LONG_TEXT_MAX_LENGTH)
    destination: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    notes: Optional[str] = Field("", max_length=LONG_TEXT_MAX_LENGTH)

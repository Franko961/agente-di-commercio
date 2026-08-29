from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from core.validation_limits import (
    LONG_TEXT_MAX_LENGTH,
    MAX_EXPENSE_AMOUNT,
    MAX_QUANTITY,
    SHORT_TEXT_MAX_LENGTH,
)

VEHICLE_TYPES = ("furgone", "camion", "auto", "altro")
DEADLINE_TYPES = ("assicurazione", "revisione", "bollo", "altro")
COST_CATEGORIES = ("carburante", "manutenzione", "riparazione", "altro")
CARGO_STATUSES = ("programmato", "in_transito", "consegnato", "non_consegnato")


def normalize_plate(v: str) -> str:
    """Maiuscolo, senza spazi/trattini: 'ab 123-cd' e 'AB123CD' devono
    finire per essere la stessa targa, sia per il confronto anti-duplicati
    sia per la visualizzazione."""
    return "".join(v.split()).upper().replace("-", "")


class VehicleIn(BaseModel):
    plate: str = Field(max_length=20)
    model: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    type: Literal["furgone", "camion", "auto", "altro"] = "furgone"
    assigned_driver: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    notes: Optional[str] = Field("", max_length=LONG_TEXT_MAX_LENGTH)
    # Collegamento vero al modulo Personale (facoltativo: un account può
    # avere Flotta senza Personale, o viceversa) — usato dalla tab "Mezzo
    # assegnato" della scheda dipendente. assigned_driver sopra resta il
    # testo libero per chi non usa Personale.
    assigned_employee_id: Optional[str] = None
    current_km: Optional[float] = Field(None, ge=0, le=MAX_QUANTITY)

    @field_validator("plate")
    @classmethod
    def _normalizza_targa(cls, v):
        v = normalize_plate(v)
        if not v:
            raise ValueError("La targa non può essere vuota")
        return v


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
    # Tutti facoltativi apposta: un account con Clienti/Ordini disattivati
    # (es. CACI SRL) deve poter registrare comunque un carico senza questi
    # collegamenti, stesso principio di client_id in models/expense.py.
    client_id: Optional[str] = None
    order_id: Optional[str] = None
    quantity: Optional[float] = Field(None, gt=0, le=MAX_QUANTITY)
    colli: Optional[int] = Field(None, gt=0, le=MAX_QUANTITY)
    peso: Optional[float] = Field(None, gt=0, le=MAX_QUANTITY)  # kg
    status: Literal["programmato", "in_transito", "consegnato", "non_consegnato"] = (
        "programmato"
    )


class CargoLoadSign(BaseModel):
    signature: str  # base64 PNG data URL
    signer_name: str = Field(max_length=SHORT_TEXT_MAX_LENGTH)

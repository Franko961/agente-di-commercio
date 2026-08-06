from datetime import date
from pydantic import BaseModel, Field
from typing import Literal, Optional
from core.validation_limits import LONG_TEXT_MAX_LENGTH, MAX_EXPENSE_AMOUNT

COMPENSATION_TYPES = ("stipendio", "bonus", "rimborso", "altro")


class EmployeeCompensationIn(BaseModel):
    type: Literal["stipendio", "bonus", "rimborso", "altro"] = "stipendio"
    amount: float = Field(gt=0, le=MAX_EXPENSE_AMOUNT)
    date: date
    notes: Optional[str] = Field("", max_length=LONG_TEXT_MAX_LENGTH)

# noqa: F401 sotto -- serve per l'annotazione `date: date` più in basso; flake8
# la segnala come inutilizzata (falso positivo pyflakes per un campo con lo
# stesso nome del tipo importato), ma senza l'import Pydantic solleva
# "EmployeeCompensationIn is not fully defined".
from datetime import date  # noqa: F401
from typing import Literal, Optional

from pydantic import BaseModel, Field

from core.validation_limits import LONG_TEXT_MAX_LENGTH, MAX_EXPENSE_AMOUNT

COMPENSATION_TYPES = ("stipendio", "bonus", "rimborso", "altro")


class EmployeeCompensationIn(BaseModel):
    type: Literal["stipendio", "bonus", "rimborso", "altro"] = "stipendio"
    amount: float = Field(gt=0, le=MAX_EXPENSE_AMOUNT)
    date: date
    notes: Optional[str] = Field("", max_length=LONG_TEXT_MAX_LENGTH)

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from core.validation_limits import SHORT_TEXT_MAX_LENGTH


class EmployeeIn(BaseModel):
    name: str = Field(max_length=SHORT_TEXT_MAX_LENGTH)
    role: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    email: Optional[EmailStr] = None


class EmployeeActiveUpdate(BaseModel):
    active: bool

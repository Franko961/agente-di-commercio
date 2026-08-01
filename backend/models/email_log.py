from typing import Optional
from pydantic import BaseModel, Field
from core.validation_limits import SHORT_TEXT_MAX_LENGTH, LONG_TEXT_MAX_LENGTH


class EmailLogIn(BaseModel):
    to: str = Field(max_length=SHORT_TEXT_MAX_LENGTH)
    subject: str = Field(max_length=SHORT_TEXT_MAX_LENGTH)
    body: str = Field(max_length=LONG_TEXT_MAX_LENGTH)
    client_id: Optional[str] = None
    offer_id: Optional[str] = None

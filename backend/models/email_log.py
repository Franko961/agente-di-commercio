from typing import Optional
from pydantic import BaseModel


class EmailLogIn(BaseModel):
    to: str
    subject: str
    body: str
    client_id: Optional[str] = None
    offer_id: Optional[str] = None

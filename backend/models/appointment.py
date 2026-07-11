from pydantic import BaseModel
from typing import Optional

class AppointmentIn(BaseModel):
    client_id: Optional[str] = None
    title: str
    description: Optional[str] = ""
    start: str
    end: Optional[str] = None
    location: Optional[str] = ""
    status: str = "pianificato"

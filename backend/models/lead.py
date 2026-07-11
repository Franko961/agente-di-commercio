from pydantic import BaseModel
from typing import Optional

class LeadIn(BaseModel):
    company_name: str
    contact_name: Optional[str] = ""
    email: Optional[str] = ""
    phone: Optional[str] = ""
    source: Optional[str] = ""
    estimated_value: Optional[float] = 0.0
    status: str = "nuovo"
    notes: Optional[str] = ""

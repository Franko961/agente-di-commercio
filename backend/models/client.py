from pydantic import BaseModel
from typing import List, Optional

class ClientIn(BaseModel):
    company_name: str
    contact_name: Optional[str] = ""
    email: Optional[str] = ""
    phone: Optional[str] = ""
    vat_number: Optional[str] = ""
    address: Optional[str] = ""
    city: Optional[str] = ""
    province: Optional[str] = ""
    zone: Optional[str] = ""
    sector: Optional[str] = ""
    potential: Optional[str] = "medio"
    lat: Optional[float] = None
    lng: Optional[float] = None
    notes: Optional[str] = ""
    mandante_ids: List[str] = []

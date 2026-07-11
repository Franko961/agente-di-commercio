from pydantic import BaseModel
from typing import List, Optional


class DocumentIn(BaseModel):
    client_id: Optional[str] = None
    name: str
    category: str = "contratto"  # contratto, offerta, fattura, altro
    url: Optional[str] = ""
    notes: Optional[str] = ""
    tags: List[str] = []

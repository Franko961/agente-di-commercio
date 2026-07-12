from typing import Optional
from pydantic import BaseModel


class AIQuery(BaseModel):
    message: str
    context: Optional[str] = None

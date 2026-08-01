from pydantic import BaseModel, Field
from typing import Any, Dict


class AutomationIn(BaseModel):
    name: str
    trigger: str  # offer_expiring, no_visit_30d, lead_inactive
    action: str  # send_reminder, create_task, send_email
    enabled: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)

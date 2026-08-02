from typing import Optional
from pydantic import BaseModel, Field
from core.validation_limits import LONG_TEXT_MAX_LENGTH


class ImpersonateIn(BaseModel):
    """Payload di POST /admin/users/{uid}/impersonate. mode "view" (default)
    è sola lettura (vedi core.security.forbid_demo_write); "edit" consente
    la scrittura e richiede reason — vedi admin_service.impersonate_user."""
    mode: str = Field(default="view", pattern=r"^(view|edit)$")
    reason: Optional[str] = Field(default=None, max_length=LONG_TEXT_MAX_LENGTH)

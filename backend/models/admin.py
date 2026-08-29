from typing import Optional

from pydantic import BaseModel, Field

from core.validation_limits import LONG_TEXT_MAX_LENGTH

# Categoria rapida obbligatoria per OGNI accesso (sola lettura inclusa): una
# sola lettura non modifica nulla, ma per una tracciabilità rigorosa
# dell'audit log deve comunque dichiarare il motivo di massima dell'accesso,
# non solo chi/su chi/quando — senza dover scrivere un testo libero.
IMPERSONATION_CATEGORIES = (
    "assistenza_richiesta",
    "diagnosi_problema",
    "verifica_configurazione",
    "controllo_amministrativo",
)


class ImpersonateIn(BaseModel):
    """Payload di POST /admin/users/{uid}/impersonate. mode "view" (default)
    è sola lettura (vedi core.security.forbid_demo_write); "edit" consente
    la scrittura e richiede anche reason (testo libero) — vedi
    admin_service.impersonate_user. category è sempre obbligatoria, in
    entrambe le modalità."""

    mode: str = Field(default="view", pattern=r"^(view|edit)$")
    category: str = Field(pattern=r"^(" + "|".join(IMPERSONATION_CATEGORIES) + r")$")
    reason: Optional[str] = Field(default=None, max_length=LONG_TEXT_MAX_LENGTH)

from typing import Optional
from pydantic import BaseModel


class AIQuery(BaseModel):
    message: str
    context: Optional[str] = None
    # "chat" (testo digitato nella pagina Assistente AI) o "voice" (comando
    # trascritto dal riconoscimento vocale, sia dalla pagina assistente che
    # dal microfono globale). Usato solo per il registro azioni AI.
    channel: Optional[str] = "chat"

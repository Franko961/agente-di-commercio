from typing import Optional

from pydantic import BaseModel, Field

from core.validation_limits import LONG_TEXT_MAX_LENGTH


class AIQuery(BaseModel):
    # Il messaggio finisce direttamente nel contenuto inviato all'API
    # Anthropic (vedi services/ai_service.py): senza un limite, un messaggio
    # enorme gonfierebbe inutilmente il costo per token della chiamata,
    # oltre a rischiare di far sforare il contesto insieme alla cronologia
    # conversazione e ai dati CRM già inclusi nel prompt.
    message: str = Field(max_length=LONG_TEXT_MAX_LENGTH)
    context: Optional[str] = None
    # "chat" (testo digitato nella pagina Assistente AI) o "voice" (comando
    # trascritto dal riconoscimento vocale, sia dalla pagina assistente che
    # dal microfono globale). Usato solo per il registro azioni AI.
    channel: Optional[str] = "chat"


class AIExecuteActionIn(BaseModel):
    # log_id tipizzato come str (non un dict = Body(...) grezzo): senza
    # questo, un payload come {"log_id": {"$ne": null}} verrebbe passato
    # così com'è al filtro MongoDB ({"id": log_id, ...}), facendo
    # corrispondere QUALUNQUE azione in_attesa dell'utente invece di quella
    # specifica mostrata nella scheda di conferma.
    tool_name: str
    log_id: str
    resolved_input: Optional[dict] = None


class AICancelActionIn(BaseModel):
    log_id: str

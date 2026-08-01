from pydantic import BaseModel, Field
from core.validation_limits import MAX_MONETARY_TARGET


class ManualCommissionIn(BaseModel):
    """Provvigione inserita manualmente dall'utente per un mese, ad
    esempio per coprire un accordo concluso fuori dal flusso ordini del
    CRM. Un solo valore per (utente, mese): l'endpoint fa upsert, non
    aggiunge righe multiple per lo stesso periodo."""
    period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")  # "YYYY-MM"
    amount: float = Field(ge=0, le=MAX_MONETARY_TARGET)

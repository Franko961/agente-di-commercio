from typing import Optional

from pydantic import BaseModel, Field

from core.validation_limits import (
    LONG_TEXT_MAX_LENGTH,
    MAX_MONETARY_TARGET,
    SHORT_TEXT_MAX_LENGTH,
)


class ManualCommissionIn(BaseModel):
    """Provvigione inserita manualmente dall'utente per un mese, ad
    esempio per coprire un accordo concluso fuori dal flusso ordini del
    CRM. Più righe possono coesistere sullo stesso periodo (es. un premio
    per un mandante e una rettifica per un altro nello stesso mese):
    POST crea una nuova riga, PUT /manual/{id} aggiorna quella esistente —
    nessun vincolo di unicità su (utente, mese), l'id è l'unica chiave.
    mandante_id è opzionale: se assente, la provvigione non è attribuita a
    nessun mandante e va inclusa solo nella vista "Tutti i mandanti" (vedi
    Commissions.jsx), non nel totale di un mandante specifico. Stessa
    logica per client_id (fatturato/provvigioni del cliente in
    ClientDetail.jsx). stato/tipo riusano gli stessi valori delle
    provvigioni calcolate dagli ordini (vedi models Commission esistente),
    per restare comparabili quando le due liste vengono unite (vedi
    commission_service.get_effective_commissions)."""

    period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")  # "YYYY-MM"
    # gt=0, non ge=0: una provvigione manuale da 0€ non ha significato
    # operativo, e con il CRUD per id (POST/PUT/DELETE) l'eliminazione ha
    # già un'azione dedicata per riga — usare 0 come "elimina" sarebbe
    # ridondante oltre che ambiguo.
    amount: float = Field(gt=0, le=MAX_MONETARY_TARGET)
    mandante_id: Optional[str] = None
    client_id: Optional[str] = None
    descrizione: Optional[str] = Field(default=None, max_length=SHORT_TEXT_MAX_LENGTH)
    stato: str = Field(default="maturato", pattern=r"^(maturato|incassato)$")
    note: Optional[str] = Field(default=None, max_length=LONG_TEXT_MAX_LENGTH)
    tipo: str = Field(default="ordinaria", pattern=r"^(ordinaria|bonus|rettifica)$")

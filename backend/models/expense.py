from datetime import datetime
from pydantic import BaseModel, field_validator
from typing import Optional

# Categorie spesa suggerite (il frontend le usa per il menu a tendina, ma il campo
# è una stringa libera lato backend per non dover fare una migrazione se ne servono altre)
EXPENSE_CATEGORIES = [
    "carburante",
    "vitto",
    "alloggio",
    "pedaggio_parcheggio",
    "materiali",
    "inps",
    "enasarco",
    "assicurazione_auto",
    "commercialista",
    "altro",
]


class ExpenseIn(BaseModel):
    date: str  # ISO date (YYYY-MM-DD)
    category: str = "altro"
    description: Optional[str] = ""
    amount: float
    client_id: Optional[str] = None  # collegamento facoltativo a un cliente/visita
    notes: Optional[str] = ""
    receipt_document_id: Optional[str] = None  # id del documento (foto/PDF scontrino) caricato via /api/documents/upload

    # Stesse due validazioni già applicate al percorso di creazione spesa via
    # assistente AI (vedi services/ai_service._safe_float/_validate_expense_date),
    # che mancavano qui: senza queste, il form/API diretta permetteva importi
    # zero/negativi e date calendaristicamente inesistenti, alterando i totali
    # di spesa mostrati in dashboard/report.
    @field_validator("amount")
    @classmethod
    def _amount_deve_essere_positivo(cls, v):
        if v <= 0:
            raise ValueError("L'importo deve essere maggiore di zero")
        return v

    @field_validator("date")
    @classmethod
    def _data_deve_essere_valida(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except (TypeError, ValueError):
            raise ValueError("Data non valida: usa il formato AAAA-MM-DD")
        return v

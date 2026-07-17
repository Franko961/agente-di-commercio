from pydantic import BaseModel
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

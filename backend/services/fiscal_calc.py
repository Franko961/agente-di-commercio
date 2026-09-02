"""Calcolo di ritenuta d'acconto e contributo ENASARCO su una provvigione
lorda reale. Stessa identica logica (e stesse aliquote) del calcolatore
interattivo pubblicato nell'articolo del blog "ritenuta d'acconto e
contributi ENASARCO" (frontend/src/components/RitenutaEnasarcoCalculator.jsx
/ frontend/src/utils/fiscalCalc.js) — tenuta qui come funzione pura e
riusabile perché, a differenza di quel calcolatore (un numero inserito a
mano, isolato), qui si applica a dati reali già presenti nel sistema
(commission_service), quindi deve restare importabile da più punti
(endpoint di riepilogo, dashboard, export) senza duplicare la formula.

Riferimenti normativi (verificati per l'articolo del blog):
- Ritenuta d'acconto: art. 25-bis DPR 600/1973, aliquota nominale 23%,
  applicata su base 50% (ordinaria) o 20% (ridotta, richiede dichiarazione
  formale al mandante entro il 31/12 dell'anno precedente).
- Esenzione totale dalla ritenuta per il regime forfettario: L. 190/2014,
  comma 67.
- Contributo ENASARCO 2026: 17% totale, 8,5% a carico dell'agente,
  indipendente dal regime fiscale (forfettario incluso).
"""

from typing import Literal, TypedDict

RITENUTA_ALIQUOTA = 0.23
ENASARCO_QUOTA_AGENTE = 0.085


# Nota per chi collegherà questa funzione a un endpoint reale (vedi sopra,
# "importabile da più punti"): il gemello JS (frontend/src/utils/fiscalCalc.js
# computeFiscalBreakdown) restituisce le stesse quattro grandezze ma in
# camelCase (ritenutaAcconto, contributoEnasarco), per convenzione idiomatica
# di ciascun linguaggio — non è un disallineamento accidentale, ma un
# endpoint che esponga questo dict come JSON dovrà comunque tradurre le
# chiavi se il consumer si aspetta il formato camelCase già in uso lato
# frontend. Entrambe le implementazioni arrotondano ora a 2 decimali con lo
# stesso criterio, per restare numericamente identiche a parità di input.
class FiscalBreakdown(TypedDict):
    lordo: float
    ritenuta_acconto: float
    contributo_enasarco: float
    netto: float


def compute_fiscal_breakdown(
    lordo: float,
    regime_fiscale: Literal["ordinario", "forfettario"],
    base_ritenuta: Literal["50", "20"],
) -> FiscalBreakdown:
    lordo = max(0.0, lordo)
    base_imponibile = 0.0
    if regime_fiscale == "ordinario":
        base_imponibile = 0.5 if base_ritenuta == "50" else 0.2
    ritenuta = lordo * base_imponibile * RITENUTA_ALIQUOTA
    enasarco = lordo * ENASARCO_QUOTA_AGENTE
    return {
        "lordo": round(lordo, 2),
        "ritenuta_acconto": round(ritenuta, 2),
        "contributo_enasarco": round(enasarco, 2),
        "netto": round(lordo - ritenuta - enasarco, 2),
    }

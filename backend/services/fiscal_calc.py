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
  indipendente dal regime fiscale (forfettario incluso), calcolato su un
  imponibile con massimale/minimale annuo PER MANDANTE (non complessivo):
  30.478€/515€ plurimandatario, 45.717€/1.026€ monomandatario/esclusiva —
  vedi l'articolo blog sui minimali/massimali 2026 e il gemello JS
  (frontend/src/utils/fiscalCalc.js, ENASARCO_SOGLIE/
  computeEnasarcoConMassimale).
"""

from typing import Literal, TypedDict

RITENUTA_ALIQUOTA = 0.23
ENASARCO_QUOTA_AGENTE = 0.085

ENASARCO_SOGLIE = {
    "plurimandatario": {"massimale": 30478.0, "minimale": 515.0},
    "monomandatario": {"massimale": 45717.0, "minimale": 1026.0},
}


class EnasarcoConMassimale(TypedDict):
    imponibile: float
    contributo_enasarco: float
    supera_massimale: bool
    sotto_minimale: bool


def compute_enasarco_con_massimale(
    cumulato_prima: float, lordo_periodo: float, esclusiva: bool
) -> EnasarcoConMassimale:
    """Calcola il contributo ENASARCO su `lordo_periodo` tenendo conto di
    quanto già maturato con lo stesso mandante nell'anno prima di questo
    periodo (`cumulato_prima`): solo la parte di `lordo_periodo` che rientra
    ancora nel massimale annuo residuo è imponibile — il resto è esente. Vedi
    RitenutaEnasarcoCalculator.jsx (stesso concetto "cumulativo prima" nel
    calcolatore interattivo) per la logica gemella lato utente."""
    soglie = ENASARCO_SOGLIE["monomandatario" if esclusiva else "plurimandatario"]
    cumulato_prima = max(0.0, cumulato_prima)
    lordo_periodo = max(0.0, lordo_periodo)
    residuo = max(0.0, soglie["massimale"] - cumulato_prima)
    imponibile = min(lordo_periodo, residuo)
    cumulato_totale = cumulato_prima + lordo_periodo
    return {
        "imponibile": round(imponibile, 2),
        "contributo_enasarco": round(imponibile * ENASARCO_QUOTA_AGENTE, 2),
        "supera_massimale": cumulato_totale > soglie["massimale"],
        "sotto_minimale": cumulato_totale < soglie["minimale"],
    }


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

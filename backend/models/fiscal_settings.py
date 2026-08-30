from typing import Literal

from pydantic import BaseModel

# Default = quello che si applica per legge senza alcuna dichiarazione da
# parte dell'agente: regime ordinario (il forfettario è un'opzione da
# richiedere attivamente all'Agenzia delle Entrate) con base ritenuta al
# 50% (la base ridotta al 20% richiede una dichiarazione formale al
# mandante, vedi services/fiscal_calc.py) — non un default "conveniente",
# ma quello legalmente corretto finché l'utente non imposta la propria
# situazione reale.
REGIMI_FISCALI = ("ordinario", "forfettario")
BASI_RITENUTA = ("50", "20")


class FiscalSettingsIn(BaseModel):
    """Situazione fiscale dell'agente, usata per calcolare ritenuta
    d'acconto e contributo ENASARCO sulle provvigioni reali (vedi
    services/fiscal_calc.py per le aliquote e i riferimenti normativi —
    stessa logica del calcolatore nell'articolo del blog "ritenuta
    d'acconto e contributi ENASARCO"). base_ritenuta è ignorato quando
    regime_fiscale è "forfettario" (nessuna ritenuta in quel caso)."""

    regime_fiscale: Literal["ordinario", "forfettario"] = "ordinario"
    base_ritenuta: Literal["50", "20"] = "50"

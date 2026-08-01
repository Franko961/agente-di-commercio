from pydantic import BaseModel, Field
from typing import List, Optional

# Oltre questo numero di tappe la matrice distanze (O(n^2) chiamate/celle) e
# il miglioramento 2-opt (O(n^3) per iterazione) diventano troppo pesanti per
# un singolo giro giornaliero — un agente reale non visita comunque così tanti
# clienti in un giorno, questo è solo un tetto di sicurezza per il backend e
# per la quota gratuita di OpenRouteService.
MAX_ROUTE_CLIENTS = 50

# "first_client": il primo cliente della lista resta il punto di partenza
# (comportamento storico, per compatibilità). Le altre modalità richiedono
# (per current_location/custom) o risolvono da sole (per home/office) una
# coordinata di partenza che NON è una delle tappe da visitare.
START_MODES = {"first_client", "current_location", "home", "office", "custom"}


class RoutePlanIn(BaseModel):
    client_ids: List[str] = Field(..., min_length=1, max_length=MAX_ROUTE_CLIENTS)
    start_time: str = "09:00"  # formato HH:MM, ora locale dell'agente
    # Prima senza alcun limite, nemmeno inferiore: un valore <= 0 avrebbe
    # reso insensato il calcolo degli orari proposti (visite sovrapposte o
    # a ritroso), uno enorme (o negativo con moltiplicatore MAX_ROUTE_CLIENTS)
    # avrebbe prodotto orari assurdi per l'intero giro.
    visit_minutes: int = Field(30, ge=1, le=480)  # durata assunta per ogni visita (max 8 ore), usata per calcolare gli orari proposti
    start_mode: str = "first_client"  # first_client | current_location | home | office | custom
    start_lat: Optional[float] = None  # richiesto per current_location/custom
    start_lng: Optional[float] = None  # richiesto per current_location/custom
    round_trip: bool = False  # se True, il giro include il ritorno al punto di partenza

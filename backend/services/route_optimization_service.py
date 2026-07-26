"""
Ottimizzazione del giro visita: dato un elenco di clienti (già geolocalizzati)
da visitare in una giornata, calcola l'ordine di visita che minimizza
chilometri/tempo di percorrenza e propone una schedulazione oraria.

Cosa fa, in breve:
  1. recupera lat/lng dei clienti richiesti;
  2. calcola una matrice di distanze/tempi reali tra tutti loro tramite
     OpenRouteService (se ORS_API_KEY è configurata), altrimenti stima in
     linea d'aria (haversine) con una velocità media assunta;
  3. ordina le tappe con un euristica nearest-neighbor + miglioramento
     2-opt (il punto di partenza — il primo cliente della lista ricevuta —
     resta fisso, il resto viene riordinato per minimizzare il percorso);
  4. propone orari di arrivo/partenza per ogni tappa, sommando tempi di
     viaggio e una durata di visita fissa per cliente.

Non è un solutore esatto del problema del commesso viaggiatore (NP-difficile
in generale): per il numero di visite di una giornata reale (tipicamente
sotto le 20-30 tappe) nearest-neighbor + 2-opt dà risultati vicini
all'ottimo in tempo trascurabile, senza bisogno di librerie di ottimizzazione
pesanti (es. OR-Tools).
"""
import asyncio
import logging
import math
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import requests

from core.config import ORS_API_KEY
from core.exceptions import NotFoundError, ValidationAppError
from repositories.client_repository import client_repository

logger = logging.getLogger(__name__)

ORS_MATRIX_URL = "https://api.openrouteservice.org/v2/matrix/driving-car"

# Usata SOLO come fallback quando ORS non è configurato o non risponde: una
# stima prudente per un misto urbano/extraurbano italiano, non una velocità
# di percorrenza reale (che dipende da traffico, tipo di strada, ecc.).
_ASSUMED_AVG_SPEED_KMH = 35

DEFAULT_VISIT_MINUTES = 30
DEFAULT_START_TIME = "09:00"

# Tetto ai tentativi di miglioramento 2-opt: con le dimensioni tipiche di un
# giro giornaliero (poche decine di tappe al massimo) l'algoritmo converge
# ben prima, questo è solo un paracadute contro input anomali.
_MAX_TWO_OPT_ITERATIONS = 200

# Un giro visita giornaliero resta per natura in una zona limitata: una
# singola tratta oltre questa soglia è quasi certamente un sintomo di
# coordinate sbagliate per uno dei due clienti coinvolti (es. un indirizzo
# geocodificato su un omonimo dall'altra parte del mondo), non un genuino
# spostamento nella stessa giornata. Non blocca il calcolo — il giro viene
# comunque proposto — ma segnala chiaramente la tratta sospetta invece di
# presentarla come un dato affidabile.
_SUSPICIOUS_LEG_DISTANCE_KM = 300


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distanza in linea d'aria tra due coordinate, in km (formula
    dell'emisenoverso). Non tiene conto di strade reali: è la stima usata
    solo quando OpenRouteService non è disponibile."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _haversine_matrix(coords: List[Tuple[float, float]]) -> Tuple[list, list]:
    n = len(coords)
    distances_km = [[0.0] * n for _ in range(n)]
    durations_min = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            d = haversine_km(coords[i][0], coords[i][1], coords[j][0], coords[j][1])
            distances_km[i][j] = d
            durations_min[i][j] = d / _ASSUMED_AVG_SPEED_KMH * 60
    return distances_km, durations_min


async def _fetch_ors_matrix(coords: List[Tuple[float, float]]) -> Optional[Tuple[list, list]]:
    """Interroga la Matrix API di OpenRouteService per le distanze/tempi
    reali su strada tra tutte le coppie di coordinate. Ritorna None (invece
    di sollevare un'eccezione) se ORS non è configurato o la chiamata
    fallisce per qualunque motivo — il chiamante ricade sulla stima in linea
    d'aria, non deve mai far fallire la pianificazione del giro per un
    servizio esterno temporaneamente non disponibile."""
    if not ORS_API_KEY:
        return None

    def _call():
        body = {
            # ORS vuole le coordinate in ordine [longitudine, latitudine],
            # l'opposto della convenzione (lat, lng) usata nel resto
            # dell'applicazione (client.lat/client.lng, Leaflet, ecc.).
            "locations": [[lng, lat] for lat, lng in coords],
            "metrics": ["distance", "duration"],
        }
        resp = requests.post(
            ORS_MATRIX_URL,
            json=body,
            headers={"Authorization": ORS_API_KEY, "Content-Type": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    try:
        data = await asyncio.to_thread(_call)
    except requests.RequestException as e:
        logger.warning(f"OpenRouteService non disponibile, uso stima in linea d'aria: {e}")
        return None

    distances_m = data.get("distances")
    durations_s = data.get("durations")
    if not distances_m or not durations_s:
        logger.warning("Risposta OpenRouteService senza distanze/durate valide, uso stima in linea d'aria")
        return None

    distances_km = [[(d or 0) / 1000 for d in row] for row in distances_m]
    durations_min = [[(d or 0) / 60 for d in row] for row in durations_s]
    return distances_km, durations_min


async def get_distance_duration_matrix(coords: List[Tuple[float, float]]) -> Tuple[list, list, bool]:
    """Ritorna (distanze_km, durate_min, usato_routing_reale). La terza
    componente indica se i valori vengono da OpenRouteService (True) o dalla
    stima in linea d'aria (False) — il chiamante la espone all'utente, che
    deve sapere se i tempi/km mostrati sono reali o solo indicativi."""
    result = await _fetch_ors_matrix(coords)
    if result:
        return result[0], result[1], True
    return (*_haversine_matrix(coords), False)


def _path_length(order: List[int], matrix: list) -> float:
    return sum(matrix[order[k]][order[k + 1]] for k in range(len(order) - 1))


def _nearest_neighbor_order(matrix: list, start: int = 0) -> List[int]:
    n = len(matrix)
    visited = [False] * n
    order = [start]
    visited[start] = True
    current = start
    for _ in range(n - 1):
        next_idx = min((j for j in range(n) if not visited[j]), key=lambda j: matrix[current][j])
        order.append(next_idx)
        visited[next_idx] = True
        current = next_idx
    return order


def _two_opt(order: List[int], matrix: list) -> List[int]:
    """Migliora l'ordine di partenza scambiando coppie di tappe finché il
    percorso totale non si accorcia più. La prima tappa (order[0], il primo
    cliente della lista ricevuta) resta sempre fissa in prima posizione: il
    ciclo su i parte da 1, non da 0, apposta per non spostarla mai."""
    order = list(order)
    n = len(order)
    if n < 4:
        return order  # con 3 o meno tappe non c'è margine di miglioramento reale
    improved = True
    iterations = 0
    while improved and iterations < _MAX_TWO_OPT_ITERATIONS:
        improved = False
        iterations += 1
        current_length = _path_length(order, matrix)
        for i in range(1, n - 1):
            for j in range(i + 1, n):
                candidate = order[:i] + order[i:j + 1][::-1] + order[j + 1:]
                candidate_length = _path_length(candidate, matrix)
                if candidate_length < current_length - 1e-9:
                    order = candidate
                    current_length = candidate_length
                    improved = True
    return order


class RouteOptimizationService:
    def __init__(self, client_repo=client_repository):
        self.client_repo = client_repo

    async def plan_day(
        self, user_id: str, client_ids: List[str],
        start_time: str = DEFAULT_START_TIME, visit_minutes: int = DEFAULT_VISIT_MINUTES,
    ) -> dict:
        if not client_ids:
            raise ValidationAppError("Seleziona almeno un cliente da visitare")

        all_clients = await self.client_repo.find_many(user_id, {})
        by_id = {c["id"]: c for c in all_clients}

        selected, missing_ids, no_coords = [], [], []
        for cid in client_ids:
            c = by_id.get(cid)
            if not c:
                missing_ids.append(cid)
            elif c.get("lat") is None or c.get("lng") is None:
                no_coords.append(c)
            else:
                selected.append(c)

        if missing_ids:
            raise NotFoundError(f"Cliente/i non trovato/i: {', '.join(missing_ids)}")
        if no_coords:
            names = ", ".join(c["company_name"] for c in no_coords)
            raise ValidationAppError(
                f"Questi clienti non hanno un indirizzo geolocalizzato, impossibile includerli nel giro: {names}"
            )

        try:
            current_time = datetime.strptime(start_time, "%H:%M")
        except (ValueError, TypeError):
            current_time = datetime.strptime(DEFAULT_START_TIME, "%H:%M")

        if len(selected) == 1:
            client = selected[0]
            departure = current_time + timedelta(minutes=visit_minutes)
            return {
                "stops": [{
                    "client_id": client["id"], "company_name": client["company_name"],
                    "address": client.get("address", ""), "city": client.get("city", ""),
                    "lat": client["lat"], "lng": client["lng"],
                    "distance_from_prev_km": 0.0, "travel_minutes_from_prev": 0,
                    "eta": current_time.strftime("%H:%M"), "departure": departure.strftime("%H:%M"),
                    "suspicious_distance": False,
                }],
                "total_distance_km": 0.0, "total_travel_minutes": 0,
                "total_visit_minutes": visit_minutes,
                "estimated_end_time": departure.strftime("%H:%M"),
                "used_real_routing": False,
                "warnings": [],
            }

        coords = [(c["lat"], c["lng"]) for c in selected]
        distances_km, durations_min, used_real_routing = await get_distance_duration_matrix(coords)

        order_idx = _nearest_neighbor_order(distances_km, start=0)
        order_idx = _two_opt(order_idx, distances_km)

        stops = []
        warnings = []
        total_km = 0.0
        total_travel_minutes = 0.0
        for pos, idx in enumerate(order_idx):
            client = selected[idx]
            distance_km = 0.0
            travel_minutes = 0.0
            suspicious = False
            if pos > 0:
                prev_idx = order_idx[pos - 1]
                distance_km = distances_km[prev_idx][idx]
                travel_minutes = durations_min[prev_idx][idx]
                current_time += timedelta(minutes=travel_minutes)
                total_km += distance_km
                total_travel_minutes += travel_minutes
                if distance_km > _SUSPICIOUS_LEG_DISTANCE_KM:
                    suspicious = True
                    prev_client = selected[prev_idx]
                    warnings.append(
                        f"Distanza implausibile ({round(distance_km)} km) tra "
                        f"\"{prev_client['company_name']}\" e \"{client['company_name']}\": "
                        "controlla l'indirizzo geolocalizzato di questi clienti, probabilmente errato."
                    )
            eta = current_time
            departure = eta + timedelta(minutes=visit_minutes)
            stops.append({
                "client_id": client["id"], "company_name": client["company_name"],
                "address": client.get("address", ""), "city": client.get("city", ""),
                "lat": client["lat"], "lng": client["lng"],
                "distance_from_prev_km": round(distance_km, 1),
                "travel_minutes_from_prev": round(travel_minutes),
                "eta": eta.strftime("%H:%M"), "departure": departure.strftime("%H:%M"),
                "suspicious_distance": suspicious,
            })
            current_time = departure

        return {
            "stops": stops,
            "total_distance_km": round(total_km, 1),
            "total_travel_minutes": round(total_travel_minutes),
            "total_visit_minutes": visit_minutes * len(selected),
            "estimated_end_time": current_time.strftime("%H:%M"),
            "used_real_routing": used_real_routing,
            "warnings": warnings,
        }


route_optimization_service = RouteOptimizationService()

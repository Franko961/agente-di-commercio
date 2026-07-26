"""
Test per il nuovo pianificatore del giro visita
(services.route_optimization_service): la parte che mancava rispetto alla
sola geocodifica — ordinamento delle tappe, calcolo di distanze/tempi, e
proposta di una schedulazione oraria per la giornata.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_route_optimization.py -v
"""
import sys
import asyncio
import random

import pytest

sys.path.insert(0, ".")

import services.route_optimization_service as route_opt_mod
from services.route_optimization_service import (
    RouteOptimizationService, haversine_km, _nearest_neighbor_order, _two_opt, _path_length,
    get_distance_duration_matrix,
)
from core.exceptions import NotFoundError, ValidationAppError


def run(coro):
    return asyncio.run(coro)


# ---------- haversine_km ----------

def test_haversine_distanza_nulla_tra_stesso_punto():
    assert haversine_km(45.0, 9.0, 45.0, 9.0) == 0.0


def test_haversine_milano_roma_ordine_di_grandezza_corretto():
    # Milano (45.4642, 9.1900) - Roma (41.9028, 12.4964): circa 480 km in
    # linea d'aria. Non serve precisione esatta, solo l'ordine di grandezza
    # giusto (tolleranza ampia, non testiamo l'esattezza della formula ma
    # che non ci siano errori grossolani, es. lat/lng invertiti).
    km = haversine_km(45.4642, 9.1900, 41.9028, 12.4964)
    assert 400 < km < 550


# ---------- _nearest_neighbor_order / _two_opt: proprietà generali ----------

def _symmetric_random_matrix(n, seed):
    rng = random.Random(seed)
    points = [(rng.uniform(0, 100), rng.uniform(0, 100)) for _ in range(n)]
    return [[((points[i][0] - points[j][0]) ** 2 + (points[i][1] - points[j][1]) ** 2) ** 0.5
              for j in range(n)] for i in range(n)]


@pytest.mark.parametrize("n,seed", [(4, 1), (6, 2), (8, 3), (10, 4)])
def test_ordine_e_una_permutazione_valida_con_partenza_fissa(n, seed):
    matrix = _symmetric_random_matrix(n, seed)
    nn_order = _nearest_neighbor_order(matrix, start=0)
    order = _two_opt(nn_order, matrix)

    assert sorted(order) == list(range(n))  # ogni tappa visitata esattamente una volta
    assert order[0] == 0  # la prima tappa della lista ricevuta resta sempre la partenza


@pytest.mark.parametrize("n,seed", [(4, 10), (6, 11), (8, 12), (10, 13), (12, 14)])
def test_two_opt_non_peggiora_mai_il_percorso_di_nearest_neighbor(n, seed):
    matrix = _symmetric_random_matrix(n, seed)
    nn_order = _nearest_neighbor_order(matrix, start=0)
    improved_order = _two_opt(nn_order, matrix)

    assert _path_length(improved_order, matrix) <= _path_length(nn_order, matrix) + 1e-9


def test_caso_concreto_quattro_tappe_ordine_atteso():
    """Quattro punti su una linea (posizioni 10, 0, 11, 1): partendo dal
    punto in posizione 10, il percorso ottimo visita le altre tappe in
    ordine di prossimità (11, poi 1, poi 0), senza tornare indietro."""
    positions = [10, 0, 11, 1]
    matrix = [[abs(positions[i] - positions[j]) for j in range(4)] for i in range(4)]

    nn_order = _nearest_neighbor_order(matrix, start=0)
    order = _two_opt(nn_order, matrix)

    assert order == [0, 2, 3, 1]  # posizioni visitate: 10 -> 11 -> 1 -> 0


# ---------- get_distance_duration_matrix: ORS vs fallback haversine ----------

def test_senza_chiave_ors_usa_stima_in_linea_daria(monkeypatch):
    monkeypatch.setattr(route_opt_mod, "ORS_API_KEY", "")
    coords = [(45.0, 9.0), (45.1, 9.1)]

    distances, durations, used_real_routing = run(get_distance_duration_matrix(coords))

    assert used_real_routing is False
    assert distances[0][1] > 0
    assert durations[0][1] > 0


def test_con_chiave_ors_valida_usa_i_dati_reali(monkeypatch):
    monkeypatch.setattr(route_opt_mod, "ORS_API_KEY", "fake-key")

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"distances": [[0, 12000], [12000, 0]], "durations": [[0, 900], [900, 0]]}

    monkeypatch.setattr(route_opt_mod.requests, "post", lambda *a, **k: FakeResponse())
    coords = [(45.0, 9.0), (45.1, 9.1)]

    distances, durations, used_real_routing = run(get_distance_duration_matrix(coords))

    assert used_real_routing is True
    assert distances[0][1] == 12.0  # 12000 m -> 12 km
    assert durations[0][1] == 15.0  # 900 s -> 15 min


def test_ors_che_fallisce_ricade_su_stima_in_linea_daria(monkeypatch):
    """Un errore di rete verso OpenRouteService non deve mai far fallire la
    pianificazione del giro: deve solo far ricadere sulla stima locale."""
    import requests as requests_mod
    monkeypatch.setattr(route_opt_mod, "ORS_API_KEY", "fake-key")

    def _raise(*a, **k):
        raise requests_mod.exceptions.ConnectionError("rete non disponibile, per il test")

    monkeypatch.setattr(route_opt_mod.requests, "post", _raise)
    coords = [(45.0, 9.0), (45.1, 9.1)]

    distances, durations, used_real_routing = run(get_distance_duration_matrix(coords))

    assert used_real_routing is False
    assert distances[0][1] > 0


# ---------- RouteOptimizationService.plan_day ----------

class FakeClientRepo:
    def __init__(self, clients):
        self.clients = clients

    async def find_many(self, user_id, filters):
        return [c for c in self.clients if c["user_id"] == user_id]


MILANO = {"id": "c-milano", "user_id": "user-1", "company_name": "Cliente Milano",
          "lat": 45.4642, "lng": 9.1900, "address": "Via Milano 1", "city": "Milano"}
BERGAMO = {"id": "c-bergamo", "user_id": "user-1", "company_name": "Cliente Bergamo",
           "lat": 45.6983, "lng": 9.6773, "address": "Via Bergamo 1", "city": "Bergamo"}
BRESCIA = {"id": "c-brescia", "user_id": "user-1", "company_name": "Cliente Brescia",
           "lat": 45.5416, "lng": 10.2118, "address": "Via Brescia 1", "city": "Brescia"}
NO_COORDS = {"id": "c-senza-coord", "user_id": "user-1", "company_name": "Cliente Senza Indirizzo",
             "lat": None, "lng": None}


def build_service(clients):
    return RouteOptimizationService(client_repo=FakeClientRepo(clients))


def test_nessun_cliente_selezionato_solleva_errore():
    service = build_service([MILANO])
    with pytest.raises(ValidationAppError):
        run(service.plan_day("user-1", []))


def test_cliente_inesistente_solleva_not_found():
    service = build_service([MILANO])
    with pytest.raises(NotFoundError):
        run(service.plan_day("user-1", ["id-che-non-esiste"]))


def test_cliente_senza_coordinate_solleva_errore_chiaro():
    service = build_service([MILANO, NO_COORDS])
    with pytest.raises(ValidationAppError) as exc_info:
        run(service.plan_day("user-1", [MILANO["id"], NO_COORDS["id"]]))
    assert "Senza Indirizzo" in str(exc_info.value.detail)


def test_singolo_cliente_nessun_viaggio():
    service = build_service([MILANO])
    plan = run(service.plan_day("user-1", [MILANO["id"]], start_time="09:00", visit_minutes=30))

    assert len(plan["stops"]) == 1
    assert plan["stops"][0]["eta"] == "09:00"
    assert plan["stops"][0]["departure"] == "09:30"
    assert plan["total_distance_km"] == 0.0
    assert plan["total_travel_minutes"] == 0


def test_piu_clienti_partenza_fissa_e_schedulazione_coerente():
    service = build_service([MILANO, BERGAMO, BRESCIA])
    plan = run(service.plan_day(
        "user-1", [MILANO["id"], BERGAMO["id"], BRESCIA["id"]],
        start_time="09:00", visit_minutes=20,
    ))

    stops = plan["stops"]
    assert len(stops) == 3
    assert {s["client_id"] for s in stops} == {MILANO["id"], BERGAMO["id"], BRESCIA["id"]}
    # Il primo cliente della lista ricevuta resta la partenza del giro.
    assert stops[0]["client_id"] == MILANO["id"]
    assert stops[0]["eta"] == "09:00"

    # Ogni ETA successiva deve essere >= alla departure della tappa precedente.
    from datetime import datetime
    for i in range(1, len(stops)):
        prev_departure = datetime.strptime(stops[i - 1]["departure"], "%H:%M")
        eta = datetime.strptime(stops[i]["eta"], "%H:%M")
        assert eta >= prev_departure

    assert plan["total_visit_minutes"] == 20 * 3
    assert plan["total_distance_km"] > 0
    assert plan["total_travel_minutes"] > 0
    assert plan["used_real_routing"] is False  # nessuna chiave ORS in ambiente di test


def test_orario_di_inizio_non_valido_ricade_sul_default(monkeypatch):
    service = build_service([MILANO])
    plan = run(service.plan_day("user-1", [MILANO["id"]], start_time="non-un-orario"))
    assert plan["stops"][0]["eta"] == "09:00"  # DEFAULT_START_TIME


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

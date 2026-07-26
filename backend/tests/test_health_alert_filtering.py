"""
Verifica _endpoint_problems() (services.startup_service): la logica che
decide quali endpoint con errori finiscono nell'email di allerta anomalie.

Il caso che ha motivato questo fix: GET /api/auth/me risponde 401 ogni volta
che chi naviga il sito non ha una sessione valida (visitatore anonimo,
sessione scaduta) — è la risposta corretta al controllo "sono autenticato?",
non un sintomo di guasto. Senza esclusione, con poco traffico bastano un
paio di visite anonime per far scattare un falso allarme.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_health_alert_filtering.py -v
"""
import sys

sys.path.insert(0, ".")

from services.startup_service import _endpoint_problems, ALERT_MIN_SAMPLE_SIZE, ALERT_ERROR_RATE_THRESHOLD_PCT


def _endpoint(method, path, count, error_count, status_class="status_4xx"):
    return {
        "method": method, "path": path, "count": count,
        "status_4xx": error_count if status_class == "status_4xx" else 0,
        "status_5xx": error_count if status_class == "status_5xx" else 0,
        "error_rate_pct": round(error_count / count * 100, 1),
    }


def test_auth_me_con_errori_non_genera_alert():
    """Il caso reale che ha motivato il fix: 2 401 su 5 richieste a
    GET /api/auth/me (40%, sopra soglia) non deve generare nessun problema."""
    endpoints = [_endpoint("GET", "/api/auth/me", count=5, error_count=2)]
    assert _endpoint_problems(endpoints) == []


def test_altro_endpoint_con_stesso_tasso_derrore_genera_alert():
    """Lo stesso identico tasso di errore su un endpoint qualunque (non
    nella lista dei "benigni") deve invece generare l'alert normalmente —
    conferma che l'esclusione è specifica per auth/me, non un bug che
    disattiva l'alerting in generale."""
    endpoints = [_endpoint("POST", "/api/orders", count=5, error_count=2)]
    problems = _endpoint_problems(endpoints)
    assert len(problems) == 1
    assert "POST /api/orders" in problems[0]
    assert "40.0%" in problems[0]


def test_auth_me_con_metodo_diverso_non_e_escluso():
    """L'esclusione è per (metodo, path) esatti: solo GET /api/auth/me è
    benigno, non un ipotetico altro metodo sullo stesso path."""
    endpoints = [_endpoint("DELETE", "/api/auth/me", count=5, error_count=5)]
    problems = _endpoint_problems(endpoints)
    assert len(problems) == 1


def test_sotto_soglia_non_genera_comunque_alert():
    endpoints = [_endpoint("POST", "/api/orders", count=5, error_count=0)]
    assert _endpoint_problems(endpoints) == []


def test_campione_troppo_piccolo_non_genera_alert():
    endpoints = [_endpoint("POST", "/api/orders", count=ALERT_MIN_SAMPLE_SIZE - 1, error_count=ALERT_MIN_SAMPLE_SIZE - 1)]
    assert _endpoint_problems(endpoints) == []


def test_piu_endpoint_filtra_solo_quello_benigno():
    endpoints = [
        _endpoint("GET", "/api/auth/me", count=10, error_count=8),
        _endpoint("POST", "/api/orders", count=10, error_count=8),
    ]
    problems = _endpoint_problems(endpoints)
    assert len(problems) == 1
    assert "POST /api/orders" in problems[0]


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))

"""
Test per i tool di ricerca/filtro in sola lettura search_clients e
search_offers, che permettono di rispondere con precisione a domande come
"clienti che non acquistano da tre mesi", "offerte sopra 5000 euro",
"clienti visitati a maggio" — invece di affidarsi al riassunto parziale di
gather_context (primi 20 clienti, ultime 10 offerte), insufficiente per
query esatte su tutto il dataset.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    ANTHROPIC_API_KEY=test python -m pytest test_ai_search_tools.py -v
"""
import sys
import asyncio
from datetime import datetime, timedelta, timezone

sys.path.insert(0, ".")

from tests.test_ai_tool_forcing import FakeClientRepo, FakeSimpleRepo, FakeAiRepo, FakeActionLogRepo


def run(coro):
    return asyncio.run(coro)


class FakeListRepo:
    """Repo generico che restituisce una lista fissa di documenti per
    find_many(user_id), per popolare ordini/appuntamenti/offerte nei test."""

    def __init__(self, docs=None):
        self.docs = docs or []

    async def find_many(self, user_id, *args, **kwargs):
        return list(self.docs)


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def build_service_for_search(clients=None, orders=None, appointments=None, offers=None):
    from services.ai_service import AiService
    client_repo = FakeClientRepo()
    client_repo.docs = clients or []
    service = AiService(
        repo=FakeAiRepo(),
        client_repo=client_repo,
        appointment_repo=FakeListRepo(appointments or []),
        lead_repo=FakeSimpleRepo(),
        offer_repo=FakeListRepo(offers or []),
        commission_repo=FakeSimpleRepo(),
        mandante_repo=FakeSimpleRepo(),
        product_repo=FakeSimpleRepo(),
        expense_repo=FakeSimpleRepo(),
        action_log_repo=FakeActionLogRepo(),
        order_repo=FakeListRepo(orders or []),
    )
    return service


# ---------- search_clients ----------

def test_search_clients_non_acquistano_da_almeno_n_giorni():
    now = datetime.now(timezone.utc)
    service = build_service_for_search(
        clients=[
            {"id": "c-old", "user_id": "u1", "company_name": "Trascurato Srl", "zone": "Milano", "potential": "medio"},
            {"id": "c-recent", "user_id": "u1", "company_name": "Recente Srl", "zone": "Milano", "potential": "medio"},
            {"id": "c-never", "user_id": "u1", "company_name": "MaiOrdinato Srl", "zone": "Milano", "potential": "medio"},
        ],
        orders=[
            {"client_id": "c-old", "created_at": _iso(now - timedelta(days=100))},
            {"client_id": "c-recent", "created_at": _iso(now - timedelta(days=10))},
        ],
    )

    result = run(service.execute_crm_tool("search_clients", {"min_days_since_last_order": 90}, "u1"))

    assert "Trascurato Srl" in result
    assert "MaiOrdinato Srl" in result  # mai ordinato -> soddisfa sempre il filtro
    assert "Recente Srl" not in result


def test_search_clients_visitati_in_un_mese():
    service = build_service_for_search(
        clients=[
            {"id": "c-maggio", "user_id": "u1", "company_name": "VisitatoMaggio Srl", "zone": "Roma", "potential": "alto"},
            {"id": "c-giugno", "user_id": "u1", "company_name": "VisitatoGiugno Srl", "zone": "Roma", "potential": "alto"},
        ],
        appointments=[
            {"client_id": "c-maggio", "start": "2026-05-15T10:00:00Z", "status": "pianificato"},
            {"client_id": "c-giugno", "start": "2026-06-02T10:00:00Z", "status": "pianificato"},
        ],
    )

    result = run(service.execute_crm_tool("search_clients", {"visited_month": "2026-05"}, "u1"))

    assert "VisitatoMaggio Srl" in result
    assert "VisitatoGiugno Srl" not in result


def test_search_clients_filtra_per_zona_e_potenziale():
    service = build_service_for_search(clients=[
        {"id": "c-1", "user_id": "u1", "company_name": "Nord Srl", "zone": "Milano", "potential": "alto"},
        {"id": "c-2", "user_id": "u1", "company_name": "Sud Srl", "zone": "Napoli", "potential": "alto"},
        {"id": "c-3", "user_id": "u1", "company_name": "NordBasso Srl", "zone": "Milano", "potential": "basso"},
    ])

    result = run(service.execute_crm_tool("search_clients", {"zone": "Milano", "potential": "alto"}, "u1"))

    assert "Nord Srl" in result
    assert "Sud Srl" not in result
    assert "NordBasso Srl" not in result


def test_search_clients_nessun_risultato_restituisce_messaggio_chiaro():
    service = build_service_for_search(clients=[
        {"id": "c-1", "user_id": "u1", "company_name": "Solo Srl", "zone": "Milano", "potential": "medio"},
    ])

    result = run(service.execute_crm_tool("search_clients", {"zone": "Torino"}, "u1"))

    assert "Nessun cliente trovato" in result


# ---------- search_offers ----------

def test_search_offers_filtra_per_importo_minimo():
    service = build_service_for_search(offers=[
        {"title": "Grande vendita", "total": 6000, "status": "accettata"},
        {"title": "Piccola vendita", "total": 500, "status": "accettata"},
    ])

    result = run(service.execute_crm_tool("search_offers", {"min_amount": 5000}, "u1"))

    assert "Grande vendita" in result
    assert "Piccola vendita" not in result


def test_search_offers_filtra_per_importo_massimo():
    service = build_service_for_search(offers=[
        {"title": "Grande vendita", "total": 6000, "status": "accettata"},
        {"title": "Piccola vendita", "total": 500, "status": "accettata"},
    ])

    result = run(service.execute_crm_tool("search_offers", {"max_amount": 1000}, "u1"))

    assert "Piccola vendita" in result
    assert "Grande vendita" not in result


def test_search_offers_filtra_per_stato():
    service = build_service_for_search(offers=[
        {"title": "Bozza X", "total": 1000, "status": "bozza"},
        {"title": "Accettata Y", "total": 1000, "status": "accettata"},
    ])

    result = run(service.execute_crm_tool("search_offers", {"status": "accettata"}, "u1"))

    assert "Accettata Y" in result
    assert "Bozza X" not in result


def test_search_offers_nessun_risultato_restituisce_messaggio_chiaro():
    service = build_service_for_search(offers=[{"title": "X", "total": 100, "status": "bozza"}])

    result = run(service.execute_crm_tool("search_offers", {"min_amount": 999999}, "u1"))

    assert "Nessuna offerta trovata" in result


def test_search_offers_non_e_un_tool_di_scrittura():
    """search_clients/search_offers non devono comparire tra i tool bloccati
    per l'account demo (sono di sola lettura)."""
    from services.ai_service import CRM_WRITE_TOOLS
    assert "search_clients" not in CRM_WRITE_TOOLS
    assert "search_offers" not in CRM_WRITE_TOOLS


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))

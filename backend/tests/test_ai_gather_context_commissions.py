"""
Verifica che gather_context includa un riepilogo delle provvigioni nel testo
passato all'assistente AI. Prima di questo fix, il repository delle
provvigioni veniva interrogato ma il risultato non finiva mai nel riassunto:
l'AI non aveva quindi visibilità sulla situazione provvigionale dell'utente
nel contesto generale (solo se invocava esplicitamente un tool dedicato).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    ANTHROPIC_API_KEY=test python -m pytest test_ai_gather_context_commissions.py -v
"""
import sys
import asyncio

sys.path.insert(0, ".")

from tests.test_ai_tool_forcing import FakeSimpleRepo
from services.ai_service import AiService
from core.utils import now_local


def run(coro):
    return asyncio.run(coro)


class FakeCommissionRepo(FakeSimpleRepo):
    def __init__(self, commissions):
        self.commissions = commissions

    async def find_many(self, user_id, mandante_id=None):
        return list(self.commissions)


def build_service(commissions, manual_commissions=None):
    return AiService(
        repo=FakeSimpleRepo(),
        client_repo=FakeSimpleRepo(),
        appointment_repo=FakeSimpleRepo(),
        lead_repo=FakeSimpleRepo(),
        offer_repo=FakeSimpleRepo(),
        commission_repo=FakeCommissionRepo(commissions),
        manual_commission_repo=FakeCommissionRepo(manual_commissions or []),
        mandante_repo=FakeSimpleRepo(),
        product_repo=FakeSimpleRepo(),
        expense_repo=FakeSimpleRepo(),
        action_log_repo=FakeSimpleRepo(),
        order_repo=FakeSimpleRepo(),
    )


def test_gather_context_include_totali_provvigioni():
    current_month = now_local().strftime("%Y-%m")
    commissions = [
        {"amount": 100.0, "status": "maturato", "sale_type": "nuovo", "created_at": f"{current_month}-05T10:00:00+00:00"},
        {"amount": 50.0, "status": "incassato", "sale_type": "rinnovo", "created_at": f"{current_month}-10T10:00:00+00:00"},
    ]
    service = build_service(commissions)

    context = run(service.gather_context("u1"))

    assert "Provvigioni" in context
    assert "maturate non incassate: 100.0" in context
    assert "incassate: 50.0" in context
    assert "totale mese corrente: 150.0" in context


def test_gather_context_lista_provvigioni_recenti_con_bonus():
    commissions = [
        {"amount": 500.0, "status": "maturato", "sale_type": "bonus", "bonus_tier_threshold": 2000, "created_at": "2026-01-01T10:00:00+00:00"},
    ]
    service = build_service(commissions)

    context = run(service.gather_context("u1"))

    assert "bonus scaglione 2000€" in context


def test_gather_context_senza_provvigioni_non_rompe():
    service = build_service([])
    context = run(service.gather_context("u1"))
    assert "maturate non incassate: 0" in context


def test_gather_context_include_provvigioni_manuali_nel_totale():
    current_month = now_local().strftime("%Y-%m")
    manual = [{"period": current_month, "amount": 250.0, "stato": "maturato"}]
    service = build_service([], manual_commissions=manual)

    context = run(service.gather_context("u1"))

    assert "maturate non incassate: 250.0" in context
    assert "totale mese corrente: 250.0" in context

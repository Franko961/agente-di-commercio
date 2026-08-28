"""
Verifica che gli helper PayPal (subscription_service.py) siano davvero
async e non blocchino l'event loop: prima usavano `requests` (sincrona)
direttamente dentro metodi/funzioni async, bloccando l'intero worker per
la durata della chiamata HTTP a PayPal (fino a 10s) — non solo la
richiesta che l'aveva innescata, ma ogni altra richiesta in corso sullo
stesso worker. Stesso principio già applicato a Google Calendar in
services/google_calendar_service.py (asyncio.to_thread).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_paypal_helpers_non_blocking.py -v
"""

import asyncio
import inspect
import sys
import time

sys.path.insert(0, ".")

import services.subscription_service as subscription_mod
from services.subscription_service import SubscriptionService
from tests.test_subscription_cancel_grace_period import FakeResponse, FakeUserRepo


def run(coro):
    return asyncio.run(coro)


def test_paypal_token_e_una_coroutine_function():
    assert inspect.iscoroutinefunction(SubscriptionService._paypal_token)


def test_paypal_get_subscription_e_una_coroutine_function():
    assert inspect.iscoroutinefunction(SubscriptionService._paypal_get_subscription)


def test_verify_paypal_webhook_signature_e_una_coroutine_function():
    assert inspect.iscoroutinefunction(
        SubscriptionService._verify_paypal_webhook_signature
    )


def test_chiamata_paypal_lenta_non_blocca_un_altro_coroutine_concorrente(monkeypatch):
    """Prova concreta che la chiamata bloccante gira su un thread separato:
    un secondo coroutine avviato subito dopo deve poter completare PRIMA
    che la chiamata PayPal (simulata lenta) finisca, se davvero non blocca
    il thread dell'event loop."""
    monkeypatch.setattr(subscription_mod, "PAYPAL_CLIENT_ID", "cid")
    monkeypatch.setattr(subscription_mod, "PAYPAL_CLIENT_SECRET", "secret")

    class SlowRequests:
        def post(self, url, **kwargs):
            time.sleep(0.2)  # requests reale bloccante: simula una PayPal lenta
            return FakeResponse(200, {"access_token": "fake-token"})

    monkeypatch.setattr(subscription_mod, "requests", SlowRequests())

    service = SubscriptionService(repo=FakeUserRepo({}))

    completion_order = []

    async def slow_paypal_call():
        await service._paypal_token()
        completion_order.append("paypal")

    async def fast_unrelated_call():
        await asyncio.sleep(0.01)
        completion_order.append("altra_richiesta")

    async def main():
        await asyncio.gather(slow_paypal_call(), fast_unrelated_call())

    run(main())

    # Se _paypal_token bloccasse l'event loop (chiamata sincrona diretta),
    # fast_unrelated_call non potrebbe MAI intercalarsi e completerebbe
    # sempre DOPO — con asyncio.to_thread, il thread dell'event loop resta
    # libero di eseguire l'altro coroutine nel frattempo.
    assert completion_order[0] == "altra_richiesta"


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))

"""
Verifica services.activation_service.mark_first_action_if_needed: il flag
"_first_action" che client_service/lead_service/order_service aggiungono
alla risposta di creazione (letto dal frontend per l'evento GA4
"first_real_action") deve scattare UNA sola volta per utente, indipendente
da quale dei tre domini sia il primo a chiamarlo.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_activation_service.py -v
"""

import asyncio
import sys

sys.path.insert(0, ".")

import services.activation_service as activation_mod
from services.activation_service import mark_first_action_if_needed


def run(coro):
    return asyncio.run(coro)


class FakeUsersCollection:
    """Riproduce solo il comportamento di find_one_and_update rilevante qui:
    un filtro che include "activated_at": {"$exists": False} deve fallire
    (restituire None) non appena il campo è stato impostato — esattamente
    la condizione su cui si basa la race-safety della funzione reale."""

    def __init__(self, docs):
        self._docs = {d["id"]: d for d in docs}

    async def find_one_and_update(self, filt, update):
        doc = self._docs.get(filt["id"])
        if doc is None:
            return None
        # Riproduce solo il filtro usato dalla funzione reale: match solo se
        # activated_at non è ancora presente sul documento.
        if filt.get("activated_at", {}).get("$exists") is False and "activated_at" in doc:
            return None
        doc.update(update["$set"])
        return dict(doc)


class FakeDb:
    def __init__(self, users):
        self.users = FakeUsersCollection(users)


def _patch_db(monkeypatch, users):
    fake_db = FakeDb(users)
    monkeypatch.setattr(activation_mod, "db", fake_db)
    return fake_db


def test_prima_chiamata_ritorna_true_e_imposta_activated_at(monkeypatch):
    fake_db = _patch_db(monkeypatch, [{"id": "user-1"}])
    result = run(mark_first_action_if_needed("user-1"))
    assert result is True
    assert "activated_at" in fake_db.users._docs["user-1"]


def test_seconda_chiamata_sullo_stesso_utente_ritorna_false(monkeypatch):
    _patch_db(monkeypatch, [{"id": "user-1"}])
    run(mark_first_action_if_needed("user-1"))
    result = run(mark_first_action_if_needed("user-1"))
    assert result is False


def test_utente_gia_attivato_in_precedenza_ritorna_false(monkeypatch):
    _patch_db(monkeypatch, [{"id": "user-1", "activated_at": "2026-01-01T00:00:00+00:00"}])
    result = run(mark_first_action_if_needed("user-1"))
    assert result is False


def test_due_utenti_diversi_sono_indipendenti(monkeypatch):
    _patch_db(monkeypatch, [{"id": "user-1"}, {"id": "user-2"}])
    result_1 = run(mark_first_action_if_needed("user-1"))
    result_2 = run(mark_first_action_if_needed("user-2"))
    assert result_1 is True
    assert result_2 is True


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))

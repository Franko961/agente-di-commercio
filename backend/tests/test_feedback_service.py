"""
Verifica feedback_service: un utente autenticato lascia un feedback (voto +
testo + consenso opzionale alla pubblicazione), che resta privato finché un
admin non lo approva ESPLICITAMENTE — e comunque non compare mai
pubblicamente senza il consenso dato dall'utente stesso al momento
dell'invio. list_public è l'endpoint non autenticato usato dalla sezione
testimonianze in home page: deve esporre solo nome/voto/testo, mai
user_id o altri dati interni.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_feedback_service.py -v
"""
import sys
import asyncio

import pytest

sys.path.insert(0, ".")

from models.feedback import FeedbackIn
from services.feedback_service import FeedbackService
from core.exceptions import NotFoundError


def run(coro):
    return asyncio.run(coro)


class FakeFeedbackRepo:
    def __init__(self, seed=None):
        self.items = list(seed or [])

    async def insert(self, doc):
        self.items.append(doc)
        return doc

    async def find_many(self, limit=500):
        return list(self.items)

    async def find_public(self, limit=20):
        return [i for i in self.items if i.get("approved") and i.get("publish_consent")]

    async def find_one(self, fid):
        return next((i for i in self.items if i["id"] == fid), None)

    async def set_approved(self, fid, approved):
        for i in self.items:
            if i["id"] == fid:
                i["approved"] = approved

    async def delete(self, fid):
        self.items[:] = [i for i in self.items if i["id"] != fid]


def build_service(seed=None):
    repo = FakeFeedbackRepo(seed=seed)
    return FeedbackService(repo=repo), repo


def _user(**overrides):
    base = {"id": "user-1", "name": "Mario Rossi"}
    base.update(overrides)
    return base


def test_create_parte_non_approvato_anche_con_consenso():
    service, repo = build_service()

    result = run(service.create(_user(), FeedbackIn(rating=5, text="Ottimo!", publish_consent=True)))

    assert result["approved"] is False
    assert result["publish_consent"] is True
    assert result["user_id"] == "user-1"
    assert result["user_name"] == "Mario Rossi"


def test_list_public_esclude_non_approvati():
    service, repo = build_service(seed=[
        {"id": "1", "user_id": "u1", "user_name": "Anna", "rating": 5, "text": "Top", "publish_consent": True, "approved": False},
    ])

    result = run(service.list_public())

    assert result == []


def test_list_public_esclude_approvati_senza_consenso():
    """Un admin non può pubblicare un feedback per cui l'utente non ha dato
    il consenso, anche se lo approva: il consenso resta la condizione che
    solo l'utente può dare."""
    service, repo = build_service(seed=[
        {"id": "1", "user_id": "u1", "user_name": "Anna", "rating": 4, "text": "Buono", "publish_consent": False, "approved": True},
    ])

    result = run(service.list_public())

    assert result == []


def test_list_public_espone_solo_nome_voto_testo():
    service, repo = build_service(seed=[
        {"id": "1", "user_id": "u1-segreto", "user_name": "Anna Verdi", "rating": 5, "text": "Fantastico", "publish_consent": True, "approved": True},
    ])

    result = run(service.list_public())

    assert result == [{"name": "Anna Verdi", "rating": 5, "text": "Fantastico"}]
    assert "user_id" not in result[0]
    assert "approved" not in result[0]


def test_set_approved_su_feedback_inesistente_solleva_not_found():
    service, repo = build_service()

    with pytest.raises(NotFoundError):
        run(service.set_approved("non-esiste", True))


def test_delete_su_feedback_inesistente_solleva_not_found():
    service, repo = build_service()

    with pytest.raises(NotFoundError):
        run(service.delete("non-esiste"))


def test_delete_rimuove_il_feedback():
    service, repo = build_service(seed=[
        {"id": "1", "user_id": "u1", "user_name": "Anna", "rating": 3, "text": "Ok", "publish_consent": False, "approved": False},
    ])

    run(service.delete("1"))

    assert repo.items == []


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

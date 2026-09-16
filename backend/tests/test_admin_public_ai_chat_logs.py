"""
Test per admin_service.get_public_ai_chat_logs: la pagina Admin ("Chat AI
pubblica") legge da qui per mostrare a Franco le domande reali fatte al
widget pubblico della homepage (vedi services/public_ai_chat_service.py).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_admin_public_ai_chat_logs.py -v
"""

import asyncio
import sys

sys.path.insert(0, ".")

import services.admin_service as admin_service_mod
from services.admin_service import AdminService


def run(coro):
    return asyncio.run(coro)


class FakePublicAiChatLogRepo:
    def __init__(self, docs):
        self.docs = docs
        self.last_page = None
        self.last_limit = None

    async def find_page(self, page=1, limit=50):
        self.last_page = page
        self.last_limit = limit
        start = (page - 1) * limit
        return self.docs[start : start + limit]

    async def count(self):
        return len(self.docs)


def test_ritorna_entries_totale_e_pagina(monkeypatch):
    docs = [
        {"id": f"log-{i}", "domanda": f"domanda {i}", "risposta": "ok"}
        for i in range(3)
    ]
    fake_repo = FakePublicAiChatLogRepo(docs)
    monkeypatch.setattr(admin_service_mod, "public_ai_chat_log_repository", fake_repo)
    service = AdminService()

    result = run(service.get_public_ai_chat_logs(page=1, limit=50))

    assert result == {"entries": docs, "total": 3, "page": 1}
    assert fake_repo.last_page == 1
    assert fake_repo.last_limit == 50


def test_pagina_e_limit_passati_al_repository(monkeypatch):
    docs = [{"id": f"log-{i}"} for i in range(5)]
    fake_repo = FakePublicAiChatLogRepo(docs)
    monkeypatch.setattr(admin_service_mod, "public_ai_chat_log_repository", fake_repo)
    service = AdminService()

    result = run(service.get_public_ai_chat_logs(page=2, limit=2))

    assert result["entries"] == docs[2:4]
    assert result["total"] == 5
    assert result["page"] == 2

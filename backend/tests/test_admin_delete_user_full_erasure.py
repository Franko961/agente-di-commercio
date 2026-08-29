"""
Verifica il fix di admin_service.delete_user(): prima cancellava solo il
documento utente (self.repo.delete_user), lasciando un eventuale
abbonamento Stripe/PayPal attivo a fatturare per sempre (nessun account a
cui ricollegarlo) e tutti i dati/file del cliente orfani nel database/S3 —
la stessa identica azione concettuale trattata in modo molto più
superficiale rispetto alla cancellazione self-service (gdpr_service.
delete_account). Ora delete_user delega a gdpr_service._erase_user_data,
lo stesso nucleo di cancellazione usato da delete_account.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_admin_delete_user_full_erasure.py -v
"""

import asyncio
import sys

sys.path.insert(0, ".")

import services.admin_service as admin_service_mod
import services.gdpr_service as gdpr_mod
from services.admin_service import AdminService


def run(coro):
    return asyncio.run(coro)


class FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    async def to_list(self, n):
        return self._docs[:n]


class FakeCollection:
    def __init__(self, name):
        self.name = name
        self.docs = []
        self.deleted_many_calls = []
        self.deleted_one_calls = []

    def find(self, query, projection=None):
        user_id = query.get("user_id")
        docs = [
            d for d in self.docs if (user_id is None or d.get("user_id") == user_id)
        ]
        return FakeCursor(docs)

    async def find_one(self, query, projection=None):
        for d in self.docs:
            if all(d.get(k) == v for k, v in query.items()):
                return dict(d)
        return None

    async def delete_many(self, query):
        self.deleted_many_calls.append(query)
        before = len(self.docs)
        self.docs = [d for d in self.docs if d.get("user_id") != query.get("user_id")]
        return type("R", (), {"deleted_count": before - len(self.docs)})()

    async def delete_one(self, query):
        self.deleted_one_calls.append(query)
        self.docs = [
            d for d in self.docs if not all(d.get(k) == v for k, v in query.items())
        ]

    async def insert_one(self, doc):
        pass


class FakeDb:
    def __init__(self):
        self._collections = {}

    def _get(self, name):
        if name not in self._collections:
            self._collections[name] = FakeCollection(name)
        return self._collections[name]

    def __getattr__(self, name):
        return self._get(name)

    def __getitem__(self, name):
        return self._get(name)


class FakeAdminRepo:
    """delete_user non deve più passare da qui — solo _record_audit lo usa
    indirettamente tramite db.admin_audit_log, non tramite questo repo."""

    pass


def test_admin_delete_user_cancella_labbonamento_e_i_dati_collegati(monkeypatch):
    fake_db = FakeDb()
    fake_db.users.docs.append(
        {
            "id": "vittima",
            "email": "vittima@test.it",
            "stripe_subscription_id": "sub_123",
        }
    )
    fake_db.clients.docs.append(
        {"id": "c1", "user_id": "vittima", "company_name": "Cliente della vittima"}
    )
    fake_db.clients.docs.append(
        {"id": "c2", "user_id": "altro-utente", "company_name": "Non toccare"}
    )

    monkeypatch.setattr(gdpr_mod, "db", fake_db)
    monkeypatch.setattr(gdpr_mod, "storage_delete", lambda path: None)
    monkeypatch.setattr(admin_service_mod, "db", fake_db)

    cancel_calls = []

    class FakeSubscriptionService:
        async def cancel_subscription(self, user):
            cancel_calls.append(user["id"])
            return {"ok": True}

    monkeypatch.setattr(gdpr_mod, "subscription_service", FakeSubscriptionService())

    service = AdminService(repo=FakeAdminRepo())
    admin_actor = {"id": "admin-1", "email": "admin@salesfly.it"}

    run(service.delete_user("vittima", admin=admin_actor))

    # L'abbonamento è stato (tentato di) cancellare, non lasciato a fatturare a vuoto.
    assert cancel_calls == ["vittima"]
    # I dati della vittima sono spariti dalle collection user-scoped...
    assert all(d.get("user_id") != "vittima" for d in fake_db.clients.docs)
    # ...ma quelli di un altro utente restano intatti.
    assert any(d.get("user_id") == "altro-utente" for d in fake_db.clients.docs)
    # Il documento utente stesso è stato cancellato.
    assert fake_db.users.deleted_one_calls == [{"id": "vittima"}]


def test_admin_delete_user_traccia_ancora_laudit(monkeypatch):
    fake_db = FakeDb()
    fake_db.users.docs.append({"id": "u-99", "email": "u99@test.it"})

    monkeypatch.setattr(gdpr_mod, "db", fake_db)
    monkeypatch.setattr(gdpr_mod, "storage_delete", lambda path: None)
    monkeypatch.setattr(admin_service_mod, "db", fake_db)

    class FakeSubscriptionService:
        async def cancel_subscription(self, user):
            return {"ok": True}

    monkeypatch.setattr(gdpr_mod, "subscription_service", FakeSubscriptionService())

    inserted = []
    original_insert_one = FakeCollection.insert_one

    async def tracking_insert_one(self, doc):
        if self.name == "admin_audit_log":
            inserted.append(doc)
        await original_insert_one(self, doc)

    monkeypatch.setattr(FakeCollection, "insert_one", tracking_insert_one)

    service = AdminService(repo=FakeAdminRepo())
    admin_actor = {"id": "admin-1", "email": "admin@salesfly.it"}

    run(service.delete_user("u-99", admin=admin_actor))

    assert len(inserted) == 1
    assert inserted[0]["action"] == "delete_user"
    assert inserted[0]["target_user_id"] == "u-99"


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))

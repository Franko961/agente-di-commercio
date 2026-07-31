"""
Verifica che il nome fornito in fase di registrazione (endpoint pubblico
/api/auth/register, non autenticato) venga HTML-escaped prima di finire nel
corpo delle due email generate (benvenuto utente + notifica admin) — stessa
protezione già applicata in contact_request_service.py e
demo_request_service.py, e per lo stesso motivo: senza, un valore come
"<img src=x onerror=...>" verrebbe interpretato dal client di posta di chi
legge invece che mostrato come testo semplice.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_auth_register_html_escaping.py -v
"""
import sys
import asyncio

sys.path.insert(0, ".")

import services.auth_service as auth_service_mod
from services.auth_service import AuthService
from models.auth import RegisterIn


def run(coro):
    return asyncio.run(coro)


async def _allow_always(*a, **kw):
    return True


async def _fake_seed_demo(user_id):
    return None


sent_emails = []


async def _capturing_send_email(to, subject, html):
    sent_emails.append({"to": to, "subject": subject, "html": html})
    return True


class FakeUserRepo:
    def __init__(self):
        self.inserted = []

    async def find_by_email(self, email):
        return None

    async def insert(self, doc):
        self.inserted.append(doc)
        return doc


def test_nome_malevolo_viene_html_escaped_in_entrambe_le_email(monkeypatch):
    sent_emails.clear()
    monkeypatch.setattr(auth_service_mod, "check_and_record", _allow_always)
    monkeypatch.setattr(auth_service_mod.seed_service, "seed_demo", _fake_seed_demo)
    monkeypatch.setattr(auth_service_mod, "send_email", _capturing_send_email)
    service = AuthService(repo=FakeUserRepo())

    run(service.register(
        RegisterIn(
            email="nuovo@example.com", password="password123",
            name="<img src=x onerror=alert(1)></b><script>alert(2)</script>",
        ),
        ip_address="1.2.3.4",
    ))

    assert len(sent_emails) == 2  # benvenuto + notifica admin
    for mail in sent_emails:
        # Il tag resta come TESTO innocuo (es. "&lt;img ... &gt;"): quello
        # che non deve mai comparire è il tag vero e proprio, che un client
        # di posta interpreterebbe come markup invece che come testo.
        assert "<img" not in mail["html"]
        assert "<script" not in mail["html"]
        assert "&lt;img src=x onerror=alert(1)&gt;" in mail["html"]


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))

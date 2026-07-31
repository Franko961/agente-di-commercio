"""
Verifica demo_request_service.create(): l'endpoint pubblico e non
autenticato che crea un account VERO (con dati demo seminati), senza però
una password realmente utilizzabile — l'utente la sceglie lui stesso
tramite un link monouso inviato via email (stesso meccanismo di
generate_reset_token/reset_password già usato per "password dimenticata"),
invece di ricevere una password generata da noi in chiaro. Senza limite di
frequenza per IP, chiunque potrebbe scriptare la creazione di account
fasulli in massa e/o far ricevere a indirizzi altrui email non richieste.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_demo_request_service.py -v
"""
import re
import sys
import asyncio

import pytest
from fastapi import HTTPException

sys.path.insert(0, ".")

from models.demo_request import DemoRequestIn
import services.demo_request_service as demo_request_mod
from services.demo_request_service import DemoRequestService
from core.exceptions import ValidationAppError
from core.security import hash_reset_token


def run(coro):
    return asyncio.run(coro)


async def _allow_always(*a, **kw):
    return True


async def _deny_always(*a, **kw):
    return False


sent_emails = []


async def _fake_send_email(to, subject, html):
    sent_emails.append({"to": to, "subject": subject, "html": html})
    return True


async def _fake_seed_demo(user_id):
    return None


class FakeUserRepo:
    def __init__(self, existing_emails=None):
        self.existing_emails = set(existing_emails or [])
        self.inserted = []

    async def find_by_email(self, email):
        return {"id": "existing-user"} if email in self.existing_emails else None

    async def insert(self, doc):
        self.inserted.append(doc)
        return doc


class FakeDemoRequestRepo:
    def __init__(self):
        self.inserted = []

    async def insert(self, doc):
        self.inserted.append(doc)
        return doc

    async def find_many(self):
        return self.inserted


def _payload(**overrides):
    base = dict(
        nome="Mario", cognome="Rossi", email="mario.rossi@example.com",
        azienda="", telefono="", privacy_consent=True, marketing_consent=False,
    )
    base.update(overrides)
    return DemoRequestIn(**base)


def build_service(monkeypatch, check_and_record_fn=_allow_always, existing_emails=None):
    monkeypatch.setattr(demo_request_mod, "check_and_record", check_and_record_fn)
    monkeypatch.setattr(demo_request_mod, "send_email", _fake_send_email)
    monkeypatch.setattr(demo_request_mod.seed_service, "seed_demo", _fake_seed_demo)
    sent_emails.clear()
    users = FakeUserRepo(existing_emails=existing_emails)
    repo = FakeDemoRequestRepo()
    return DemoRequestService(repo=repo, users=users), users, repo


def test_richiesta_valida_crea_account_e_invia_email(monkeypatch):
    service, users, repo = build_service(monkeypatch)

    result = run(service.create(_payload(), ip_address="1.2.3.4", user_agent="pytest"))

    assert result == {"ok": True, "setup_email_sent": True}
    assert len(users.inserted) == 1
    assert users.inserted[0]["subscription_status"] == "trial"
    # L'account nasce con un link di impostazione password, non una
    # password generata da noi: deve avere un token di reset valido pronto
    # all'uso, esattamente come dopo una richiesta "password dimenticata".
    assert users.inserted[0]["reset_token_hash"]
    assert users.inserted[0]["reset_token_expires"]
    # Un'email all'utente col link di impostazione, una all'admin di notifica.
    assert len(sent_emails) == 2
    assert sent_emails[0]["to"] == "mario.rossi@example.com"

    # Il link nell'email deve contenere ESATTAMENTE il token il cui hash è
    # stato salvato sull'utente — non un token diverso o disallineato, che
    # renderebbe il link inutilizzabile pur sembrando valido.
    match = re.search(r"token=([\w-]+)", sent_emails[0]["html"])
    assert match, "nessun link di impostazione trovato nell'email"
    assert hash_reset_token(match.group(1)) == users.inserted[0]["reset_token_hash"]


def test_campi_del_form_vengono_html_escaped_nelle_due_email(monkeypatch):
    """I campi del form (nome, cognome, azienda, telefono) arrivano da un
    endpoint pubblico non autenticato: un valore come
    '<img src=x onerror=...>' non deve mai finire crudo nel corpo HTML delle
    email (né quella all'utente né quella di notifica admin), altrimenti
    verrebbe interpretato dal client di posta di chi legge invece che
    mostrato come testo semplice — stessa protezione già applicata in
    contact_request_service.py."""
    service, users, repo = build_service(monkeypatch)
    payload = _payload(
        nome="<img src=x onerror=alert(1)>",
        cognome="</b><script>alert(2)</script>",
        azienda="<svg onload=alert(3)>",
        telefono="<b>000</b>",
    )

    run(service.create(payload, ip_address="1.2.3.4", user_agent="pytest"))

    assert len(sent_emails) == 2
    for sent in sent_emails:
        # I tag restano come TESTO innocuo (es. "&lt;img ... &gt;"): quello
        # che non deve mai comparire è il tag vero e proprio, che un client
        # di posta interpreterebbe come markup invece che come testo.
        assert "<img" not in sent["html"]
        assert "<script" not in sent["html"]
        assert "<svg" not in sent["html"]
    # L'email di notifica admin mostra nome/cognome/azienda/telefono: la
    # versione escaped deve comunque comparire come testo (prova che non è
    # stato semplicemente rimosso, ma reso innocuo mantenendo il contenuto).
    admin_html = sent_emails[1]["html"]
    assert "&lt;img src=x onerror=alert(1)&gt;" in admin_html
    assert "&lt;svg onload=alert(3)&gt;" in admin_html


def test_fallimento_invio_email_credenziali_viene_segnalato_ma_account_resta_creato(monkeypatch):
    """Se l'invio dell'email col link di impostazione fallisce, l'utente non
    ha ALCUN modo di impostare una password e accedere: il fallimento deve
    essere propagato nella risposta (per far mostrare al frontend un
    messaggio diverso, che indirizzi a 'password dimenticata'), ma
    l'account va comunque creato — non ha senso bloccare la creazione per
    un problema di consegna email."""
    monkeypatch.setattr(demo_request_mod, "check_and_record", _allow_always)
    monkeypatch.setattr(demo_request_mod.seed_service, "seed_demo", _fake_seed_demo)

    calls = []

    async def _fail_user_email_only(to, subject, html):
        calls.append(to)
        return to != "mario.rossi@example.com"

    monkeypatch.setattr(demo_request_mod, "send_email", _fail_user_email_only)
    users = FakeUserRepo()
    repo = FakeDemoRequestRepo()
    service = DemoRequestService(repo=repo, users=users)

    result = run(service.create(_payload(), ip_address="1.2.3.4", user_agent="pytest"))

    assert result == {"ok": True, "setup_email_sent": False}
    assert len(users.inserted) == 1


def test_email_gia_esistente_viene_rifiutata(monkeypatch):
    service, users, repo = build_service(monkeypatch, existing_emails={"mario.rossi@example.com"})

    with pytest.raises(ValidationAppError):
        run(service.create(_payload(), ip_address="1.2.3.4"))
    assert len(users.inserted) == 0
    assert sent_emails == []


def test_senza_consenso_privacy_viene_rifiutata(monkeypatch):
    service, users, repo = build_service(monkeypatch)

    with pytest.raises(ValidationAppError):
        run(service.create(_payload(privacy_consent=False), ip_address="1.2.3.4"))
    assert len(users.inserted) == 0


def test_troppe_richieste_dallo_stesso_ip_vengono_bloccate(monkeypatch):
    """Il caso che ha motivato il fix: senza rate limit, un IP potrebbe
    scriptare la creazione di account fasulli in massa, inviando email non
    richieste a indirizzi arbitrari."""
    service, users, repo = build_service(monkeypatch, check_and_record_fn=_deny_always)

    with pytest.raises(HTTPException) as exc_info:
        run(service.create(_payload(), ip_address="1.2.3.4"))
    assert exc_info.value.status_code == 429
    # Bloccato PRIMA di creare l'account o inviare email.
    assert len(users.inserted) == 0
    assert sent_emails == []


def test_rate_limit_usa_lip_come_chiave(monkeypatch):
    """Il rate limit deve essere applicato per IP (un attaccante userebbe
    email sempre diverse, è l'IP il segnale utile da arginare)."""
    calls = []

    async def _tracking_check(kind, key, max_attempts, window_minutes):
        calls.append((kind, key))
        return True

    monkeypatch.setattr(demo_request_mod, "check_and_record", _tracking_check)
    monkeypatch.setattr(demo_request_mod, "send_email", _fake_send_email)
    monkeypatch.setattr(demo_request_mod.seed_service, "seed_demo", _fake_seed_demo)
    sent_emails.clear()
    service = DemoRequestService(repo=FakeDemoRequestRepo(), users=FakeUserRepo())

    run(service.create(_payload(), ip_address="9.9.9.9"))

    assert ("demo_request_ip", "9.9.9.9") in calls


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

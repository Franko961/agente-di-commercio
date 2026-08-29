"""
Verifica l'irrobustimento di admin_service.make_admin(): endpoint non
autenticato per natura (serve a creare il primo admin), la cui sicurezza
dipende interamente dalla segretezza di ADMIN_SECRET — prima non aveva
nessun limite di tentativi (forza bruta illimitata su un secret
eventualmente debole) e usava un confronto '!=' invece che a tempo costante.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_make_admin_hardening.py -v
"""

import asyncio
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, ".")

import services.admin_service as admin_service_mod
from services.admin_service import AdminService


def run(coro):
    return asyncio.run(coro)


async def _allow_always(*a, **kw):
    return True


async def _deny_always(*a, **kw):
    return False


class FakeAuditCollection:
    def __init__(self):
        self.inserted = []

    async def insert_one(self, doc):
        self.inserted.append(doc)


class FakeDb:
    def __init__(self):
        self.admin_audit_log = FakeAuditCollection()


class FakeAdminRepo:
    async def promote_by_email(self, email):
        return email == "franco@test.it"


def build_service(monkeypatch, check_and_record_fn=_allow_always):
    monkeypatch.setattr(admin_service_mod, "db", FakeDb())
    monkeypatch.setattr(admin_service_mod, "check_and_record", check_and_record_fn)
    return AdminService(repo=FakeAdminRepo())


def test_secret_corretto_promuove_lutente(monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", "s3gr3t0")
    service = build_service(monkeypatch)

    result = run(service.make_admin("franco@test.it", "s3gr3t0", ip_address="1.2.3.4"))

    assert result["ok"] is True


def test_secret_sbagliato_rifiutato_e_tracciato(monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", "s3gr3t0")
    service = build_service(monkeypatch)

    with pytest.raises(HTTPException) as exc_info:
        run(
            service.make_admin(
                "franco@test.it", "secret-sbagliato", ip_address="1.2.3.4"
            )
        )
    assert exc_info.value.status_code == 403

    # Il tentativo fallito lascia comunque una traccia in audit, distinta
    # dalla promozione riuscita — utile per accorgersi di un tentativo di
    # forza bruta in corso.
    entries = admin_service_mod.db.admin_audit_log.inserted
    assert len(entries) == 1
    assert entries[0]["action"] == "make_admin_failed"


def test_admin_secret_non_configurato_rifiuta_sempre(monkeypatch):
    """Se ADMIN_SECRET non è impostato nell'ambiente (stringa vuota di
    default), l'endpoint deve rifiutare qualunque tentativo — mai un
    default 'aperto'."""
    monkeypatch.delenv("ADMIN_SECRET", raising=False)
    service = build_service(monkeypatch)

    with pytest.raises(HTTPException) as exc_info:
        run(service.make_admin("franco@test.it", "", ip_address="1.2.3.4"))
    assert exc_info.value.status_code == 403


def test_troppi_tentativi_per_email_vengono_bloccati(monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", "s3gr3t0")
    service = build_service(monkeypatch, check_and_record_fn=_deny_always)

    with pytest.raises(HTTPException) as exc_info:
        run(service.make_admin("franco@test.it", "s3gr3t0", ip_address="1.2.3.4"))
    assert exc_info.value.status_code == 429


def test_email_mancante_non_rompe_il_controllo_di_frequenza(monkeypatch):
    """Un tentativo senza email (payload malformato) non deve mai passare
    silenziosamente né far esplodere il controllo di rate limit."""
    monkeypatch.setenv("ADMIN_SECRET", "s3gr3t0")
    service = build_service(monkeypatch)

    with pytest.raises(HTTPException) as exc_info:
        run(service.make_admin("", "s3gr3t0", ip_address="1.2.3.4"))
    assert exc_info.value.status_code == 400


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

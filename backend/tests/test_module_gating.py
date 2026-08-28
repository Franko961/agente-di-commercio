"""
Verifica il meccanismo di attivazione/disattivazione moduli per singolo
account (core/security.py require_module + admin_service.update_user):
un admin può disattivare interi moduli del gestionale (es. "Provvigioni")
per un cliente che non li usa — vedi Admin.jsx "Moduli attivi".

Copre:
- require_module blocca l'accesso quando il modulo è nell'elenco
  disabled_modules dell'utente, lo consente altrimenti (incluso quando
  il campo manca del tutto, per compatibilità con gli account esistenti).
- admin_service.update_user valida disabled_modules: solo una lista di
  chiavi note da MODULE_KEYS, altrimenti 400.
- ai_service: un tool CRM il cui modulo è disattivato viene rifiutato
  prima di essere eseguito, non solo bloccato lato router HTTP — vedi il
  commento su TOOL_MODULE per il perché (l'assistente non deve poter
  aggirare via voce/chat un modulo disattivato dal form web).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_module_gating.py -v
"""

import asyncio
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, ".")

from core.security import MODULE_KEYS, require_module
from services.admin_service import ALLOWED_USER_UPDATE_FIELDS, AdminService


def run(coro):
    return asyncio.run(coro)


# ---------- require_module ----------


def test_modulo_non_disattivato_passa():
    check = require_module("clienti")
    user = {"id": "u1", "disabled_modules": ["provvigioni"]}
    result = run(check(user=user))
    assert result is user


def test_modulo_disattivato_blocca_con_403():
    check = require_module("provvigioni")
    user = {"id": "u1", "disabled_modules": ["provvigioni"]}
    with pytest.raises(HTTPException) as exc:
        run(check(user=user))
    assert exc.value.status_code == 403


def test_utente_senza_il_campo_disabled_modules_non_viene_bloccato():
    """Account creati prima di questa funzionalità non hanno il campo:
    deve valere come "nessun modulo disattivato", non far esplodere il
    controllo (.get(...) or [] deve reggere anche un None esplicito)."""
    check = require_module("clienti")
    user = {"id": "u1"}
    result = run(check(user=user))
    assert result is user


def test_ogni_modulo_e_bloccabile_singolarmente():
    for module in MODULE_KEYS:
        check = require_module(module)
        blocked_user = {"id": "u1", "disabled_modules": [module]}
        with pytest.raises(HTTPException):
            run(check(user=blocked_user))
        other_user = {
            "id": "u1",
            "disabled_modules": [m for m in MODULE_KEYS if m != module],
        }
        assert run(check(user=other_user)) is other_user


# ---------- admin_service.update_user: validazione disabled_modules ----------


class FakeAdminRepo:
    def __init__(self):
        self.updates = []

    async def update_user(self, uid, data):
        self.updates.append((uid, data))

    async def find_admin_by_id(self, uid):
        return None


def build_service():
    repo = FakeAdminRepo()
    service = AdminService(repo=repo)
    service._record_audit = lambda *a, **kw: asyncio.sleep(
        0
    )  # no-op, non è l'oggetto del test
    return service, repo


def test_disabled_modules_e_nella_whitelist_dei_campi_modificabili():
    assert "disabled_modules" in ALLOWED_USER_UPDATE_FIELDS


def test_disabled_modules_valida_accetta_chiavi_note():
    service, repo = build_service()
    run(
        service.update_user(
            "u1",
            {"disabled_modules": ["clienti", "provvigioni"]},
            admin={"id": "admin-1"},
        )
    )
    assert repo.updates == [("u1", {"disabled_modules": ["clienti", "provvigioni"]})]


def test_disabled_modules_rifiuta_chiave_sconosciuta():
    service, repo = build_service()
    with pytest.raises(HTTPException) as exc:
        run(
            service.update_user(
                "u1", {"disabled_modules": ["non-esiste"]}, admin={"id": "admin-1"}
            )
        )
    assert exc.value.status_code == 400
    assert repo.updates == []


def test_disabled_modules_rifiuta_valore_non_lista():
    service, repo = build_service()
    with pytest.raises(HTTPException) as exc:
        run(
            service.update_user(
                "u1", {"disabled_modules": "clienti"}, admin={"id": "admin-1"}
            )
        )
    assert exc.value.status_code == 400
    assert repo.updates == []


# ---------- ai_service: i tool CRM rispettano i moduli disattivati ----------


def test_tool_module_copre_tutti_i_tool_scrittura_con_rischio_di_bypass():
    """add_client/add_note_to_client/search_clients -> clienti,
    add_appointment -> agenda, add_lead -> lead,
    add_offer/search_offers -> offerte, add_expense -> spese: se un tool
    manca da questa mappa, un modulo disattivato dal form web resta
    comunque azionabile parlando con l'assistente."""
    from services.ai_service import CRM_WRITE_TOOLS, TOOL_MODULE

    for tool in CRM_WRITE_TOOLS:
        assert (
            tool in TOOL_MODULE
        ), f"{tool} scrive dati ma non è mappato a nessun modulo in TOOL_MODULE"

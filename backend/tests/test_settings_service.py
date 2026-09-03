"""
Verifica services/settings_service.py per le impostazioni "Azienda" (logo
usato nell'export cartellino, vedi services/attendance_xlsx_export.py).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_settings_service.py -v
"""

import asyncio
import sys

sys.path.insert(0, ".")

from models.company_settings import CompanySettingsIn
from models.fiscal_settings import FiscalSettingsIn
from services.settings_service import SettingsService


def run(coro):
    return asyncio.run(coro)


class FakeUserRepo:
    def __init__(self):
        self.updates = {}

    async def update_by_id(self, uid, data):
        self.updates.setdefault(uid, {}).update(data)


USER = {"id": "user-1", "email": "manager@example.com"}


def test_get_company_settings_ritorna_none_se_mai_impostato():
    service = SettingsService(repo=FakeUserRepo())
    result = run(service.get_company_settings(USER))
    assert result == {"logo": None, "vat_number": None}


def test_update_company_settings_salva_il_logo():
    repo = FakeUserRepo()
    service = SettingsService(repo=repo)
    logo = "data:image/png;base64,aGVsbG8="

    result = run(service.update_company_settings(USER, CompanySettingsIn(logo=logo)))

    assert result == {"logo": logo, "vat_number": None}
    assert repo.updates[USER["id"]] == {
        "company_logo": logo,
        "company_vat_number": None,
    }


def test_update_company_settings_puo_rimuovere_il_logo():
    repo = FakeUserRepo()
    service = SettingsService(repo=repo)

    run(
        service.update_company_settings(
            USER, CompanySettingsIn(logo="data:image/png;base64,aGVsbG8=")
        )
    )
    result = run(service.update_company_settings(USER, CompanySettingsIn(logo=None)))

    assert result == {"logo": None, "vat_number": None}
    assert repo.updates[USER["id"]]["company_logo"] is None


def test_update_company_settings_salva_la_partita_iva():
    repo = FakeUserRepo()
    service = SettingsService(repo=repo)

    result = run(
        service.update_company_settings(
            USER, CompanySettingsIn(vat_number="01234567890")
        )
    )

    assert result == {"logo": None, "vat_number": "01234567890"}
    assert repo.updates[USER["id"]] == {
        "company_logo": None,
        "company_vat_number": "01234567890",
    }


def test_get_fiscal_settings_ritorna_i_default_legali_se_mai_impostato():
    service = SettingsService(repo=FakeUserRepo())
    result = run(service.get_fiscal_settings(USER))
    assert result == {"regime_fiscale": "ordinario", "base_ritenuta": "50"}


def test_update_fiscal_settings_salva_il_regime_forfettario():
    repo = FakeUserRepo()
    service = SettingsService(repo=repo)

    result = run(
        service.update_fiscal_settings(
            USER, FiscalSettingsIn(regime_fiscale="forfettario", base_ritenuta="50")
        )
    )

    assert result == {"regime_fiscale": "forfettario", "base_ritenuta": "50"}
    assert repo.updates[USER["id"]] == {
        "regime_fiscale": "forfettario",
        "base_ritenuta": "50",
    }


def test_update_fiscal_settings_salva_la_base_ritenuta_ridotta():
    repo = FakeUserRepo()
    service = SettingsService(repo=repo)

    result = run(
        service.update_fiscal_settings(
            USER, FiscalSettingsIn(regime_fiscale="ordinario", base_ritenuta="20")
        )
    )

    assert result == {"regime_fiscale": "ordinario", "base_ritenuta": "20"}

"""
Verifica CommissionService.get_effective_commissions: il punto di raccolta
unico usato da dashboard/obiettivi/briefing AI/export CSV/dettaglio cliente
per contare le provvigioni manuali come "vere", non solo nella pagina
Provvigioni. Unisce commission_repository (calcolate dagli ordini) e
manual_commission_repository (inserite a mano), normalizzando queste ultime
nella stessa forma (status da stato, sale_type da tipo, created_at
sintetico dal period — per restare compatibili con i confronti mensili via
local_month_str usati da dashboard_service/ai_service/automation_engine).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_commission_service_effective.py -v
"""

import asyncio
import sys

sys.path.insert(0, ".")

from services.commission_service import CommissionService


def run(coro):
    return asyncio.run(coro)


class FakeCommissionRepo:
    def __init__(self, docs):
        self.docs = list(docs)

    async def find_many(self, user_id, mandante_id=None):
        result = [d for d in self.docs if d["user_id"] == user_id]
        if mandante_id:
            result = [d for d in result if d.get("mandante_id") == mandante_id]
        return result


class FakeManualRepo:
    def __init__(self, docs):
        self.docs = list(docs)

    async def find_many(self, user_id):
        return [d for d in self.docs if d["user_id"] == user_id]


def build_service(real=None, manual=None):
    service = CommissionService(
        repo=FakeCommissionRepo(real or []),
        mandante_repo=None,
        manual_repo=FakeManualRepo(manual or []),
    )
    return service


REAL = {
    "id": "c-1",
    "user_id": "user-1",
    "mandante_id": "m-A",
    "client_id": "cl-1",
    "period": "2026-08",
    "amount": 100,
    "status": "maturato",
    "sale_type": "nuovo",
    "created_at": "2026-08-05T10:00:00+00:00",
}

MANUAL = {
    "user_id": "user-1",
    "period": "2026-08",
    "amount": 500,
    "mandante_id": None,
    "client_id": None,
    "stato": "maturato",
    "tipo": "ordinaria",
}


def test_unisce_reali_e_manuali():
    service = build_service(real=[REAL], manual=[MANUAL])
    result = run(service.get_effective_commissions({"id": "user-1"}))
    assert len(result) == 2
    assert sum(c["amount"] for c in result) == 600


def test_manuale_normalizzata_ha_status_e_sale_type():
    service = build_service(
        manual=[{**MANUAL, "stato": "incassato", "tipo": "rettifica"}]
    )
    result = run(service.get_effective_commissions({"id": "user-1"}))
    assert result[0]["status"] == "incassato"
    assert result[0]["sale_type"] == "rettifica"
    assert result[0]["source"] == "manual"


def test_manuale_senza_stato_default_maturato():
    service = build_service(
        manual=[{"user_id": "user-1", "period": "2026-08", "amount": 200}]
    )
    result = run(service.get_effective_commissions({"id": "user-1"}))
    assert result[0]["status"] == "maturato"


def test_created_at_sintetico_riflette_il_period_non_now():
    """Cruciale: se created_at fosse il momento del salvataggio invece che
    dedotto da period, una provvigione manuale di un mese passato,
    salvata/modificata oggi, verrebbe contata nel mese corrente da
    dashboard_service/ai_service (che confrontano local_month_str(created_at)
    col mese corrente, non period)."""
    service = build_service(manual=[{**MANUAL, "period": "2025-01"}])
    result = run(service.get_effective_commissions({"id": "user-1"}))
    assert result[0]["created_at"].startswith("2025-01-01")


def test_manuale_senza_mandante_esclusa_se_filtro_mandante_specifico():
    service = build_service(manual=[MANUAL])  # mandante_id None
    result = run(service.get_effective_commissions({"id": "user-1"}, mandante_id="m-A"))
    assert result == []


def test_manuale_taggata_inclusa_solo_per_il_suo_mandante():
    tagged = {**MANUAL, "mandante_id": "m-A"}
    service = build_service(manual=[tagged])
    result_a = run(
        service.get_effective_commissions({"id": "user-1"}, mandante_id="m-A")
    )
    result_b = run(
        service.get_effective_commissions({"id": "user-1"}, mandante_id="m-B")
    )
    assert len(result_a) == 1
    assert result_b == []


def test_reale_filtrata_per_mandante_tramite_repo():
    other_mandante_real = {**REAL, "id": "c-2", "mandante_id": "m-B"}
    service = build_service(real=[REAL, other_mandante_real])
    result = run(service.get_effective_commissions({"id": "user-1"}, mandante_id="m-A"))
    assert len(result) == 1
    assert result[0]["id"] == "c-1"


def test_filtro_client_id_si_applica_a_reali_e_manuali():
    manual_for_client = {**MANUAL, "client_id": "cl-1"}
    manual_other_client = {**MANUAL, "client_id": "cl-2"}
    service = build_service(
        real=[REAL], manual=[manual_for_client, manual_other_client]
    )
    result = run(service.get_effective_commissions({"id": "user-1"}, client_id="cl-1"))
    assert len(result) == 2  # la reale (client_id=cl-1) + la manuale taggata cl-1
    assert all(c.get("client_id") == "cl-1" for c in result)


def test_vista_tutti_i_mandanti_include_manuali_taggate_e_non():
    tagged = {**MANUAL, "mandante_id": "m-A"}
    untagged = {**MANUAL, "period": "2026-07"}
    service = build_service(manual=[tagged, untagged])
    result = run(service.get_effective_commissions({"id": "user-1"}))
    assert len(result) == 2

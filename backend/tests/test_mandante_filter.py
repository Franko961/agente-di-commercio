"""
Test isolato (mock) per il filtro "Mandante attivo": verifica che
dashboard_service.get_stats/get_today_brief e i repository di
clienti/offerte/ordini/provvigioni applichino correttamente il filtro per
mandante_id quando presente, e restino invariati (comportamento globale)
quando assente — senza toccare un MongoDB reale.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    ANTHROPIC_API_KEY=test AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test \
    AWS_S3_BUCKET=test python -m pytest test_mandante_filter.py -v
"""

import asyncio
import sys

sys.path.insert(0, ".")

from core.database import db
from core.utils import local_wallclock_to_utc_iso, now_local
from repositories.client_repository import client_repository
from repositories.commission_repository import commission_repository
from repositories.offer_repository import offer_repository
from repositories.order_repository import order_repository
from services.dashboard_service import dashboard_service


def run(coro):
    return asyncio.run(coro)


class FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    def to_list(self, n):
        async def _inner():
            return self._docs[:n]

        return _inner()


class FakeCollection:
    """Replica solo il sottoinsieme di semantica Mongo che ci serve: uguaglianza
    su campo scalare, e "contiene" quando il campo del documento è una lista
    (comportamento reale di Mongo per {"mandante_ids": "x"})."""

    def __init__(self, docs):
        self.docs = docs
        self.last_query = None

    def find(self, query, *_args, **_kwargs):
        self.last_query = query
        matched = []
        for d in self.docs:
            ok = True
            for k, v in query.items():
                if k == "$or":
                    continue
                dv = d.get(k)
                if isinstance(dv, list):
                    if v not in dv:
                        ok = False
                        break
                elif dv != v:
                    ok = False
                    break
            if ok:
                matched.append(d)
        return FakeCursor(matched)


USER = {"id": "u1"}

CLIENTS = [
    {
        "id": "c1",
        "user_id": "u1",
        "mandante_ids": ["m1"],
        "company_name": "Bar Rossi",
        "status": "attivo",
    },
    {
        "id": "c2",
        "user_id": "u1",
        "mandante_ids": ["m2"],
        "company_name": "Alimentari Verdi",
        "status": "attivo",
    },
    {
        "id": "c3",
        "user_id": "u1",
        "mandante_ids": ["m1", "m2"],
        "company_name": "Ristorante Blu",
        "status": "attivo",
    },
]
OFFERS = [
    {
        "id": "o1",
        "user_id": "u1",
        "mandante_id": "m1",
        "client_id": "c1",
        "status": "accettata",
        "total": 1000,
        "created_at": "2026-07-01",
    },
    {
        "id": "o2",
        "user_id": "u1",
        "mandante_id": "m2",
        "client_id": "c2",
        "status": "accettata",
        "total": 2000,
        "created_at": "2026-07-01",
    },
]
COMMISSIONS = [
    {
        "id": "cm1",
        "user_id": "u1",
        "mandante_id": "m1",
        "status": "maturato",
        "amount": 100,
    },
    {
        "id": "cm2",
        "user_id": "u1",
        "mandante_id": "m2",
        "status": "incassato",
        "amount": 200,
    },
]
# "Oggi" calcolato dinamicamente in ora italiana (stessa logica usata da
# get_today_brief), non una data fissa: una data hardcoded scade non appena
# passa quel giorno, rompendo il test per chiunque lo esegua dopo.
_TODAY = now_local().strftime("%Y-%m-%d")
APPTS = [
    {
        "id": "a1",
        "user_id": "u1",
        "client_id": "c1",
        "start": local_wallclock_to_utc_iso(f"{_TODAY}T10:00:00"),
        "status": "pianificato",
    },
    {
        "id": "a2",
        "user_id": "u1",
        "client_id": "c2",
        "start": local_wallclock_to_utc_iso(f"{_TODAY}T11:00:00"),
        "status": "pianificato",
    },
]
ORDERS = [
    {
        "id": "or1",
        "user_id": "u1",
        "mandante_id": "m1",
        "client_id": "c1",
        "created_at": "2026-07-01",
    },
    {
        "id": "or2",
        "user_id": "u1",
        "mandante_id": "m2",
        "client_id": "c2",
        "created_at": "2026-07-01",
    },
]


def install_fake_db(monkeypatch):
    monkeypatch.setattr(db, "clients", FakeCollection(CLIENTS))
    monkeypatch.setattr(db, "offers", FakeCollection(OFFERS))
    monkeypatch.setattr(db, "leads", FakeCollection([]))
    monkeypatch.setattr(db, "appointments", FakeCollection(APPTS))
    monkeypatch.setattr(db, "commissions", FakeCollection(COMMISSIONS))
    monkeypatch.setattr(db, "manual_commissions", FakeCollection([]))
    monkeypatch.setattr(db, "expenses", FakeCollection([]))
    monkeypatch.setattr(db, "orders", FakeCollection(ORDERS))


# ---------- dashboard_service.get_stats ----------


def test_get_stats_senza_mandante_e_globale(monkeypatch):
    install_fake_db(monkeypatch)
    stats = run(dashboard_service.get_stats(USER))
    assert stats["kpi"]["clients_count"] == 3
    assert stats["kpi"]["revenue_won"] == 3000


def test_get_stats_filtra_per_mandante(monkeypatch):
    install_fake_db(monkeypatch)
    stats = run(dashboard_service.get_stats(USER, mandante_id="m1"))
    # Solo c1 (mandante_ids=[m1]) e c3 (mandante_ids=[m1,m2]) devono contare
    assert stats["kpi"]["clients_count"] == 2
    assert stats["kpi"]["revenue_won"] == 1000
    assert stats["kpi"]["commissions_accrued"] == 100
    assert stats["kpi"]["commissions_collected"] == 0


def test_get_stats_mandante_diverso_da_risultati_diversi(monkeypatch):
    install_fake_db(monkeypatch)
    stats_m1 = run(dashboard_service.get_stats(USER, mandante_id="m1"))
    stats_m2 = run(dashboard_service.get_stats(USER, mandante_id="m2"))
    assert stats_m1["kpi"]["revenue_won"] != stats_m2["kpi"]["revenue_won"]


# ---------- dashboard_service.get_today_brief ----------


def test_get_today_brief_filtra_appuntamenti_per_cliente_del_mandante(monkeypatch):
    install_fake_db(monkeypatch)
    brief_all = run(dashboard_service.get_today_brief(USER))
    brief_m1 = run(dashboard_service.get_today_brief(USER, mandante_id="m1"))
    # Globale: 2 appuntamenti oggi (c1 + c2). Filtrato su m1: solo quello di c1.
    assert brief_all["appointments_today"] == 2
    assert brief_m1["appointments_today"] == 1


def test_get_today_brief_pagamenti_da_verificare_filtrati(monkeypatch):
    install_fake_db(monkeypatch)
    brief_m1 = run(dashboard_service.get_today_brief(USER, mandante_id="m1"))
    brief_m2 = run(dashboard_service.get_today_brief(USER, mandante_id="m2"))
    # Solo la provvigione m1 è "maturato" (da verificare)
    assert brief_m1["payments_to_verify"] == 1
    assert brief_m2["payments_to_verify"] == 0


# ---------- dashboard_service: provvigioni manuali contano come vere ----------

MANUAL_COMMISSIONS = [
    # Senza mandante_id: non attribuibile a un mandante specifico.
    {
        "user_id": "u1",
        "period": "2026-07",
        "amount": 300,
        "mandante_id": None,
        "stato": "maturato",
    },
    # Taggata su m1: deve contare SOLO quando il filtro è m1 (o assente).
    {
        "user_id": "u1",
        "period": "2026-07",
        "amount": 50,
        "mandante_id": "m1",
        "stato": "incassato",
    },
]


def test_get_stats_include_provvigioni_manuali_in_vista_globale(monkeypatch):
    install_fake_db(monkeypatch)
    monkeypatch.setattr(db, "manual_commissions", FakeCollection(MANUAL_COMMISSIONS))
    stats = run(dashboard_service.get_stats(USER))
    # 100 (cm1 maturato) + 300 (manuale senza mandante) = 400
    assert stats["kpi"]["commissions_accrued"] == 400
    # 200 (cm2 incassato) + 50 (manuale m1 incassato) = 250
    assert stats["kpi"]["commissions_collected"] == 250


def test_get_stats_provvigione_manuale_senza_mandante_esclusa_da_filtro_specifico(
    monkeypatch,
):
    install_fake_db(monkeypatch)
    monkeypatch.setattr(db, "manual_commissions", FakeCollection(MANUAL_COMMISSIONS))
    stats = run(dashboard_service.get_stats(USER, mandante_id="m1"))
    # 100 (cm1) — la manuale senza mandante_id NON conta qui
    assert stats["kpi"]["commissions_accrued"] == 100
    # 50 (manuale taggata m1) — la reale cm2 è di m2, non conta qui
    assert stats["kpi"]["commissions_collected"] == 50


def test_get_today_brief_pagamenti_da_verificare_include_manuali(monkeypatch):
    install_fake_db(monkeypatch)
    monkeypatch.setattr(db, "manual_commissions", FakeCollection(MANUAL_COMMISSIONS))
    brief_all = run(dashboard_service.get_today_brief(USER))
    # cm1 (maturato) + la manuale senza mandante (maturato) = 2
    assert brief_all["payments_to_verify"] == 2


# ---------- repository: query costruita correttamente ----------


def test_offer_repository_aggiunge_filtro_mandante_alla_query():
    fake = FakeCollection(OFFERS)
    offer_repository.collection = fake
    run(offer_repository.find_many("u1", mandante_id="m1"))
    assert fake.last_query == {"user_id": "u1", "mandante_id": "m1"}


def test_offer_repository_senza_mandante_non_aggiunge_filtro():
    fake = FakeCollection(OFFERS)
    offer_repository.collection = fake
    run(offer_repository.find_many("u1"))
    assert fake.last_query == {"user_id": "u1"}


def test_order_repository_aggiunge_filtro_mandante_alla_query():
    fake = FakeCollection(ORDERS)
    order_repository.collection = fake
    run(order_repository.find_many("u1", mandante_id="m2"))
    assert fake.last_query == {"user_id": "u1", "mandante_id": "m2"}


def test_commission_repository_aggiunge_filtro_mandante_alla_query():
    fake = FakeCollection(COMMISSIONS)
    commission_repository.collection = fake
    run(commission_repository.find_many("u1", mandante_id="m1"))
    assert fake.last_query == {"user_id": "u1", "mandante_id": "m1"}


def test_client_repository_filtra_su_mandante_ids_array():
    fake = FakeCollection(CLIENTS)
    client_repository.collection = fake
    result = run(client_repository.find_many("u1", {}, mandante_id="m2"))
    ids = {c["id"] for c in result}
    assert ids == {"c2", "c3"}

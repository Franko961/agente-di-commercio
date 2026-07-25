"""
Test per client_service.bulk_import: l'import massivo self-service da
CSV/Excel caricato direttamente dall'utente (parsing già fatto lato
frontend, qui arriva già come lista di ClientBulkItem).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_clients_bulk_import.py -v
"""
import sys
import asyncio

sys.path.insert(0, ".")

from models.client import ClientBulkItem, ClientBulkIn
from services.client_service import ClientService


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class FakeClientRepo:
    def __init__(self, existing=None):
        self.docs = list(existing or [])
        self.inserted_batches = []

    async def find_many(self, user_id, filters, mandante_id=None):
        return [d for d in self.docs if d["user_id"] == user_id]

    async def insert_many(self, docs):
        self.inserted_batches.append(docs)
        self.docs.extend(docs)


class FakeMandanteRepo:
    def __init__(self, mandanti):
        self.mandanti = mandanti

    async def find_many(self, user_id):
        return list(self.mandanti)


USER = {"id": "u1"}
MANDANTI = [
    {"id": "m1", "user_id": "u1", "name": "Rossi Spa"},
    {"id": "m2", "user_id": "u1", "name": "Bianchi Srl"},
]


def build_service(existing_clients=None, mandanti=None):
    repo = FakeClientRepo(existing_clients)
    mandante_repo = FakeMandanteRepo(mandanti if mandanti is not None else MANDANTI)
    return ClientService(repo=repo, mandante_repo=mandante_repo), repo


def _item(**overrides):
    base = dict(company_name="Bar Centrale", city="Bologna", vat_number="", mandante_names="")
    base.update(overrides)
    return ClientBulkItem(**base)


def test_import_semplice_va_a_buon_fine():
    service, repo = build_service()
    payload = ClientBulkIn(clients=[_item(company_name="Bar Centrale"), _item(company_name="Ristorante Roma", city="Roma")])

    result = run(service.bulk_import(USER, payload))

    assert result["imported"] == 2
    assert result["skipped"] == []
    assert len(repo.docs) == 2


def test_deduplica_per_partita_iva_contro_clienti_esistenti():
    existing = [{"id": "c1", "user_id": "u1", "company_name": "Bar Vecchio", "vat_number": "12345678901", "city": "Bologna"}]
    service, repo = build_service(existing_clients=existing)
    payload = ClientBulkIn(clients=[_item(company_name="Bar Vecchio SRL", vat_number="12345678901")])

    result = run(service.bulk_import(USER, payload))

    assert result["imported"] == 0
    assert len(result["skipped"]) == 1
    assert "partita IVA" in result["skipped"][0]["reason"]


def test_deduplica_per_ragione_sociale_e_citta_senza_piva():
    existing = [{"id": "c1", "user_id": "u1", "company_name": "Bar Centrale", "city": "Bologna", "vat_number": ""}]
    service, repo = build_service(existing_clients=existing)
    payload = ClientBulkIn(clients=[_item(company_name="bar centrale", city="BOLOGNA")])  # case diverso, stesso cliente

    result = run(service.bulk_import(USER, payload))

    assert result["imported"] == 0
    assert "città" in result["skipped"][0]["reason"] or "citt" in result["skipped"][0]["reason"]


def test_deduplica_anche_tra_righe_dello_stesso_file():
    service, repo = build_service()
    payload = ClientBulkIn(clients=[
        _item(company_name="Bar Centrale", vat_number="11111111111"),
        _item(company_name="Bar Centrale Srl", vat_number="11111111111"),  # stessa P.IVA, riga duplicata nel file
    ])

    result = run(service.bulk_import(USER, payload))

    assert result["imported"] == 1
    assert len(result["skipped"]) == 1


def test_riga_senza_ragione_sociale_viene_saltata():
    service, repo = build_service()
    payload = ClientBulkIn(clients=[_item(company_name=""), _item(company_name="Valido Srl")])

    result = run(service.bulk_import(USER, payload))

    assert result["imported"] == 1
    assert any("mancante" in s["reason"] for s in result["skipped"])


def test_mandante_risolto_per_nome_case_insensitive():
    service, repo = build_service()
    payload = ClientBulkIn(clients=[_item(company_name="Cliente Test", mandante_names="rossi spa, Bianchi Srl")])

    run(service.bulk_import(USER, payload))

    assert set(repo.docs[0]["mandante_ids"]) == {"m1", "m2"}


def test_mandante_non_trovato_non_blocca_la_riga():
    service, repo = build_service()
    payload = ClientBulkIn(clients=[_item(company_name="Cliente Test", mandante_names="Mandante Inesistente Srl")])

    result = run(service.bulk_import(USER, payload))

    assert result["imported"] == 1
    assert repo.docs[0]["mandante_ids"] == []


def test_insert_avviene_in_batch_non_riga_per_riga():
    service, repo = build_service()
    payload = ClientBulkIn(clients=[_item(company_name=f"Cliente {i}") for i in range(5)])

    run(service.bulk_import(USER, payload))

    # Un'unica chiamata insert_many con tutti i documenti, non 5 insert separati
    assert len(repo.inserted_batches) == 1
    assert len(repo.inserted_batches[0]) == 5

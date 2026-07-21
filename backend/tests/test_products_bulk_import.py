"""
Test per l'importazione in blocco dei prodotti (POST /api/products/bulk),
usata per caricare un listino fornitore (es. da un PDF) in un colpo solo
invece che prodotto per prodotto.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    ANTHROPIC_API_KEY=test python -m pytest test_products_bulk_import.py -v
"""
import sys
import asyncio

sys.path.insert(0, ".")

from fastapi import HTTPException
from services.product_service import ProductService
from models.product import ProductBulkIn, ProductBulkItem


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class FakeProductRepo:
    def __init__(self):
        self.docs = []

    async def find_many(self, user_id, mandante_id=None):
        results = [d for d in self.docs if d["user_id"] == user_id]
        if mandante_id:
            results = [d for d in results if d["mandante_id"] == mandante_id]
        return results

    async def insert_many(self, docs):
        self.docs.extend(docs)


class FakeMandanteRepo:
    def __init__(self, mandante):
        self.mandante = mandante

    async def find_by_name_regex(self, user_id, name):
        if name and name.lower() in self.mandante["name"].lower():
            return self.mandante
        return None


def build_service():
    mandante = {"id": "m-1", "user_id": "user-1", "name": "PagineSì!"}
    product_repo = FakeProductRepo()
    mandante_repo = FakeMandanteRepo(mandante)
    service = ProductService(repo=product_repo, mandante_repo=mandante_repo)
    return service, product_repo, mandante


FAKE_USER = {"id": "user-1"}


def _payload(items):
    return ProductBulkIn(
        mandante_name="PagineSì!",
        products=[ProductBulkItem(**i) for i in items],
    )


def test_importa_prodotti_nuovi_correttamente():
    service, product_repo, mandante = build_service()
    payload = _payload([
        {"sku": "AI-ADISET", "name": "Assistente Digitale Intelligente set", "price": 1118, "category": "Intelligenza Artificiale"},
        {"sku": "GBP", "name": "Scheda Google Business Profile", "price": 211, "category": "Google Business Profile"},
    ])

    result = run(service.bulk_import(FAKE_USER, payload))

    assert result["imported"] == 2
    assert result["skipped_existing"] == 0
    assert result["mandante_id"] == "m-1"
    assert len(product_repo.docs) == 2
    assert product_repo.docs[0]["mandante_id"] == "m-1"
    assert product_repo.docs[0]["user_id"] == "user-1"


def test_mandante_non_trovato_solleva_404():
    service, product_repo, mandante = build_service()
    payload = ProductBulkIn(
        mandante_name="Fornitore Inesistente",
        products=[ProductBulkItem(sku="X", name="Y", price=10)],
    )

    try:
        run(service.bulk_import(FAKE_USER, payload))
        assert False, "doveva sollevare HTTPException"
    except HTTPException as e:
        assert e.status_code == 404
    assert len(product_repo.docs) == 0


def test_reimportare_gli_stessi_sku_non_crea_doppioni():
    """L'endpoint deve essere idempotente: richiamarlo due volte con lo
    stesso listino non deve duplicare i prodotti già presenti."""
    service, product_repo, mandante = build_service()
    payload = _payload([
        {"sku": "AI-ADISET", "name": "Assistente Digitale Intelligente set", "price": 1118, "category": "Intelligenza Artificiale"},
    ])

    run(service.bulk_import(FAKE_USER, payload))
    result2 = run(service.bulk_import(FAKE_USER, payload))

    assert result2["imported"] == 0
    assert result2["skipped_existing"] == 1
    assert "AI-ADISET" in result2["skipped_skus"]
    assert len(product_repo.docs) == 1  # non duplicato


def test_import_parziale_salta_solo_gli_sku_gia_presenti():
    service, product_repo, mandante = build_service()
    run(service.bulk_import(FAKE_USER, _payload([
        {"sku": "GBP", "name": "Scheda Google Business Profile", "price": 211},
    ])))

    result = run(service.bulk_import(FAKE_USER, _payload([
        {"sku": "GBP", "name": "Scheda Google Business Profile", "price": 211},
        {"sku": "GBPM", "name": "Scheda Google Business Profile Mantenim.", "price": 211},
    ])))

    assert result["imported"] == 1
    assert result["skipped_existing"] == 1
    assert len(product_repo.docs) == 2


def test_prodotti_di_un_altro_utente_non_influenzano_lo_sku_check():
    service, product_repo, mandante = build_service()
    # Prodotto con lo stesso sku ma di un altro utente: non deve bloccare
    # l'import per l'utente corrente.
    product_repo.docs.append({
        "id": "p-other", "user_id": "user-2", "mandante_id": "m-1",
        "sku": "GBP", "name": "...", "price": 211, "category": "",
    })

    result = run(service.bulk_import(FAKE_USER, _payload([
        {"sku": "GBP", "name": "Scheda Google Business Profile", "price": 211},
    ])))

    assert result["imported"] == 1


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))

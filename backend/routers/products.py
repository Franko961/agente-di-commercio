from typing import Optional

from fastapi import APIRouter, Depends

from core.security import forbid_demo_write, get_current_user, require_module
from models.product import ProductBulkIn, ProductIn
from services.product_service import product_service

router = APIRouter(prefix="/api/products", tags=["products"])

# Solo le scritture legate al modulo "prodotti": la lettura resta sempre
# disponibile perché Offerte e Ordini usano il listino per comporre le
# righe — bloccarla romperebbe quelle pagine anche quando non è
# "Prodotti & Listini" il modulo disattivato.
MODULE_DEP = Depends(require_module("prodotti"))


@router.get("")
async def list_products(
    mandante_id: Optional[str] = None, user=Depends(get_current_user)
):
    return await product_service.list_products(user, mandante_id)


@router.post("", dependencies=[MODULE_DEP])
async def create_product(payload: ProductIn, user=Depends(forbid_demo_write)):
    return await product_service.create_product(user, payload)


@router.post("/bulk", dependencies=[MODULE_DEP])
async def bulk_import_products(payload: ProductBulkIn, user=Depends(forbid_demo_write)):
    """Importa in blocco un listino prodotti (es. da un PDF/Excel fornitore)
    per un mandante esistente, risolto per nome. Idempotente per sku: le
    voci già presenti per quel mandante vengono saltate, non duplicate."""
    return await product_service.bulk_import(user, payload)


@router.put("/{pid}", dependencies=[MODULE_DEP])
async def update_product(pid: str, payload: ProductIn, user=Depends(forbid_demo_write)):
    await product_service.update_product(user, pid, payload)
    return {"ok": True}


@router.delete("/{pid}", dependencies=[MODULE_DEP])
async def delete_product(pid: str, user=Depends(forbid_demo_write)):
    await product_service.delete_product(user, pid)
    return {"ok": True}

from fastapi import APIRouter, Depends
from typing import Optional
from core.security import get_current_user
from services.product_service import product_service
from models.product import ProductIn

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("")
async def list_products(mandante_id: Optional[str] = None, user=Depends(get_current_user)):
    return await product_service.list_products(user, mandante_id)


@router.post("")
async def create_product(payload: ProductIn, user=Depends(get_current_user)):
    return await product_service.create_product(user, payload)


@router.put("/{pid}")
async def update_product(pid: str, payload: ProductIn, user=Depends(get_current_user)):
    await product_service.update_product(user, pid, payload)
    return {"ok": True}


@router.delete("/{pid}")
async def delete_product(pid: str, user=Depends(get_current_user)):
    await product_service.delete_product(user, pid)
    return {"ok": True}

from fastapi import APIRouter, Depends, Body
from typing import Optional
from core.security import get_current_user, forbid_demo_write
from services.order_service import order_service
from models.order import OrderIn, OrderStatusIn

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("")
async def list_orders(mandante_id: Optional[str] = None, user=Depends(get_current_user)):
    return await order_service.list_orders(user, mandante_id)


@router.get("/client/{client_id}")
async def list_orders_by_client(client_id: str, user=Depends(get_current_user)):
    return await order_service.list_orders_by_client(user, client_id)


@router.get("/{oid}")
async def get_order(oid: str, user=Depends(get_current_user)):
    return await order_service.get_order(user, oid)


@router.post("")
async def create_order(payload: OrderIn, user=Depends(get_current_user)):
    return await order_service.create_order(user, payload)


@router.put("/{oid}")
async def update_order(oid: str, payload: OrderIn, user=Depends(get_current_user)):
    await order_service.update_order(user, oid, payload)
    return {"ok": True}


@router.patch("/{oid}/status")
async def update_order_status(oid: str, payload: OrderStatusIn, user=Depends(get_current_user)):
    await order_service.update_order_status(user, oid, payload)
    return {"ok": True}


@router.delete("/{oid}")
async def delete_order(oid: str, user=Depends(forbid_demo_write)):
    await order_service.delete_order(user, oid)
    return {"ok": True}

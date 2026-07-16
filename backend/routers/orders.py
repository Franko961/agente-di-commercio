from fastapi import APIRouter, Depends
from core.security import get_current_user, forbid_demo_write
from services.order_service import order_service
from models.order import OrderIn

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("")
async def list_orders(user=Depends(get_current_user)):
    return await order_service.list_orders(user)


@router.get("/client/{client_id}")
async def list_orders_by_client(client_id: str, user=Depends(get_current_user)):
    return await order_service.list_orders_by_client(user, client_id)


@router.post("")
async def create_order(payload: OrderIn, user=Depends(get_current_user)):
    return await order_service.create_order(user, payload)


@router.delete("/{oid}")
async def delete_order(oid: str, user=Depends(forbid_demo_write)):
    await order_service.delete_order(user, oid)
    return {"ok": True}

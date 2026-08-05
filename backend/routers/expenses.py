from fastapi import APIRouter, Depends
from typing import Optional
from core.security import get_current_user, forbid_demo_write, require_module
from services.expense_service import expense_service
from models.expense import ExpenseIn

router = APIRouter(prefix="/api/expenses", tags=["expenses"], dependencies=[Depends(require_module("spese"))])


@router.get("")
async def list_expenses(
    category: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user=Depends(get_current_user),
):
    return await expense_service.list_expenses(user, category, date_from, date_to)


@router.post("")
async def create_expense(payload: ExpenseIn, user=Depends(forbid_demo_write)):
    return await expense_service.create_expense(user, payload)


@router.put("/{eid}")
async def update_expense(eid: str, payload: ExpenseIn, user=Depends(forbid_demo_write)):
    await expense_service.update_expense(user, eid, payload)
    return {"ok": True}


@router.delete("/{eid}")
async def delete_expense(eid: str, user=Depends(forbid_demo_write)):
    await expense_service.delete_expense(user, eid)
    return {"ok": True}

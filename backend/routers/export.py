from fastapi import APIRouter, Depends
from core.security import get_current_user
from services.export_service import export_service

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/clients.csv")
async def export_clients(user=Depends(get_current_user)):
    return await export_service.export_clients(user)


@router.get("/offers.csv")
async def export_offers(user=Depends(get_current_user)):
    return await export_service.export_offers(user)


@router.get("/commissions.csv")
async def export_commissions(user=Depends(get_current_user)):
    return await export_service.export_commissions(user)


@router.get("/leads.csv")
async def export_leads(user=Depends(get_current_user)):
    return await export_service.export_leads(user)

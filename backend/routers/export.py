from typing import Optional

from fastapi import APIRouter, Depends

from core.security import get_current_user, require_module
from services.export_service import export_service

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/clients.csv", dependencies=[Depends(require_module("clienti"))])
async def export_clients(user=Depends(get_current_user)):
    return await export_service.export_clients(user)


@router.get("/offers.csv", dependencies=[Depends(require_module("offerte"))])
async def export_offers(user=Depends(get_current_user)):
    return await export_service.export_offers(user)


@router.get("/commissions.csv", dependencies=[Depends(require_module("provvigioni"))])
async def export_commissions(user=Depends(get_current_user)):
    return await export_service.export_commissions(user)


@router.get("/leads.csv", dependencies=[Depends(require_module("lead"))])
async def export_leads(user=Depends(get_current_user)):
    return await export_service.export_leads(user)


@router.get(
    "/mandante-report.pdf", dependencies=[Depends(require_module("provvigioni"))]
)
async def export_mandante_report(
    mandante_id: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user=Depends(get_current_user),
):
    return await export_service.export_mandante_report(
        user, mandante_id, date_from, date_to
    )

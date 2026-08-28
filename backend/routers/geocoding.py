from fastapi import APIRouter, Depends, Query

from core.security import get_current_user
from services.geocoding_service import geocoding_service

router = APIRouter(prefix="/api/geocode", tags=["geocode"])


@router.get("")
async def search_address(
    q: str = Query(..., min_length=3), user=Depends(get_current_user)
):
    return await geocoding_service.search_address(user["id"], q)

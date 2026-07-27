from fastapi import APIRouter, Depends, HTTPException
from core.security import get_current_user
from core.rate_limit import check_and_record
from services.route_optimization_service import route_optimization_service
from models.route_planning import RoutePlanIn

router = APIRouter(prefix="/api/route-planning", tags=["route-planning"])


@router.post("/optimize")
async def optimize_route(payload: RoutePlanIn, user=Depends(get_current_user)):
    # Protegge la chiamata esterna a OpenRouteService (piano gratuito, quota
    # giornaliera limitata) da un uso eccessivo — stesso principio già
    # applicato alla ricerca indirizzi in geocoding_service.
    allowed = await check_and_record("route_optimize", user["id"], max_attempts=20, window_minutes=10)
    if not allowed:
        raise HTTPException(429, "Troppe richieste di pianificazione giro in poco tempo, riprova tra qualche minuto")
    return await route_optimization_service.plan_day(
        user, payload.client_ids, payload.start_time, payload.visit_minutes,
        payload.start_mode, payload.start_lat, payload.start_lng, payload.round_trip,
    )

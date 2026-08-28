import logging

import requests
from fastapi import HTTPException

from core.rate_limit import check_and_record

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# Nominatim (il servizio di geocodifica gratuito di OpenStreetMap, già la
# fonte delle mappe usate in MapView.jsx) richiede un User-Agent descrittivo
# per il rispetto della loro politica di uso equo del servizio gratuito —
# niente chiave API, ma niente abusi neanche da parte nostra.
_USER_AGENT = "SalesflyCRM/1.0 (gestionale per agenti di commercio)"


class GeocodingService:
    async def search_address(self, user_id: str, query: str) -> list:
        query = (query or "").strip()
        if len(query) < 3:
            raise HTTPException(400, "Indirizzo troppo corto per la ricerca")

        # Limite per utente (non globale): un agente che digita un indirizzo
        # per cliente non si avvicina mai a questa soglia in condizioni
        # normali; serve solo a restare entro l'uso equo del servizio gratuito.
        allowed = await check_and_record(
            "geocode", user_id, max_attempts=30, window_minutes=10
        )
        if not allowed:
            raise HTTPException(
                429,
                "Troppe ricerche indirizzo in poco tempo, riprova tra qualche minuto",
            )

        try:
            resp = requests.get(
                NOMINATIM_URL,
                params={"format": "json", "q": query, "limit": 5, "countrycodes": "it"},
                headers={"User-Agent": _USER_AGENT},
                timeout=8,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"geocoding: errore chiamata Nominatim: {e}")
            raise HTTPException(
                502,
                "Servizio di ricerca indirizzi non disponibile al momento, riprova più tardi",
            )

        try:
            results = resp.json()
        except ValueError:
            return []

        return [
            {
                "display_name": r.get("display_name", ""),
                "lat": float(r["lat"]),
                "lng": float(r["lon"]),
            }
            for r in results
            if r.get("lat") and r.get("lon")
        ]


geocoding_service = GeocodingService()

"""
Verifica che ClientIn rifiuti coordinate geograficamente impossibili
(lat fuori da -90/90, lng fuori da -180/180). Senza questo vincolo, una
coordinata corrotta (es. invertita da un match di geocodifica sbagliato)
poteva essere salvata e mandare in crash "Out of Memory" il browser quando
Leaflet provava a renderla su una mappa (LocationPicker.jsx/MapView.jsx) —
bug reale osservato in produzione.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_client_coordinates_validation.py -v
"""
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, ".")

from models.client import ClientIn


def _base(**overrides):
    payload = {"company_name": "Cliente Test", **overrides}
    return payload


def test_coordinate_valide_accettate():
    c = ClientIn(**_base(lat=42.75, lng=13.95))
    assert c.lat == 42.75
    assert c.lng == 13.95


def test_nessuna_coordinata_accettata():
    c = ClientIn(**_base())
    assert c.lat is None
    assert c.lng is None


@pytest.mark.parametrize("lat", [90.1, -90.1, 999.0, -999.0])
def test_latitudine_fuori_dai_limiti_rifiutata(lat):
    with pytest.raises(ValidationError):
        ClientIn(**_base(lat=lat, lng=13.0))


@pytest.mark.parametrize("lng", [180.1, -180.1, 999.0, -999.0])
def test_longitudine_fuori_dai_limiti_rifiutata(lng):
    with pytest.raises(ValidationError):
        ClientIn(**_base(lat=42.0, lng=lng))


def test_limiti_esatti_accettati():
    """I valori esattamente ai bordi (90/-90, 180/-180) sono geograficamente
    validi (i poli, l'antimeridiano) e devono essere accettati."""
    c = ClientIn(**_base(lat=90.0, lng=180.0))
    assert c.lat == 90.0
    assert c.lng == 180.0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

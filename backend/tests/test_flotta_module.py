"""
Verifica il modulo "Flotta" (services/vehicle_service.py +
vehicle_deadline_service.py + vehicle_cost_service.py +
cargo_load_service.py): anagrafica mezzi, scadenze documentali, storico
costi e carico merce per account come CACI SRL.

Copre:
- create_vehicle salva il mezzo con active=True; set_active lo
  disattiva/riattiva; update_vehicle aggiorna i campi.
- create_deadline/create_cost/create_load denormalizzano vehicle_plate
  (resta leggibile anche se il mezzo viene poi eliminato) e rifiutano un
  vehicle_id che non appartiene all'utente (o inesistente).
- I modelli pydantic rifiutano date non valide (stesso principio già
  applicato a LeaveRequestIn) e importi <= 0 per i costi.
- Ogni risorsa è scoped per utente: un utente non vede/non può
  modificare le risorse di un altro.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_flotta_module.py -v
"""
import sys
import asyncio

import pytest
from pydantic import ValidationError

sys.path.insert(0, ".")

from core.exceptions import NotFoundError, ValidationAppError
from models.vehicle import VehicleIn, VehicleDeadlineIn, VehicleCostIn, CargoLoadIn
from services.vehicle_service import VehicleService
from services.vehicle_deadline_service import VehicleDeadlineService
from services.vehicle_cost_service import VehicleCostService
from services.cargo_load_service import CargoLoadService


def run(coro):
    return asyncio.run(coro)


USER = {"id": "user-1", "email": "manager@example.com"}
ALTRO_USER = {"id": "user-2", "email": "altro@example.com"}


class FakeVehicleRepo:
    def __init__(self):
        self.docs = {}

    async def find_many(self, user_id):
        return [d for d in self.docs.values() if d["user_id"] == user_id]

    async def find_one(self, vid, user_id):
        d = self.docs.get(vid)
        return d if d and d["user_id"] == user_id else None

    async def insert(self, doc):
        self.docs[doc["id"]] = dict(doc)
        return doc

    async def update(self, vid, user_id, data):
        d = self.docs.get(vid)
        if not d or d["user_id"] != user_id:
            return False
        d.update(data)
        return True

    async def delete(self, vid, user_id):
        d = self.docs.get(vid)
        if d and d["user_id"] == user_id:
            del self.docs[vid]


class FakeDetailRepo:
    """Fake generico per deadline/cost/cargo: stessa forma in tutti e tre."""
    def __init__(self):
        self.docs = {}

    async def find_many(self, user_id):
        return [d for d in self.docs.values() if d["user_id"] == user_id]

    async def find_one(self, rid, user_id):
        d = self.docs.get(rid)
        return d if d and d["user_id"] == user_id else None

    async def insert(self, doc):
        self.docs[doc["id"]] = dict(doc)
        return doc

    async def update(self, rid, user_id, data):
        d = self.docs.get(rid)
        if not d or d["user_id"] != user_id:
            return False
        d.update(data)
        return True

    async def delete(self, rid, user_id):
        d = self.docs.get(rid)
        if d and d["user_id"] == user_id:
            del self.docs[rid]


def make_vehicle(plate="AB123CD", **overrides):
    return VehicleIn(
        plate=plate,
        model=overrides.get("model", "Fiat Ducato"),
        type=overrides.get("type", "furgone"),
        assigned_driver=overrides.get("assigned_driver", ""),
        notes=overrides.get("notes", ""),
    )


def build_vehicle_service():
    repo = FakeVehicleRepo()
    return VehicleService(repo=repo), repo


# ---------- vehicle_service ----------

def test_create_vehicle_e_attivo_di_default():
    service, repo = build_vehicle_service()
    v = run(service.create_vehicle(USER, make_vehicle()))
    assert v["active"] is True
    assert v["user_id"] == USER["id"]
    assert v["plate"] == "AB123CD"


def test_update_vehicle_aggiorna_i_campi():
    service, repo = build_vehicle_service()
    v = run(service.create_vehicle(USER, make_vehicle()))
    run(service.update_vehicle(USER, v["id"], make_vehicle(plate="AB123CD", model="Iveco Daily")))
    assert repo.docs[v["id"]]["model"] == "Iveco Daily"


def test_update_vehicle_rifiuta_mezzo_di_un_altro_utente():
    service, repo = build_vehicle_service()
    v = run(service.create_vehicle(USER, make_vehicle()))
    with pytest.raises(NotFoundError):
        run(service.update_vehicle(ALTRO_USER, v["id"], make_vehicle()))


def test_set_active_disattiva_e_riattiva():
    service, repo = build_vehicle_service()
    v = run(service.create_vehicle(USER, make_vehicle()))
    run(service.set_active(USER, v["id"], False))
    assert repo.docs[v["id"]]["active"] is False
    run(service.set_active(USER, v["id"], True))
    assert repo.docs[v["id"]]["active"] is True


def test_delete_vehicle_rimuove_solo_il_proprio():
    service, repo = build_vehicle_service()
    v = run(service.create_vehicle(USER, make_vehicle()))
    run(service.delete_vehicle(ALTRO_USER, v["id"]))
    assert v["id"] in repo.docs  # non cancellato: apparteneva a un altro utente
    run(service.delete_vehicle(USER, v["id"]))
    assert v["id"] not in repo.docs


# ---------- vehicle_deadline_service ----------

def build_deadline_service(vehicle_repo):
    repo = FakeDetailRepo()
    return VehicleDeadlineService(repo=repo, vehicles=vehicle_repo), repo


def test_create_deadline_denormalizza_la_targa():
    vservice, vrepo = build_vehicle_service()
    vehicle = run(vservice.create_vehicle(USER, make_vehicle("XY999ZZ")))
    service, repo = build_deadline_service(vrepo)

    d = run(service.create_deadline(USER, VehicleDeadlineIn(
        vehicle_id=vehicle["id"], type="assicurazione", due_date="2026-12-01",
    )))
    assert d["vehicle_plate"] == "XY999ZZ"
    assert d["due_date"] == "2026-12-01"


def test_create_deadline_rifiuta_mezzo_inesistente():
    vservice, vrepo = build_vehicle_service()
    service, repo = build_deadline_service(vrepo)
    with pytest.raises(ValidationAppError):
        run(service.create_deadline(USER, VehicleDeadlineIn(
            vehicle_id="non-esiste", type="revisione", due_date="2026-12-01",
        )))


def test_create_deadline_rifiuta_mezzo_di_un_altro_utente():
    vservice, vrepo = build_vehicle_service()
    vehicle = run(vservice.create_vehicle(ALTRO_USER, make_vehicle()))
    service, repo = build_deadline_service(vrepo)
    with pytest.raises(ValidationAppError):
        run(service.create_deadline(USER, VehicleDeadlineIn(
            vehicle_id=vehicle["id"], type="bollo", due_date="2026-12-01",
        )))


@pytest.mark.parametrize("due_date", ["2026-99-99", "2026-02-31", "test", "2026-8-2"])
def test_vehicle_deadline_in_rifiuta_date_non_valide(due_date):
    with pytest.raises(ValidationError):
        VehicleDeadlineIn(vehicle_id="qualsiasi", type="bollo", due_date=due_date)


def test_delete_deadline_resta_leggibile_dopo_eliminazione_mezzo():
    """La scadenza non viene cancellata a cascata quando il mezzo viene
    eliminato: vehicle_plate denormalizzato la rende comunque leggibile."""
    vservice, vrepo = build_vehicle_service()
    vehicle = run(vservice.create_vehicle(USER, make_vehicle("ZZ111AA")))
    service, repo = build_deadline_service(vrepo)
    d = run(service.create_deadline(USER, VehicleDeadlineIn(
        vehicle_id=vehicle["id"], type="revisione", due_date="2026-12-01",
    )))
    run(vservice.delete_vehicle(USER, vehicle["id"]))
    assert repo.docs[d["id"]]["vehicle_plate"] == "ZZ111AA"


# ---------- vehicle_cost_service ----------

def build_cost_service(vehicle_repo):
    repo = FakeDetailRepo()
    return VehicleCostService(repo=repo, vehicles=vehicle_repo), repo


def test_create_cost_denormalizza_la_targa_e_salva_importo():
    vservice, vrepo = build_vehicle_service()
    vehicle = run(vservice.create_vehicle(USER, make_vehicle("CO123ST")))
    service, repo = build_cost_service(vrepo)
    c = run(service.create_cost(USER, VehicleCostIn(
        vehicle_id=vehicle["id"], category="carburante", amount=45.5, date="2026-08-01",
    )))
    assert c["vehicle_plate"] == "CO123ST"
    assert c["amount"] == 45.5


def test_create_cost_rifiuta_mezzo_inesistente():
    vservice, vrepo = build_vehicle_service()
    service, repo = build_cost_service(vrepo)
    with pytest.raises(ValidationAppError):
        run(service.create_cost(USER, VehicleCostIn(
            vehicle_id="non-esiste", category="manutenzione", amount=100, date="2026-08-01",
        )))


def test_vehicle_cost_in_rifiuta_importo_non_positivo():
    with pytest.raises(ValidationError):
        VehicleCostIn(vehicle_id="qualsiasi", category="carburante", amount=0, date="2026-08-01")
    with pytest.raises(ValidationError):
        VehicleCostIn(vehicle_id="qualsiasi", category="carburante", amount=-10, date="2026-08-01")


# ---------- cargo_load_service ----------

def build_cargo_service(vehicle_repo):
    repo = FakeDetailRepo()
    return CargoLoadService(repo=repo, vehicles=vehicle_repo), repo


def test_create_load_denormalizza_la_targa():
    vservice, vrepo = build_vehicle_service()
    vehicle = run(vservice.create_vehicle(USER, make_vehicle("LO456AD")))
    service, repo = build_cargo_service(vrepo)
    load = run(service.create_load(USER, CargoLoadIn(
        vehicle_id=vehicle["id"], date="2026-08-05", description="Pallet materiali edili",
        destination="Cantiere Milano Nord",
    )))
    assert load["vehicle_plate"] == "LO456AD"
    assert load["destination"] == "Cantiere Milano Nord"


def test_create_load_rifiuta_mezzo_di_un_altro_utente():
    vservice, vrepo = build_vehicle_service()
    vehicle = run(vservice.create_vehicle(ALTRO_USER, make_vehicle()))
    service, repo = build_cargo_service(vrepo)
    with pytest.raises(ValidationAppError):
        run(service.create_load(USER, CargoLoadIn(
            vehicle_id=vehicle["id"], date="2026-08-05", description="Carico test",
        )))


def test_update_load_rifiuta_carico_di_un_altro_utente():
    """ALTRO_USER passa un proprio mezzo valido (il controllo di
    ownership sul vehicle_id supera), ma il carico stesso appartiene a
    USER: deve comunque essere rifiutato."""
    vservice, vrepo = build_vehicle_service()
    vehicle = run(vservice.create_vehicle(USER, make_vehicle()))
    altro_vehicle = run(vservice.create_vehicle(ALTRO_USER, make_vehicle("AL999TR")))
    service, repo = build_cargo_service(vrepo)
    load = run(service.create_load(USER, CargoLoadIn(
        vehicle_id=vehicle["id"], date="2026-08-05", description="Carico originale",
    )))
    with pytest.raises(NotFoundError):
        run(service.update_load(ALTRO_USER, load["id"], CargoLoadIn(
            vehicle_id=altro_vehicle["id"], date="2026-08-06", description="Modificato",
        )))

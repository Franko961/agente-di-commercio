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
from models.vehicle import VehicleIn, VehicleDeadlineIn, VehicleCostIn, CargoLoadIn, CargoLoadSign
from services.vehicle_service import VehicleService
from services.vehicle_deadline_service import VehicleDeadlineService
from services.vehicle_cost_service import VehicleCostService
from services.cargo_load_service import CargoLoadService
from services.expense_service import ExpenseService
from models.expense import ExpenseIn


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

    async def find_by_plate(self, plate, user_id):
        for d in self.docs.values():
            if d["plate"] == plate and d["user_id"] == user_id:
                return d
        return None


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

    async def sign(self, rid, user_id, signature, signer_name, signed_at):
        d = self.docs.get(rid)
        if not d or d["user_id"] != user_id:
            return False
        d.update({"signature": signature, "signer_name": signer_name, "signed_at": signed_at, "status": "consegnato"})
        return True


class FakeExpenseRepo:
    def __init__(self):
        self.docs = {}

    async def find_one(self, eid, user_id):
        d = self.docs.get(eid)
        return d if d and d["user_id"] == user_id else None

    async def insert(self, doc):
        self.docs[doc["id"]] = dict(doc)
        return doc

    async def update(self, eid, user_id, data):
        d = self.docs.get(eid)
        if d and d["user_id"] == user_id:
            d.update(data)

    async def delete(self, eid, user_id):
        d = self.docs.get(eid)
        if d and d["user_id"] == user_id:
            del self.docs[eid]


class FakeRefRepo:
    """Fake generico find_one su una lista di dict — usato per client/order
    nei test di cargo_load_service (link facoltativi)."""
    def __init__(self, docs=None):
        self.docs = docs or []

    async def find_one(self, doc_id, user_id):
        for d in self.docs:
            if d["id"] == doc_id and d["user_id"] == user_id:
                return d
        return None


def make_vehicle(plate="AB123CD", **overrides):
    return VehicleIn(
        plate=plate,
        model=overrides.get("model", "Fiat Ducato"),
        type=overrides.get("type", "furgone"),
        assigned_driver=overrides.get("assigned_driver", ""),
        notes=overrides.get("notes", ""),
        assigned_employee_id=overrides.get("assigned_employee_id"),
        current_km=overrides.get("current_km"),
    )


def build_vehicle_service(employees=None):
    repo = FakeVehicleRepo()
    return VehicleService(repo=repo, employees=employees or FakeRefRepo()), repo


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


@pytest.mark.parametrize("raw,expected", [
    ("ab123cd", "AB123CD"),
    ("AB 123 CD", "AB123CD"),
    ("ab-123-cd", "AB123CD"),
])
def test_create_vehicle_normalizza_la_targa(raw, expected):
    service, repo = build_vehicle_service()
    v = run(service.create_vehicle(USER, make_vehicle(plate=raw)))
    assert v["plate"] == expected


def test_create_vehicle_rifiuta_targa_duplicata_per_lo_stesso_utente():
    service, repo = build_vehicle_service()
    run(service.create_vehicle(USER, make_vehicle("AB123CD")))
    with pytest.raises(ValidationAppError):
        run(service.create_vehicle(USER, make_vehicle("ab 123-cd")))  # normalizza alla stessa targa


def test_create_vehicle_permette_targa_duplicata_tra_utenti_diversi():
    service, repo = build_vehicle_service()
    run(service.create_vehicle(USER, make_vehicle("AB123CD")))
    v2 = run(service.create_vehicle(ALTRO_USER, make_vehicle("AB123CD")))
    assert v2["plate"] == "AB123CD"


def test_update_vehicle_rifiuta_targa_duplicata_di_un_altro_mezzo():
    service, repo = build_vehicle_service()
    run(service.create_vehicle(USER, make_vehicle("AB123CD")))
    v2 = run(service.create_vehicle(USER, make_vehicle("XY999ZZ")))
    with pytest.raises(ValidationAppError):
        run(service.update_vehicle(USER, v2["id"], make_vehicle("AB123CD")))


def test_update_vehicle_permette_di_salvare_la_propria_stessa_targa():
    service, repo = build_vehicle_service()
    v = run(service.create_vehicle(USER, make_vehicle("AB123CD")))
    run(service.update_vehicle(USER, v["id"], make_vehicle("AB123CD", model="Nuovo modello")))
    assert repo.docs[v["id"]]["model"] == "Nuovo modello"


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


# ---------- vehicle_cost_service (+ sync su Spese) ----------

def build_cost_service(vehicle_repo, expense_repo=None):
    repo = FakeDetailRepo()
    expenses = expense_repo if expense_repo is not None else FakeExpenseRepo()
    return VehicleCostService(repo=repo, vehicles=vehicle_repo, expenses=expenses), repo, expenses


def test_create_cost_denormalizza_la_targa_e_salva_importo():
    vservice, vrepo = build_vehicle_service()
    vehicle = run(vservice.create_vehicle(USER, make_vehicle("CO123ST")))
    service, repo, expenses = build_cost_service(vrepo)
    c = run(service.create_cost(USER, VehicleCostIn(
        vehicle_id=vehicle["id"], category="carburante", amount=45.5, date="2026-08-01",
    )))
    assert c["vehicle_plate"] == "CO123ST"
    assert c["amount"] == 45.5


def test_create_cost_rifiuta_mezzo_inesistente():
    vservice, vrepo = build_vehicle_service()
    service, repo, expenses = build_cost_service(vrepo)
    with pytest.raises(ValidationAppError):
        run(service.create_cost(USER, VehicleCostIn(
            vehicle_id="non-esiste", category="manutenzione", amount=100, date="2026-08-01",
        )))


def test_vehicle_cost_in_rifiuta_importo_non_positivo():
    with pytest.raises(ValidationError):
        VehicleCostIn(vehicle_id="qualsiasi", category="carburante", amount=0, date="2026-08-01")
    with pytest.raises(ValidationError):
        VehicleCostIn(vehicle_id="qualsiasi", category="carburante", amount=-10, date="2026-08-01")


def test_create_cost_genera_una_spesa_collegata():
    vservice, vrepo = build_vehicle_service()
    vehicle = run(vservice.create_vehicle(USER, make_vehicle("CO123ST")))
    service, repo, expenses = build_cost_service(vrepo)
    c = run(service.create_cost(USER, VehicleCostIn(
        vehicle_id=vehicle["id"], category="carburante", amount=45.5, date="2026-08-01", description="Pieno diesel",
    )))
    assert c["expense_id"] in expenses.docs
    expense = expenses.docs[c["expense_id"]]
    assert expense["source"] == "flotta"
    assert expense["vehicle_cost_id"] == c["id"]
    assert expense["amount"] == 45.5
    assert expense["category"] == "carburante"  # mappatura diretta
    assert "CO123ST" in expense["description"]


def test_create_cost_categoria_non_carburante_mappa_su_altro():
    vservice, vrepo = build_vehicle_service()
    vehicle = run(vservice.create_vehicle(USER, make_vehicle()))
    service, repo, expenses = build_cost_service(vrepo)
    c = run(service.create_cost(USER, VehicleCostIn(
        vehicle_id=vehicle["id"], category="manutenzione", amount=150, date="2026-08-01",
    )))
    assert expenses.docs[c["expense_id"]]["category"] == "altro"


def test_update_cost_sincronizza_la_spesa_collegata():
    vservice, vrepo = build_vehicle_service()
    vehicle = run(vservice.create_vehicle(USER, make_vehicle("CO123ST")))
    service, repo, expenses = build_cost_service(vrepo)
    c = run(service.create_cost(USER, VehicleCostIn(
        vehicle_id=vehicle["id"], category="carburante", amount=45.5, date="2026-08-01",
    )))
    run(service.update_cost(USER, c["id"], VehicleCostIn(
        vehicle_id=vehicle["id"], category="manutenzione", amount=200, date="2026-08-02", description="Tagliando",
    )))
    expense = expenses.docs[c["expense_id"]]
    assert expense["amount"] == 200
    assert expense["date"] == "2026-08-02"
    assert expense["category"] == "altro"
    assert "Tagliando" in expense["description"]


def test_delete_cost_elimina_anche_la_spesa_collegata():
    vservice, vrepo = build_vehicle_service()
    vehicle = run(vservice.create_vehicle(USER, make_vehicle()))
    service, repo, expenses = build_cost_service(vrepo)
    c = run(service.create_cost(USER, VehicleCostIn(
        vehicle_id=vehicle["id"], category="carburante", amount=45.5, date="2026-08-01",
    )))
    expense_id = c["expense_id"]
    run(service.delete_cost(USER, c["id"]))
    assert c["id"] not in repo.docs
    assert expense_id not in expenses.docs


def test_create_cost_rollback_spesa_se_insert_costo_fallisce():
    # Niente transazione Mongo sul flusso a due scritture (insert spesa,
    # poi insert costo): senza rollback esplicito, un fallimento qui
    # lascerebbe la spesa orfana per sempre — vedi services/reconciliation_service.py.
    vservice, vrepo = build_vehicle_service()
    vehicle = run(vservice.create_vehicle(USER, make_vehicle()))
    service, repo, expenses = build_cost_service(vrepo)

    async def failing_insert(doc):
        raise RuntimeError("scrittura del costo fallita")
    repo.insert = failing_insert

    with pytest.raises(RuntimeError):
        run(service.create_cost(USER, VehicleCostIn(
            vehicle_id=vehicle["id"], category="carburante", amount=45.5, date="2026-08-01",
        )))
    assert expenses.docs == {}


def test_expense_service_rifiuta_modifica_di_una_spesa_generata_da_flotta():
    vservice, vrepo = build_vehicle_service()
    vehicle = run(vservice.create_vehicle(USER, make_vehicle()))
    cost_service, cost_repo, expenses = build_cost_service(vrepo)
    c = run(cost_service.create_cost(USER, VehicleCostIn(
        vehicle_id=vehicle["id"], category="carburante", amount=45.5, date="2026-08-01",
    )))

    expense_service = ExpenseService(repo=expenses)
    with pytest.raises(ValidationAppError):
        run(expense_service.update_expense(USER, c["expense_id"], ExpenseIn(date="2026-08-05", amount=999)))
    with pytest.raises(ValidationAppError):
        run(expense_service.delete_expense(USER, c["expense_id"]))
    # In entrambi i casi la spesa non deve essere stata toccata.
    assert expenses.docs[c["expense_id"]]["amount"] == 45.5


def test_expense_service_permette_modifica_di_una_spesa_normale():
    expenses = FakeExpenseRepo()
    expense_service = ExpenseService(repo=expenses)
    doc = run(expense_service.create_expense(USER, ExpenseIn(date="2026-08-01", amount=30, category="vitto")))
    run(expense_service.update_expense(USER, doc["id"], ExpenseIn(date="2026-08-01", amount=35, category="vitto")))
    assert expenses.docs[doc["id"]]["amount"] == 35


# ---------- cargo_load_service ----------

def build_cargo_service(vehicle_repo, clients=None, orders=None):
    repo = FakeDetailRepo()
    service = CargoLoadService(
        repo=repo, vehicles=vehicle_repo,
        clients=clients or FakeRefRepo(), orders=orders or FakeRefRepo(),
    )
    return service, repo


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
    assert load["status"] == "programmato"


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


def test_create_load_accetta_cliente_e_ordine_facoltativi_validi():
    vservice, vrepo = build_vehicle_service()
    vehicle = run(vservice.create_vehicle(USER, make_vehicle()))
    clients = FakeRefRepo([{"id": "client-1", "user_id": USER["id"]}])
    orders = FakeRefRepo([{"id": "order-1", "user_id": USER["id"]}])
    service, repo = build_cargo_service(vrepo, clients=clients, orders=orders)
    load = run(service.create_load(USER, CargoLoadIn(
        vehicle_id=vehicle["id"], date="2026-08-05", description="Pallet",
        client_id="client-1", order_id="order-1", quantity=10, colli=3, peso=250.5,
    )))
    assert load["client_id"] == "client-1"
    assert load["order_id"] == "order-1"
    assert load["quantity"] == 10
    assert load["colli"] == 3
    assert load["peso"] == 250.5


def test_create_load_rifiuta_cliente_di_un_altro_utente():
    vservice, vrepo = build_vehicle_service()
    vehicle = run(vservice.create_vehicle(USER, make_vehicle()))
    clients = FakeRefRepo([{"id": "client-1", "user_id": ALTRO_USER["id"]}])
    service, repo = build_cargo_service(vrepo, clients=clients)
    with pytest.raises(ValidationAppError):
        run(service.create_load(USER, CargoLoadIn(
            vehicle_id=vehicle["id"], date="2026-08-05", description="Pallet", client_id="client-1",
        )))


def test_create_load_senza_cliente_o_ordine_e_comunque_valido():
    """Un account con Clienti/Ordini disattivati (es. CACI SRL) deve poter
    registrare un carico senza questi collegamenti."""
    vservice, vrepo = build_vehicle_service()
    vehicle = run(vservice.create_vehicle(USER, make_vehicle()))
    service, repo = build_cargo_service(vrepo)
    load = run(service.create_load(USER, CargoLoadIn(
        vehicle_id=vehicle["id"], date="2026-08-05", description="Pallet",
    )))
    assert load["client_id"] is None
    assert load["order_id"] is None


def test_sign_load_registra_la_firma_e_segna_consegnato():
    vservice, vrepo = build_vehicle_service()
    vehicle = run(vservice.create_vehicle(USER, make_vehicle()))
    service, repo = build_cargo_service(vrepo)
    load = run(service.create_load(USER, CargoLoadIn(
        vehicle_id=vehicle["id"], date="2026-08-05", description="Pallet",
    )))
    run(service.sign_load(USER, load["id"], "data:image/png;base64,xyz", "Mario Rossi"))
    signed = repo.docs[load["id"]]
    assert signed["status"] == "consegnato"
    assert signed["signer_name"] == "Mario Rossi"
    assert signed["signature"] == "data:image/png;base64,xyz"
    assert signed["signed_at"] is not None


def test_sign_load_rifiuta_carico_inesistente():
    vservice, vrepo = build_vehicle_service()
    service, repo = build_cargo_service(vrepo)
    with pytest.raises(NotFoundError):
        run(service.sign_load(USER, "non-esiste", "data:image/png;base64,xyz", "Mario Rossi"))


# ---------- vehicle_service <-> Personale (assigned_employee_id) ----------

def test_create_vehicle_accetta_dipendente_assegnato_valido():
    employees = FakeRefRepo([{"id": "emp-1", "user_id": USER["id"]}])
    service, repo = build_vehicle_service(employees=employees)
    v = run(service.create_vehicle(USER, make_vehicle(assigned_employee_id="emp-1")))
    assert v["assigned_employee_id"] == "emp-1"


def test_create_vehicle_rifiuta_dipendente_assegnato_di_un_altro_utente():
    employees = FakeRefRepo([{"id": "emp-1", "user_id": ALTRO_USER["id"]}])
    service, repo = build_vehicle_service(employees=employees)
    with pytest.raises(ValidationAppError):
        run(service.create_vehicle(USER, make_vehicle(assigned_employee_id="emp-1")))


def test_create_vehicle_senza_dipendente_assegnato_e_valido():
    service, repo = build_vehicle_service()
    v = run(service.create_vehicle(USER, make_vehicle()))
    assert v["assigned_employee_id"] is None


def test_find_assigned_restituisce_il_mezzo_del_dipendente():
    employees = FakeRefRepo([{"id": "emp-1", "user_id": USER["id"]}])
    service, repo = build_vehicle_service(employees=employees)
    run(service.create_vehicle(USER, make_vehicle("AB123CD", assigned_employee_id="emp-1")))
    run(service.create_vehicle(USER, make_vehicle("XY999ZZ")))

    found = run(service.find_assigned(USER, "emp-1"))
    assert found["plate"] == "AB123CD"


def test_find_assigned_restituisce_none_se_nessun_mezzo_collegato():
    service, repo = build_vehicle_service()
    run(service.create_vehicle(USER, make_vehicle()))
    assert run(service.find_assigned(USER, "emp-1")) is None


# ---------- vehicle_deadline_service.next_deadline ----------

def test_next_deadline_restituisce_la_piu_vicina_dello_stesso_tipo():
    vservice, vrepo = build_vehicle_service()
    vehicle = run(vservice.create_vehicle(USER, make_vehicle()))
    service, repo = build_deadline_service(vrepo)
    run(service.create_deadline(USER, VehicleDeadlineIn(vehicle_id=vehicle["id"], type="revisione", due_date="2026-12-01")))
    run(service.create_deadline(USER, VehicleDeadlineIn(vehicle_id=vehicle["id"], type="revisione", due_date="2026-10-01")))
    run(service.create_deadline(USER, VehicleDeadlineIn(vehicle_id=vehicle["id"], type="bollo", due_date="2026-09-01")))

    next_rev = run(service.next_deadline(USER, vehicle["id"], "revisione"))
    assert next_rev["due_date"] == "2026-10-01"


def test_next_deadline_restituisce_none_se_nessuna_scadenza_di_quel_tipo():
    vservice, vrepo = build_vehicle_service()
    vehicle = run(vservice.create_vehicle(USER, make_vehicle()))
    service, repo = build_deadline_service(vrepo)
    assert run(service.next_deadline(USER, vehicle["id"], "revisione")) is None

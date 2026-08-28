"""
Verifica la gestione dei conflitti sul numero ordine (numero_ordine):

- next_order_number() è già atomico (contatore MongoDB con $inc, vedi
  repositories/order_repository.py) e non collide mai da solo;
- MA numero_ordine resta un campo modificabile a mano da form (creazione e
  modifica ordine — vedi models/order.py e la UI in Ordini.jsx), quindi un
  valore digitato dall'utente può collidere con uno già esistente;
- l'indice univoco su (user_id, numero_ordine) (vedi startup_service) è la
  rete di sicurezza a livello database;
- order_service._create_order_doc ritenta automaticamente con il numero
  successivo SOLO quando il numero era stato generato in automatico (mai
  quando è stato scelto a mano dall'utente, in quel caso l'errore va a lui).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_order_number_conflict.py -v
"""

import asyncio
import sys

import pytest

sys.path.insert(0, ".")

import services.order_service as order_service_mod
from core.exceptions import ConflictError
from services.order_service import _MAX_AUTO_NUMBER_RETRIES, OrderService


def run(coro):
    return asyncio.run(coro)


class FakeOrderRepo:
    """A differenza del FakeOrderRepo di test_orders_update.py, questo
    applica DAVVERO l'unicità di (user_id, numero_ordine), come farebbe
    l'indice univoco reale in MongoDB — necessario per testare la logica di
    retry/conflitto, che altrimenti non avrebbe mai motivo di scattare."""

    def __init__(self):
        self.docs = {}
        self._counters = {}

    def _collides(self, user_id, numero_ordine, exclude_oid=None):
        return any(
            d["user_id"] == user_id
            and d.get("numero_ordine") == numero_ordine
            and d["id"] != exclude_oid
            for d in self.docs.values()
        )

    async def find_many(self, user_id, mandante_id=None):
        return [d for d in self.docs.values() if d["user_id"] == user_id]

    async def find_by_client(self, user_id, client_id):
        return [
            d
            for d in self.docs.values()
            if d["user_id"] == user_id and d["client_id"] == client_id
        ]

    async def find_by_source_offer(self, offer_id, user_id):
        return next(
            (
                d
                for d in self.docs.values()
                if d.get("source_offer_id") == offer_id and d["user_id"] == user_id
            ),
            None,
        )

    async def find_one(self, oid, user_id):
        d = self.docs.get(oid)
        return dict(d) if d and d["user_id"] == user_id else None

    async def insert(self, doc):
        if self._collides(doc["user_id"], doc.get("numero_ordine")):
            raise ConflictError(
                f"Numero ordine \"{doc.get('numero_ordine')}\" già in uso"
            )
        self.docs[doc["id"]] = doc
        return doc

    async def update(self, oid, user_id, data):
        if "numero_ordine" in data and self._collides(
            user_id, data["numero_ordine"], exclude_oid=oid
        ):
            raise ConflictError(
                f"Numero ordine \"{data.get('numero_ordine')}\" già in uso"
            )
        self.docs[oid].update(data)

    async def update_fields(self, oid, user_id, data):
        if oid not in self.docs:
            return False
        if "numero_ordine" in data and self._collides(
            user_id, data["numero_ordine"], exclude_oid=oid
        ):
            raise ConflictError(
                f"Numero ordine \"{data.get('numero_ordine')}\" già in uso"
            )
        self.docs[oid].update(data)
        return True

    async def delete(self, oid, user_id):
        self.docs.pop(oid, None)

    async def next_order_number(self, user_id):
        self._counters[user_id] = self._counters.get(user_id, 0) + 1
        return f"ORD-{self._counters[user_id]:04d}"


class FakeMandanteRepo:
    def __init__(self):
        self.docs = {}

    async def find_one(self, mid, user_id):
        return self.docs.get(mid)


class FakeCommissionRepo:
    def __init__(self):
        self.docs = []

    async def find_many(self, user_id, mandante_id=None):
        return [d for d in self.docs if d["user_id"] == user_id]

    async def find_by_order(self, order_id, user_id):
        return [d for d in self.docs if d.get("order_id") == order_id]

    async def delete_by_order(self, order_id, user_id):
        self.docs = [d for d in self.docs if d.get("order_id") != order_id]

    async def insert(self, doc):
        self.docs.append(doc)
        return doc


class FakeCommissionService:
    """Sostituisce il modulo commission_service usato internamente da
    order_service: non serve testare qui la logica di provvigioni/bonus,
    solo che _create_order_doc non fallisca chiamandolo."""

    def __init__(self):
        self.repo = FakeCommissionRepo()

    async def check_and_award_bonus(self, user_id, mandante_id):
        pass


def build_service(monkeypatch, order_repo=None):
    order_repo = order_repo or FakeOrderRepo()
    fake_commission_service = FakeCommissionService()
    # commission_service è importato per nome dentro order_service: va
    # sostituito lì, non nel modulo commission_service originale (stesso
    # accorgimento di test_orders_update.py).
    monkeypatch.setattr(
        order_service_mod, "commission_service", fake_commission_service
    )
    service = OrderService(repo=order_repo, mandante_repo=FakeMandanteRepo())
    return service, order_repo


FAKE_ITEMS = [
    {"description": "Prodotto test", "quantity": 1, "unit_price": 100, "discount": 0}
]


def test_numeri_automatici_sequenziali_non_collidono(monkeypatch):
    service, _ = build_service(monkeypatch)
    d1 = run(service._create_order_doc({"id": "user-1"}, "c-1", "m-1", FAKE_ITEMS))
    d2 = run(service._create_order_doc({"id": "user-1"}, "c-1", "m-1", FAKE_ITEMS))
    assert d1["numero_ordine"] == "ORD-0001"
    assert d2["numero_ordine"] == "ORD-0002"


def test_numero_manuale_duplicato_solleva_conflitto(monkeypatch):
    service, _ = build_service(monkeypatch)
    run(
        service._create_order_doc(
            {"id": "user-1"}, "c-1", "m-1", FAKE_ITEMS, numero_ordine="ORD-CUSTOM"
        )
    )
    with pytest.raises(ConflictError):
        run(
            service._create_order_doc(
                {"id": "user-1"}, "c-1", "m-1", FAKE_ITEMS, numero_ordine="ORD-CUSTOM"
            )
        )


def test_stesso_numero_permesso_per_utenti_diversi(monkeypatch):
    """L'unicità è per utente, non globale: due agenti diversi possono
    avere entrambi un ordine 'ORD-0001' senza conflitto."""
    service, _ = build_service(monkeypatch)
    d1 = run(
        service._create_order_doc(
            {"id": "user-1"}, "c-1", "m-1", FAKE_ITEMS, numero_ordine="ORD-0001"
        )
    )
    d2 = run(
        service._create_order_doc(
            {"id": "user-2"}, "c-1", "m-1", FAKE_ITEMS, numero_ordine="ORD-0001"
        )
    )
    assert d1["numero_ordine"] == d2["numero_ordine"] == "ORD-0001"


def test_numero_automatico_che_collide_con_uno_manuale_viene_ritentato(monkeypatch):
    """Scenario reale: l'utente ha in precedenza digitato a mano 'ORD-0002'
    quando il contatore era ancora indietro. Quando il contatore automatico
    lo raggiunge, non deve fallire: deve saltare quel numero e riprovare
    con il successivo, in modo trasparente per l'utente."""
    service, repo = build_service(monkeypatch)
    # Il contatore è ancora a 0; l'utente inserisce a mano un ordine con un
    # numero "nel futuro" del contatore.
    run(
        service._create_order_doc(
            {"id": "user-1"}, "c-1", "m-1", FAKE_ITEMS, numero_ordine="ORD-0002"
        )
    )

    d1 = run(
        service._create_order_doc({"id": "user-1"}, "c-1", "m-1", FAKE_ITEMS)
    )  # -> ORD-0001
    d2 = run(
        service._create_order_doc({"id": "user-1"}, "c-1", "m-1", FAKE_ITEMS)
    )  # collide su ORD-0002, ritenta

    assert d1["numero_ordine"] == "ORD-0001"
    assert d2["numero_ordine"] == "ORD-0003"  # non ORD-0002, saltato per la collisione


def test_retry_si_ferma_dopo_troppi_tentativi(monkeypatch):
    """Se la generazione automatica continua a collidere oltre la soglia di
    tentativi (scenario patologico, non dovrebbe succedere in pratica), il
    servizio deve arrendersi con un errore chiaro invece di ritentare
    all'infinito."""

    class AlwaysCollidingRepo(FakeOrderRepo):
        async def insert(self, doc):
            raise ConflictError("sempre in conflitto, per il test")

    service, repo = build_service(monkeypatch, order_repo=AlwaysCollidingRepo())

    with pytest.raises(ConflictError):
        run(service._create_order_doc({"id": "user-1"}, "c-1", "m-1", FAKE_ITEMS))

    # Deve aver chiamato next_order_number esattamente _MAX_AUTO_NUMBER_RETRIES volte,
    # non un numero indefinito.
    assert repo._counters["user-1"] == _MAX_AUTO_NUMBER_RETRIES


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

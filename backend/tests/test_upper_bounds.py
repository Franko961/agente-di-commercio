"""
Verifica i limiti massimi aggiunti ai campi numerici/testuali/liste che
prima non ne avevano uno (o avevano solo un limite inferiore): quantità,
prezzi unitari, importi spesa, testo libero (note/descrizioni/messaggio
contatti), e le liste di sotto-elementi (righe offerta/ordine, tag
documento, mandanti collegati a un cliente, import in blocco). Senza un
tetto, un valore assurdo (es. quantità 10^30, un messaggio di contatto da
10 MB) veniva accettato e salvato così com'è — dati palesemente errati,
payload sproporzionati, più costi di storage e, per i campi passati
all'assistente AI, di token per chiamata.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_upper_bounds.py -v
"""

import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, ".")

from core.validation_limits import (
    LONG_TEXT_MAX_LENGTH,
    MAX_COUNT,
    MAX_EXPENSE_AMOUNT,
    MAX_LINE_ITEMS,
    MAX_MANDANTI_PER_CLIENT,
    MAX_MONETARY_TARGET,
    MAX_QUANTITY,
    MAX_TAGS,
    MAX_UNIT_PRICE,
    SHORT_TEXT_MAX_LENGTH,
)
from models.ai import AIQuery
from models.auth import PASSWORD_MAX_LENGTH, RegisterIn
from models.client import ClientIn
from models.contact_request import ContactRequestIn
from models.document import DocumentIn
from models.expense import ExpenseIn
from models.lead import LeadIn
from models.mandante import MandanteIn
from models.offer import OfferIn, OfferLineItem
from models.order import OrderIn, OrderLineItem
from models.route_planning import RoutePlanIn

# ---------- Quantità e prezzo unitario (riga offerta/ordine) ----------


@pytest.mark.parametrize("ItemModel", [OfferLineItem, OrderLineItem])
def test_quantita_astronomica_rifiutata(ItemModel):
    with pytest.raises(ValidationError):
        ItemModel(description="Prodotto", quantity=MAX_QUANTITY + 1, unit_price=10)


@pytest.mark.parametrize("ItemModel", [OfferLineItem, OrderLineItem])
def test_quantita_al_limite_accettata(ItemModel):
    item = ItemModel(description="Prodotto", quantity=MAX_QUANTITY, unit_price=10)
    assert item.quantity == MAX_QUANTITY


@pytest.mark.parametrize("ItemModel", [OfferLineItem, OrderLineItem])
def test_prezzo_unitario_enorme_rifiutato(ItemModel):
    with pytest.raises(ValidationError):
        ItemModel(description="Prodotto", quantity=1, unit_price=MAX_UNIT_PRICE + 1)


def test_descrizione_riga_troppo_lunga_rifiutata():
    with pytest.raises(ValidationError):
        OfferLineItem(description="x" * 501, quantity=1, unit_price=10)


# ---------- Numero di righe offerta/ordine ----------


def test_troppe_righe_offerta_rifiutato():
    riga = OfferLineItem(description="Prodotto", quantity=1, unit_price=10)
    with pytest.raises(ValidationError):
        OfferIn(
            client_id="c1",
            mandante_id="m1",
            title="Offerta",
            items=[riga] * (MAX_LINE_ITEMS + 1),
        )


def test_troppe_righe_ordine_rifiutato():
    riga = OrderLineItem(description="Prodotto", quantity=1, unit_price=10)
    with pytest.raises(ValidationError):
        OrderIn(client_id="c1", mandante_id="m1", items=[riga] * (MAX_LINE_ITEMS + 1))


# ---------- Importo spesa ----------


def test_importo_spesa_enorme_rifiutato():
    with pytest.raises(ValidationError):
        ExpenseIn(date="2026-08-01", amount=MAX_EXPENSE_AMOUNT + 1)


def test_importo_spesa_al_limite_accettato():
    expense = ExpenseIn(date="2026-08-01", amount=MAX_EXPENSE_AMOUNT)
    assert expense.amount == MAX_EXPENSE_AMOUNT


def test_importo_spesa_zero_ancora_rifiutato_dal_validatore_esistente():
    """Non deve essere stata toccata la validazione preesistente sul
    limite INFERIORE (amount > 0), solo aggiunto quello superiore."""
    with pytest.raises(ValidationError):
        ExpenseIn(date="2026-08-01", amount=0)


# ---------- Messaggio contatti ----------


def test_messaggio_contatti_troppo_lungo_rifiutato():
    with pytest.raises(ValidationError):
        ContactRequestIn(
            nome="Mario Rossi",
            email="mario@example.com",
            messaggio="x" * (LONG_TEXT_MAX_LENGTH + 1),
        )


def test_messaggio_contatti_al_limite_accettato():
    req = ContactRequestIn(
        nome="Mario Rossi",
        email="mario@example.com",
        messaggio="x" * LONG_TEXT_MAX_LENGTH,
    )
    assert len(req.messaggio) == LONG_TEXT_MAX_LENGTH


def test_nome_contatti_troppo_lungo_rifiutato():
    with pytest.raises(ValidationError):
        ContactRequestIn(
            nome="x" * (SHORT_TEXT_MAX_LENGTH + 1),
            email="mario@example.com",
            messaggio="Ciao",
        )


# ---------- Note/descrizioni generiche ----------


def test_note_cliente_troppo_lunghe_rifiutate():
    with pytest.raises(ValidationError):
        ClientIn(company_name="Acme", notes="x" * (LONG_TEXT_MAX_LENGTH + 1))


def test_note_offerta_troppo_lunghe_rifiutate():
    with pytest.raises(ValidationError):
        OfferIn(
            client_id="c1",
            mandante_id="m1",
            title="Offerta",
            notes="x" * (LONG_TEXT_MAX_LENGTH + 1),
        )


# ---------- Campi prima privi di QUALUNQUE limite (né inferiore né superiore) ----------


def test_estimated_value_lead_negativo_ora_rifiutato():
    with pytest.raises(ValidationError):
        LeadIn(company_name="Acme", estimated_value=-1)


def test_estimated_value_lead_astronomico_rifiutato():
    with pytest.raises(ValidationError):
        LeadIn(company_name="Acme", estimated_value=MAX_MONETARY_TARGET + 1)


def test_target_monthly_mandante_astronomico_rifiutato():
    with pytest.raises(ValidationError):
        MandanteIn(name="Mandante SRL", target_monthly=MAX_MONETARY_TARGET + 1)


def test_target_clients_mandante_astronomico_rifiutato():
    with pytest.raises(ValidationError):
        MandanteIn(name="Mandante SRL", target_clients=MAX_COUNT + 1)


def test_visit_minutes_zero_ora_rifiutato():
    with pytest.raises(ValidationError):
        RoutePlanIn(client_ids=["c1"], visit_minutes=0)


def test_visit_minutes_eccessivo_rifiutato():
    with pytest.raises(ValidationError):
        RoutePlanIn(client_ids=["c1"], visit_minutes=481)


def test_visit_minutes_valore_ragionevole_accettato():
    plan = RoutePlanIn(client_ids=["c1"], visit_minutes=45)
    assert plan.visit_minutes == 45


# ---------- Liste (tag, mandanti collegati) ----------


def test_troppi_tag_documento_rifiutato():
    with pytest.raises(ValidationError):
        DocumentIn(name="File.pdf", tags=[f"tag{i}" for i in range(MAX_TAGS + 1)])


def test_troppi_mandanti_collegati_a_cliente_rifiutato():
    with pytest.raises(ValidationError):
        ClientIn(
            company_name="Acme",
            mandante_ids=[f"m{i}" for i in range(MAX_MANDANTI_PER_CLIENT + 1)],
        )


# ---------- Password (troncatura silenziosa bcrypt oltre 72 byte) ----------


def test_password_oltre_72_caratteri_rifiutata_in_registrazione():
    with pytest.raises(ValidationError):
        RegisterIn(
            email="a@example.com",
            password="x" * (PASSWORD_MAX_LENGTH + 1),
            name="Mario",
        )


def test_password_72_caratteri_accettata_in_registrazione():
    reg = RegisterIn(
        email="a@example.com", password="x" * PASSWORD_MAX_LENGTH, name="Mario"
    )
    assert len(reg.password) == PASSWORD_MAX_LENGTH


# ---------- Messaggio assistente AI ----------


def test_messaggio_ai_troppo_lungo_rifiutato():
    with pytest.raises(ValidationError):
        AIQuery(message="x" * (LONG_TEXT_MAX_LENGTH + 1))


def test_messaggio_ai_al_limite_accettato():
    query = AIQuery(message="x" * LONG_TEXT_MAX_LENGTH)
    assert len(query.message) == LONG_TEXT_MAX_LENGTH


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

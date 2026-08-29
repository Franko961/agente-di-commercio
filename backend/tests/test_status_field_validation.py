"""
Verifica che gli stati/categorie definiti come costanti (ORDER_STATUSES,
PAYMENT_STATUSES, OFFER_STATUSES, LEAD_STATUSES, APPOINTMENT_STATUSES,
SALE_TYPES, DOCUMENT_CATEGORIES) siano davvero applicati come vincolo sui
campi corrispondenti, e non solo dichiarati e mai controllati: prima di
questo fix i modelli accettavano una stringa qualunque (es.
status="qualsiasi_valore"), che finiva salvata così com'è — rompendo
silenziosamente confronti a stringa fissa nel codice (es.
services.offer_service.update_offer_status che confronta con "accettata",
o services.commission_service.get_commission_rate che confronta sale_type
con "nuovo"/"rinnovo") e i filtri colore/etichetta nel frontend.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_status_field_validation.py -v
"""

import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, ".")

from models.appointment import APPOINTMENT_STATUSES, AppointmentIn
from models.document import DOCUMENT_CATEGORIES, DocumentIn, DocumentMetaUpdate
from models.lead import LEAD_STATUSES, LeadIn, LeadStatusIn
from models.offer import OFFER_STATUSES, OfferIn, OfferStatusIn
from models.order import (
    ORDER_STATUSES,
    PAYMENT_STATUSES,
    SALE_TYPES,
    OrderIn,
    OrderStatusIn,
)

# ---------- OrderIn / OrderStatusIn ----------


@pytest.mark.parametrize("value", ORDER_STATUSES)
def test_order_status_valido_accettato(value):
    order = OrderIn(client_id="c1", mandante_id="m1", status=value)
    assert order.status == value


def test_order_status_arbitrario_rifiutato():
    with pytest.raises(ValidationError):
        OrderIn(client_id="c1", mandante_id="m1", status="qualsiasi_valore")


def test_order_payment_status_arbitrario_rifiutato():
    with pytest.raises(ValidationError):
        OrderIn(client_id="c1", mandante_id="m1", payment_status="cripto")


def test_order_sale_type_arbitrario_rifiutato():
    with pytest.raises(ValidationError):
        OrderIn(client_id="c1", mandante_id="m1", sale_type="usato")


def test_order_status_in_patch_status_arbitrario_rifiutato():
    with pytest.raises(ValidationError):
        OrderStatusIn(status="qualsiasi_valore")


def test_order_status_in_patch_payment_status_arbitrario_rifiutato():
    with pytest.raises(ValidationError):
        OrderStatusIn(payment_status="cripto")


def test_order_status_in_patch_campi_omessi_restano_none():
    """Semantica 'patch': i campi non inviati devono restare None, non
    ricadere sul default di OrderIn (che romperebbe l'aggiornamento
    parziale, sovrascrivendo campi non toccati dalla richiesta)."""
    payload = OrderStatusIn()
    assert payload.status is None
    assert payload.payment_status is None


# ---------- OfferIn / OfferStatusIn ----------


@pytest.mark.parametrize("value", OFFER_STATUSES)
def test_offer_status_valido_accettato(value):
    offer = OfferIn(client_id="c1", mandante_id="m1", title="Offerta", status=value)
    assert offer.status == value


def test_offer_status_arbitrario_rifiutato():
    with pytest.raises(ValidationError):
        OfferIn(
            client_id="c1", mandante_id="m1", title="Offerta", status="qualsiasi_valore"
        )


def test_offer_sale_type_arbitrario_rifiutato():
    with pytest.raises(ValidationError):
        OfferIn(client_id="c1", mandante_id="m1", title="Offerta", sale_type="usato")


def test_offer_status_in_valido_accettato():
    assert OfferStatusIn(status="accettata").status == "accettata"


def test_offer_status_in_arbitrario_rifiutato():
    """Il caso centrale segnalato: PATCH /api/offers/{id}/status passava
    payload.get('status') a offer_service senza alcuna validazione — un
    valore fuori dai 5 stati reali veniva salvato così com'è, e non avrebbe
    mai fatto scattare la conversione automatica in ordine (che confronta
    esplicitamente con la stringa "accettata")."""
    with pytest.raises(ValidationError):
        OfferStatusIn(status="qualsiasi_valore")


def test_offer_status_in_richiede_il_campo():
    with pytest.raises(ValidationError):
        OfferStatusIn()


# ---------- AppointmentIn ----------


@pytest.mark.parametrize("value", APPOINTMENT_STATUSES)
def test_appointment_status_valido_accettato(value):
    appt = AppointmentIn(title="Visita", start="2026-08-01T10:00:00", status=value)
    assert appt.status == value


def test_appointment_status_arbitrario_rifiutato():
    with pytest.raises(ValidationError):
        AppointmentIn(title="Visita", start="2026-08-01T10:00:00", status="in_corso")


# ---------- LeadIn / LeadStatusIn ----------


@pytest.mark.parametrize("value", LEAD_STATUSES)
def test_lead_status_valido_accettato(value):
    lead = LeadIn(company_name="Acme", status=value)
    assert lead.status == value


def test_lead_status_arbitrario_rifiutato():
    with pytest.raises(ValidationError):
        LeadIn(company_name="Acme", status="interessato")


def test_lead_status_in_valido_accettato():
    assert LeadStatusIn(status="vinto").status == "vinto"


def test_lead_status_in_arbitrario_rifiutato():
    """Stesso gap di OfferStatusIn: PATCH /api/leads/{id}/status passava
    payload.get('status') senza validazione."""
    with pytest.raises(ValidationError):
        LeadStatusIn(status="interessato")


# ---------- DocumentIn / DocumentMetaUpdate ----------


@pytest.mark.parametrize("value", DOCUMENT_CATEGORIES)
def test_document_category_valida_accettata(value):
    doc = DocumentIn(name="File", category=value)
    assert doc.category == value


def test_document_category_arbitraria_rifiutata():
    with pytest.raises(ValidationError):
        DocumentIn(name="File", category="qualsiasi_valore")


def test_document_meta_update_categoria_arbitraria_rifiutata():
    with pytest.raises(ValidationError):
        DocumentMetaUpdate(category="qualsiasi_valore")


def test_document_meta_update_campi_omessi_non_impostati():
    """exclude_unset=True (usato da document_service.update_document_meta)
    deve poter distinguere 'non inviato' da 'inviato con valore falsy':
    verificato qui a livello di model_fields_set, la base di quella
    distinzione."""
    payload = DocumentMetaUpdate(name="nuovo_nome.pdf")
    assert payload.model_fields_set == {"name"}
    assert payload.model_dump(exclude_unset=True) == {"name": "nuovo_nome.pdf"}


# ---------- Le liste stesse non sono vuote (garanzia minima di sanità) ----------


@pytest.mark.parametrize(
    "values",
    [
        ORDER_STATUSES,
        PAYMENT_STATUSES,
        SALE_TYPES,
        OFFER_STATUSES,
        APPOINTMENT_STATUSES,
        LEAD_STATUSES,
        DOCUMENT_CATEGORIES,
    ],
)
def test_costante_non_vuota(values):
    assert len(values) > 0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

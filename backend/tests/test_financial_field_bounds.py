"""
Verifica i limiti aggiunti a OfferLineItem, OrderLineItem, ProductIn e
MandanteIn: quantità/prezzi/aliquote/sconti privi di limiti permettevano
valori negativi o assurdi (es. sconto 500%, aliquota -10%) che si
propagavano silenziosamente al totale di un'offerta/ordine e da lì alla
provvigione calcolata su di esso (services.commission_service).

Esegui con:
    JWT_SECRET=test python -m pytest tests/test_financial_field_bounds.py -v
"""
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, ".")

from models.offer import OfferLineItem
from models.order import OrderLineItem
from models.product import ProductIn
from models.mandante import MandanteIn, BonusTier


# ---------- OfferLineItem / OrderLineItem ----------

@pytest.mark.parametrize("ItemModel", [OfferLineItem, OrderLineItem])
def test_riga_valida_accettata(ItemModel):
    item = ItemModel(description="Prodotto", quantity=2, unit_price=100, discount=10)
    assert item.quantity == 2


@pytest.mark.parametrize("ItemModel", [OfferLineItem, OrderLineItem])
@pytest.mark.parametrize("quantity", [0, -1, -5.5])
def test_quantita_zero_o_negativa_rifiutata(ItemModel, quantity):
    with pytest.raises(ValidationError):
        ItemModel(description="Prodotto", quantity=quantity, unit_price=100)


@pytest.mark.parametrize("ItemModel", [OfferLineItem, OrderLineItem])
def test_prezzo_negativo_rifiutato(ItemModel):
    with pytest.raises(ValidationError):
        ItemModel(description="Prodotto", quantity=1, unit_price=-50)


@pytest.mark.parametrize("ItemModel", [OfferLineItem, OrderLineItem])
@pytest.mark.parametrize("discount", [-1, 100.1, 500])
def test_sconto_fuori_dai_limiti_rifiutato(ItemModel, discount):
    with pytest.raises(ValidationError):
        ItemModel(description="Prodotto", quantity=1, unit_price=100, discount=discount)


@pytest.mark.parametrize("ItemModel", [OfferLineItem, OrderLineItem])
def test_sconto_100_per_cento_accettato(ItemModel):
    """100% è il limite massimo valido (prodotto omaggio), non oltre."""
    item = ItemModel(description="Omaggio", quantity=1, unit_price=100, discount=100)
    assert item.discount == 100


# ---------- ProductIn ----------

def test_prodotto_valido_accettato():
    p = ProductIn(mandante_id="m1", name="Prodotto A", price=50, cost=20, commission_rate=10)
    assert p.price == 50


def test_prodotto_prezzo_negativo_rifiutato():
    with pytest.raises(ValidationError):
        ProductIn(mandante_id="m1", name="Prodotto A", price=-10)


def test_prodotto_costo_negativo_rifiutato():
    with pytest.raises(ValidationError):
        ProductIn(mandante_id="m1", name="Prodotto A", price=10, cost=-5)


def test_prodotto_aliquota_fuori_limiti_rifiutata():
    with pytest.raises(ValidationError):
        ProductIn(mandante_id="m1", name="Prodotto A", price=10, commission_rate=150)


# ---------- MandanteIn / BonusTier ----------

def test_mandante_valido_accettato():
    m = MandanteIn(name="Mandante Test", commission_rate=8)
    assert m.commission_rate == 8


@pytest.mark.parametrize("rate", [-5, 150])
def test_mandante_aliquota_fuori_limiti_rifiutata(rate):
    with pytest.raises(ValidationError):
        MandanteIn(name="Mandante Test", commission_rate=rate)


@pytest.mark.parametrize("rate", [-5, 150])
def test_mandante_aliquota_override_fuori_limiti_rifiutata(rate):
    with pytest.raises(ValidationError):
        MandanteIn(name="Mandante Test", commission_rate_new=rate)


def test_bonus_tier_soglia_negativa_rifiutata():
    with pytest.raises(ValidationError):
        BonusTier(threshold=-1000, bonus=500)


def test_bonus_tier_importo_negativo_rifiutato():
    with pytest.raises(ValidationError):
        BonusTier(threshold=2000, bonus=-500)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

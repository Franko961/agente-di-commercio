"""
Test isolato (nessun DB reale) per la logica della scala premi.

Regola (Franco, 14/07/2026):
- Primo scaglione 2000€ -> bonus 500€: FISSO, si somma sempre agli altri.
- Scaglioni successivi (es. 3000€ -> 360€, 5000€ -> 600€): NON si sommano tra loro.
  Conta solo il bonus dello scaglione più alto raggiunto tra questi, che si somma
  ai 500€ del primo scaglione.

Esempi attesi:
- fatturato 2100€  -> solo scaglione base  -> totale 500€
- fatturato 3100€  -> base + scaglione 3000 -> totale 500 + 360 = 860€
- fatturato 5100€  -> base + scaglione 5000 -> totale 500 + 600 = 1100€ (il 360 NON si somma)
"""

import asyncio
import sys

sys.path.insert(0, ".")


class FakeCommissionRepo:
    def __init__(self, commissions):
        self.docs = list(commissions)

    async def find_many(self, user_id):
        return list(self.docs)

    async def insert(self, doc):
        self.docs.append(doc)
        return doc

    async def delete(self, cid, user_id):
        self.docs = [d for d in self.docs if d["id"] != cid]


class FakeMandanteRepo:
    def __init__(self, mandante):
        self.mandante = mandante

    async def find_one(self, mid, user_id):
        return self.mandante

    async def find_many(self, user_id):
        return [self.mandante]


def make_sale_commission(cid, base_amount, rate=10.0):
    return {
        "id": cid,
        "user_id": "user-1",
        "mandante_id": "m-1",
        "amount": base_amount * rate / 100,
        "rate": rate,
        "base_amount": base_amount,
        "sale_type": "nuovo",
        "status": "maturato",
    }


def build_service(mandante, commissions):
    from services.commission_service import CommissionService

    commission_repo = FakeCommissionRepo(commissions)
    mandante_repo = FakeMandanteRepo(mandante)
    service = CommissionService(repo=commission_repo, mandante_repo=mandante_repo)
    return service, commission_repo


MANDANTE = {
    "id": "m-1",
    "user_id": "user-1",
    "name": "Mandante Test",
    "commission_rate": 10.0,
    "bonus_tiers": [
        {"threshold": 2000, "bonus": 500},
        {"threshold": 3000, "bonus": 360},
        {"threshold": 5000, "bonus": 600},
    ],
}


def _run_and_get_bonus(fatturato):
    commissions = [make_sale_commission("c1", base_amount=fatturato)]
    service, repo = build_service(MANDANTE, commissions)
    asyncio.run(service.check_and_award_bonus("user-1", "m-1"))
    bonus_records = [d for d in repo.docs if d.get("sale_type") == "bonus"]
    return bonus_records, repo


def test_solo_scaglione_base():
    bonus_records, _ = _run_and_get_bonus(2100)
    thresholds = sorted(d["bonus_tier_threshold"] for d in bonus_records)
    total = sum(d["amount"] for d in bonus_records)
    assert thresholds == [2000]
    assert total == 500


def test_base_piu_scaglione_3000():
    bonus_records, _ = _run_and_get_bonus(3100)
    thresholds = sorted(d["bonus_tier_threshold"] for d in bonus_records)
    total = sum(d["amount"] for d in bonus_records)
    assert thresholds == [2000, 3000]
    assert total == 860, f"Atteso 500+360=860, trovato {total}"


def test_base_piu_scaglione_5000_non_cumula_col_3000():
    """Superando anche i 5000€, il bonus dei 3000€ (360) NON deve più esserci:
    solo il più alto tra gli 'altri' scaglioni conta."""
    bonus_records, _ = _run_and_get_bonus(5100)
    thresholds = sorted(d["bonus_tier_threshold"] for d in bonus_records)
    total = sum(d["amount"] for d in bonus_records)
    assert thresholds == [
        2000,
        5000,
    ], f"Il 3000 non deve comparire, trovato {thresholds}"
    assert total == 1100, f"Atteso 500+600=1100 (senza il 360), trovato {total}"


def test_transizione_da_3000_a_5000_sostituisce_il_bonus():
    """Se il fatturato passa da 3100€ a 5100€, il bonus del 3000 deve essere
    rimosso e sostituito da quello del 5000 (non si accumulano)."""
    commissions = [make_sale_commission("c1", base_amount=3100)]
    service, repo = build_service(MANDANTE, commissions)
    asyncio.run(service.check_and_award_bonus("user-1", "m-1"))
    assert sorted(
        d["bonus_tier_threshold"] for d in repo.docs if d.get("sale_type") == "bonus"
    ) == [2000, 3000]

    # il fatturato sale a 5100
    repo.docs = [d for d in repo.docs if d.get("sale_type") != "nuovo"]
    repo.docs.append(make_sale_commission("c1", base_amount=5100))
    asyncio.run(service.check_and_award_bonus("user-1", "m-1"))

    bonus_records = [d for d in repo.docs if d.get("sale_type") == "bonus"]
    thresholds = sorted(d["bonus_tier_threshold"] for d in bonus_records)
    total = sum(d["amount"] for d in bonus_records)
    assert thresholds == [2000, 5000]
    assert total == 1100


def test_bonus_summary_totale_coerente():
    commissions = [make_sale_commission("c1", base_amount=5100)]
    service, repo = build_service(MANDANTE, commissions)
    result = asyncio.run(service.bonus_summary({"id": "user-1"}))
    assert len(result) == 1
    assert result[0]["total_bonus"] == 1100


if __name__ == "__main__":
    test_solo_scaglione_base()
    print("OK: test 1 - solo scaglione base (2100€ -> 500€)")
    test_base_piu_scaglione_3000()
    print("OK: test 2 - base + 3000 (3100€ -> 860€)")
    test_base_piu_scaglione_5000_non_cumula_col_3000()
    print("OK: test 3 - base + 5000, il 3000 non si somma (5100€ -> 1100€)")
    test_transizione_da_3000_a_5000_sostituisce_il_bonus()
    print("OK: test 4 - transizione 3000 -> 5000 sostituisce il bonus intermedio")
    test_bonus_summary_totale_coerente()
    print("OK: test 5 - bonus_summary coerente")

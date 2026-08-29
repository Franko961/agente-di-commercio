"""
Verifica migrations.runner (backend/migrations/): il sistema di migrazioni
dati tracciate introdotto per non rifare ad ogni avvio la scansione completa
delle collection dei vecchi backfill una tantum (services/startup/migrations.py,
rimosso) — man mano che le collection crescono, "tanto è comunque un no-op"
resta comunque un costo reale.

Copre le tre proprietà nuove (non solo codice spostato):
- una migrazione già tracciata non viene rieseguita;
- una migrazione che fallisce non lascia il tracciamento come "applicata"
  (va ritentata al prossimo avvio, non persa per sempre come "fatta" senza
  esserlo davvero);
- l'ordine di scoperta dei file rispetta il prefisso numerico, non l'ordine
  del filesystem.

Usa un finto collection MongoDB che replica la garanzia su cui si basa il
runner (insert_one che solleva DuplicateKeyError se la chiave _id esiste
già, come farebbe l'unicità implicita di _id) — stesso approccio già
validato in test_job_lock_repository.py/test_automation_run_repository.py.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_migration_runner.py -v
"""

import asyncio
import importlib
import sys
import types
from pathlib import Path

import pytest
from pymongo.errors import DuplicateKeyError

sys.path.insert(0, ".")

import migrations.runner as runner_mod


def run(coro):
    return asyncio.run(coro)


class FakeMigrationsCollection:
    def __init__(self):
        self.docs = {}  # module_name -> dict

    async def insert_one(self, doc):
        key = doc["_id"]
        if key in self.docs:
            raise DuplicateKeyError("chiave duplicata (_id)")
        self.docs[key] = dict(doc)

    async def delete_one(self, query):
        self.docs.pop(query["_id"], None)


def _fake_module(run_fn):
    mod = types.SimpleNamespace()
    mod.run = run_fn
    return mod


def test_discover_migration_names_ordina_per_prefisso_numerico(tmp_path: Path):
    for name in ("_003_c.py", "_001_a.py", "_002_b.py"):
        (tmp_path / name).write_text("async def run(): ...\n")
    # File che NON deve comparire tra le migrazioni scoperte: __init__.py e
    # runner.py stesso vivono nella stessa cartella ma non seguono il
    # pattern _NNN_, e un file senza prefisso numerico valido va ignorato.
    (tmp_path / "__init__.py").write_text("")
    (tmp_path / "runner.py").write_text("")
    (tmp_path / "not_a_migration.py").write_text("")

    names = runner_mod._discover_migration_names(tmp_path)

    assert names == ["_001_a", "_002_b", "_003_c"]


def test_apply_one_esegue_una_migrazione_non_ancora_tracciata(monkeypatch):
    fake_collection = FakeMigrationsCollection()
    monkeypatch.setattr(runner_mod, "COLLECTION", fake_collection)

    calls = []

    async def fake_run():
        calls.append("eseguita")

    monkeypatch.setattr(importlib, "import_module", lambda name: _fake_module(fake_run))

    run(runner_mod._apply_one("_001_esempio"))

    assert calls == ["eseguita"]
    assert "_001_esempio" in fake_collection.docs


def test_apply_one_salta_una_migrazione_gia_tracciata(monkeypatch):
    fake_collection = FakeMigrationsCollection()
    fake_collection.docs["_001_esempio"] = {"_id": "_001_esempio"}
    monkeypatch.setattr(runner_mod, "COLLECTION", fake_collection)

    async def run_non_deve_essere_chiamata():
        raise AssertionError(
            "run() non doveva essere chiamata per una migrazione già tracciata"
        )

    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: _fake_module(run_non_deve_essere_chiamata),
    )

    run(runner_mod._apply_one("_001_esempio"))  # non deve sollevare nulla


def test_apply_one_rimuove_il_tracciamento_se_la_migrazione_fallisce(monkeypatch):
    fake_collection = FakeMigrationsCollection()
    monkeypatch.setattr(runner_mod, "COLLECTION", fake_collection)

    async def fake_run_che_fallisce():
        raise RuntimeError("errore simulato durante la migrazione")

    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: _fake_module(fake_run_che_fallisce),
    )

    with pytest.raises(RuntimeError, match="errore simulato"):
        run(runner_mod._apply_one("_001_esempio"))

    # Il tracciamento va tolto: al prossimo avvio la migrazione deve poter
    # essere ritentata, non restare bloccata per sempre come "applicata".
    assert "_001_esempio" not in fake_collection.docs

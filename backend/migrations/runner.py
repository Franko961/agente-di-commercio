import importlib
import logging
from pathlib import Path

from pymongo.errors import DuplicateKeyError

from core.database import db

logger = logging.getLogger(__name__)

COLLECTION = db.schema_migrations


def _discover_migration_names(migrations_dir: Path) -> list:
    """Nomi dei moduli di migrazione in migrations_dir, in ordine di
    esecuzione (il prefisso _NNN_ ordina correttamente per confronto di
    stringhe: "_001_..." < "_002_..." < ... fino a "_999_...")."""
    return sorted(f.stem for f in migrations_dir.glob("_[0-9][0-9][0-9]_*.py"))


async def _apply_one(module_name: str) -> None:
    """Applica una singola migrazione se non ancora tracciata. Con più
    repliche Railway che avviano run_startup contemporaneamente allo stesso
    deploy, solo la prima che riesce a inserire il documento di tracciamento
    esegue davvero la migrazione — stesso pattern già validato in questo
    codebase per job_lock_repository.try_acquire/
    automation_run_repository.try_claim/dedup webhook: l'indice univoco
    implicito su _id fa fallire con DuplicateKeyError chi arriva secondo, le
    altre repliche saltano silenziosamente. Se run() solleva un'eccezione, il
    documento di tracciamento viene tolto prima di ripropagare l'errore: la
    migrazione non risulta "applicata" e verrà ritentata al prossimo avvio,
    invece di restare bloccata per sempre come "fatta" senza esserlo
    davvero."""
    try:
        await COLLECTION.insert_one({"_id": module_name})
    except DuplicateKeyError:
        return  # già applicata (o in corso su un'altra replica)

    module = importlib.import_module(f"migrations.{module_name}")
    try:
        logger.info(f"Eseguo migrazione {module_name}...")
        await module.run()
        logger.info(f"Migrazione {module_name} completata")
    except Exception:
        await COLLECTION.delete_one({"_id": module_name})
        raise


async def apply_pending_migrations() -> None:
    """Applica in ordine ogni migrazione dati in migrations/_NNN_*.py non
    ancora eseguita — a differenza della creazione indici
    (services/startup/indexes.py, idempotente ed economica, gira sempre ad
    ogni avvio), ogni migrazione qui gira UNA sola volta nella vita del
    database, mai più dopo, indipendentemente da quanti riavvii/deploy ci
    saranno: man mano che le collection crescono, rifare a ogni boot una
    scansione completa "tanto è comunque un no-op" resta un costo reale."""
    migrations_dir = Path(__file__).parent
    for module_name in _discover_migration_names(migrations_dir):
        await _apply_one(module_name)

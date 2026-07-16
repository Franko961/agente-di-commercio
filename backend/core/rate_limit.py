from datetime import datetime, timezone, timedelta
from core.database import db

# Collezione dedicata con indice TTL (creato in startup_service.py): i vecchi
# eventi vengono ripuliti automaticamente da MongoDB, non serve un job separato.
COLLECTION = db.rate_limit_events


async def check_and_record(kind: str, key: str, max_attempts: int, window_minutes: int) -> bool:
    """Contatore a finestra scorrevole per un tipo di evento + chiave (es. email o IP).

    Ritorna True se la richiesta è concessa (ed la registra), False se il limite
    per la finestra corrente è già stato raggiunto (in quel caso NON registra
    un evento aggiuntivo, per non allungare artificialmente il blocco)."""
    now = datetime.now(timezone.utc)
    since = now - timedelta(minutes=window_minutes)
    count = await COLLECTION.count_documents({
        "kind": kind,
        "key": key,
        "created_at": {"$gte": since},
    })
    if count >= max_attempts:
        return False
    await COLLECTION.insert_one({"kind": kind, "key": key, "created_at": now})
    return True

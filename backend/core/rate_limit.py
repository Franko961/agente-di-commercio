from datetime import datetime, timedelta, timezone
from typing import Optional

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from core.database import db

# Un documento per (kind, key) — non più uno per tentativo — con un array
# "attempts" dei soli timestamp ancora dentro la finestra (i vecchi vengono
# filtrati via ad ogni chiamata). L'indice univoco su (kind, key) e il TTL su
# last_updated sono creati in startup_service.py.
COLLECTION = db.rate_limit_events


async def check_and_record(
    kind: str, key: Optional[str], max_attempts: int, window_minutes: int
) -> bool:
    """Contatore a finestra scorrevole per un tipo di evento + chiave (es. email o IP).

    Ritorna True se la richiesta è concessa (e la registra), False se il limite
    per la finestra corrente è già stato raggiunto (in quel caso NON registra
    un evento aggiuntivo, per non allungare artificialmente il blocco).

    Il "conta poi eventualmente inserisci" di prima erano due operazioni
    separate: due chiamate concorrenti sulla stessa (kind, key) potevano
    entrambe leggere lo stesso conteggio-sotto-soglia PRIMA che una delle due
    registrasse il proprio tentativo, superando così max_attempts in una
    singola raffica (es. tentativi di login in parallelo). find_one_and_update
    con una pipeline di aggiornamento esegue filtro-e-eventuale-append come
    UNA sola operazione atomica lato server: nessuna finestra in cui due
    chiamate concorrenti possano vedere lo stesso stato "non ancora scritto"."""
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    since_iso = (now - timedelta(minutes=window_minutes)).isoformat()

    pipeline = [
        {
            "$set": {
                "attempts": {
                    "$filter": {
                        "input": {"$ifNull": ["$attempts", []]},
                        "cond": {"$gte": ["$$this", since_iso]},
                    },
                },
            }
        },
        {
            "$set": {
                "attempts": {
                    "$cond": [
                        {"$lt": [{"$size": "$attempts"}, max_attempts]},
                        {"$concatArrays": ["$attempts", [now_iso]]},
                        "$attempts",
                    ],
                },
                "last_updated": now,
            }
        },
    ]
    try:
        doc = await COLLECTION.find_one_and_update(
            {"kind": kind, "key": key},
            pipeline,
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
    except DuplicateKeyError:
        # Due chiamate concorrenti su una (kind, key) MAI vista prima possono
        # entrambe tentare di crearla: la seconda perde la corsa sull'indice
        # univoco. Il documento ormai esiste già, quindi ritentare una volta
        # diventa un semplice update atomico, non più un insert.
        doc = await COLLECTION.find_one_and_update(
            {"kind": kind, "key": key},
            pipeline,
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )

    attempts = doc.get("attempts") or []
    # Concesso solo se il tentativo di ADESSO è stato davvero aggiunto in
    # fondo all'array: se il conteggio era già al limite, la pipeline lascia
    # l'array invariato e l'ultimo elemento non è now_iso.
    return bool(attempts) and attempts[-1] == now_iso

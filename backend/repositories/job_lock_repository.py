import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from pymongo.errors import DuplicateKeyError

from core.database import db


class JobLockRepository:
    """Lock distribuito per i cicli periodici avviati da ogni processo
    backend (vedi services/startup_service.py). Con una sola replica
    Railway ogni ciclo è naturalmente unico; con più repliche, ognuna
    avvia lo stesso asyncio.create_task allo stesso intervallo — senza un
    lock, sync Google Calendar, reset demo, alert anomalie, pulizia
    richieste demo/contatti, finalizzazione abbonamenti e recupero azioni
    AI bloccate partirebbero contemporaneamente su ogni replica,
    producendo email duplicate, sync concorrenti o carico raddoppiato sul
    database.

    Stesso pattern già validato in automation_run_repository.try_claim:
    insert_one atomico per il primo tentativo (l'indice univoco implicito
    su _id fa fallire con DuplicateKeyError chi arriva secondo), update_one
    con filtro sulla scadenza per i tentativi successivi (chi vince
    aggiorna locked_until, chi perde non trova più nulla da aggiornare e
    matched_count resta 0). Il lock ha una scadenza (locked_until, TTL
    applicativo confrontato a mano — non un indice Mongo) più breve
    dell'intervallo del ciclo che protegge: si libera da solo prima del
    giro successivo, senza bisogno di un unlock esplicito — anche se
    l'istanza che lo deteneva crasha a metà."""

    collection = db.job_locks

    async def try_acquire(self, job_name: str, ttl_seconds: int) -> Optional[str]:
        """Ritorna l'owner_id della prenotazione vinta (da passare a
        extend() per estenderla in sicurezza — vedi sotto), o None se il
        lock è già detenuto da un'altra istanza. Un owner_id nuovo (non
        legato al processo) per ogni chiamata vinta: rappresenta QUESTA
        specifica prenotazione, non "questa istanza" in generale — anche
        la stessa istanza che riconquista lo stesso job_name in un giro
        successivo ottiene un owner_id diverso, così un'estensione tardiva
        legata alla prenotazione precedente non può essere confusa con
        quella nuova."""
        now_iso = datetime.now(timezone.utc).isoformat()
        owner_id = str(uuid.uuid4())
        locked_until_iso = (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat()

        try:
            await self.collection.insert_one({"_id": job_name, "owner_id": owner_id, "locked_until": locked_until_iso})
            return owner_id
        except DuplicateKeyError:
            pass  # un lock esiste già: proviamo comunque a "rubarlo" sotto, se scaduto

        result = await self.collection.update_one(
            {"_id": job_name, "locked_until": {"$lt": now_iso}},
            {"$set": {"owner_id": owner_id, "locked_until": locked_until_iso}},
        )
        return owner_id if result.matched_count == 1 else None

    async def extend(self, job_name: str, owner_id: str, ttl_seconds: int) -> bool:
        """Allunga la scadenza di un lock, ma SOLO se ancora posseduto da
        owner_id (quello ritornato dalla chiamata a try_acquire che lo ha
        vinto) — il filtro su owner_id, non solo su job_name, è quello che
        rende sicura l'operazione: senza, un'istanza la cui esecuzione (tra
        il proprio try_acquire e la propria extend) dura più del ttl_seconds
        con cui aveva acquisito il lock potrebbe "rubare" indietro il lock
        nel frattempo legittimamente riconquistato da un'altra istanza.

        Ritorna False se l'estensione non si applica più (lock scaduto e
        riassegnato altrove nel frattempo): il chiamante non deve
        considerare l'effetto ottenuto (es. il cooldown anti-spam
        dell'alert anomalie) come impostato con successo."""
        locked_until_iso = (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat()
        result = await self.collection.update_one(
            {"_id": job_name, "owner_id": owner_id},
            {"$set": {"locked_until": locked_until_iso}},
        )
        return result.matched_count == 1


job_lock_repository = JobLockRepository()

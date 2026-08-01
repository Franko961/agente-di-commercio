from datetime import datetime, timedelta, timezone

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

    async def try_acquire(self, job_name: str, ttl_seconds: int) -> bool:
        now_iso = datetime.now(timezone.utc).isoformat()
        locked_until_iso = (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat()

        try:
            await self.collection.insert_one({"_id": job_name, "locked_until": locked_until_iso})
            return True
        except DuplicateKeyError:
            pass  # un lock esiste già: proviamo comunque a "rubarlo" sotto, se scaduto

        result = await self.collection.update_one(
            {"_id": job_name, "locked_until": {"$lt": now_iso}},
            {"$set": {"locked_until": locked_until_iso}},
        )
        return result.matched_count == 1

    async def extend(self, job_name: str, ttl_seconds: int) -> None:
        """Allunga la scadenza di un lock già acquisito da questa stessa
        istanza, senza ri-validare nulla (va chiamato solo subito dopo un
        try_acquire vinto). Usato dal ciclo di alert anomalie per
        trasformare il lock in un cooldown condiviso fra repliche dopo
        l'invio effettivo di un'email: senza questo, il cooldown
        anti-spam viveva solo in una variabile di processo
        (_last_alert_sent_at), invisibile alle altre repliche, che
        avrebbero potuto rimandare lo stesso alert al giro successivo."""
        locked_until_iso = (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat()
        await self.collection.update_one(
            {"_id": job_name},
            {"$set": {"locked_until": locked_until_iso}},
        )


job_lock_repository = JobLockRepository()

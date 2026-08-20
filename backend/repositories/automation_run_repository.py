from datetime import datetime, timedelta, timezone
from typing import Optional

from pymongo.errors import DuplicateKeyError

from core.database import db


class AutomationRunRepository:
    """Traccia, per ogni coppia (automazione, entità target — es. una
    specifica offerta/cliente/lead), l'esito dell'ultima esecuzione: serve
    sia a evitare di rieseguire la stessa azione più volte per la stessa
    condizione (dedup), sia a contare i tentativi falliti consecutivi per
    poter smettere di ritentare dopo una soglia (vedi AUTOMATION_MAX_ATTEMPTS
    in core/config.py).

    Con una sola replica del backend, un controllo ("è già stata eseguita?")
    seguito dall'esecuzione e poi dalla registrazione del risultato basta a
    evitare i doppioni. Con più repliche (Railway può scalare
    orizzontalmente), due istanze potrebbero superare il controllo entrambe
    prima che una delle due registri il risultato, eseguendo l'azione
    (invio email, creazione appuntamento, ecc.) due volte: l'indice univoco
    su (automation_id, target_id) impedirebbe due RECORD duplicati, ma non
    i due EFFETTI ESTERNI già avvenuti nel frattempo. try_claim() esiste
    apposta per questo: prenota atomicamente il diritto a eseguire PRIMA di
    farlo, così solo l'istanza che vince la prenotazione procede."""

    collection = db.automation_runs

    async def find_one(self, automation_id: str, target_id: str) -> Optional[dict]:
        return await self.collection.find_one(
            {"automation_id": automation_id, "target_id": target_id}, {"_id": 0}
        )

    async def try_claim(
        self, automation_id: str, user_id: str, target_type: str, target_id: str,
        cooldown_days: Optional[int] = None, stale_after_seconds: int = 300,
    ) -> bool:
        """Prenota atomicamente il diritto a eseguire l'azione per questa
        coppia (automazione, target), PRIMA che l'azione venga eseguita.
        Ritorna True solo per la chiamata che vince la prenotazione — è
        quella, e SOLO quella, che deve procedere a eseguire l'azione.

        Incorpora la stessa logica di dedup/retry/cooldown che prima viveva
        in un controllo separato (_should_run): nessun record esistente,
        oppure un tentativo precedente in 'error' (sotto la soglia di
        tentativi), oppure un 'ok' il cui cooldown_days configurato è
        trascorso, oppure un 'processing' rimasto bloccato oltre
        stale_after_seconds (un'istanza crashata a metà esecuzione — senza
        questo, quel target resterebbe bloccato per sempre).

        La prenotazione è atomica in due modi complementari:
        - se non esiste ancora nessun record, si tenta un insert_one: se
          due istanze ci provano nello stesso istante, l'indice univoco su
          (automation_id, target_id) fa fallire quella che arriva seconda
          con DuplicateKeyError, interpretato qui come "prenotazione persa",
          non come un errore;
        - se un record esiste già in uno stato che permette di ritentare,
          si usa un update_one il cui filtro include anche la condizione
          sullo stato atteso: se un'altra istanza ha già vinto e cambiato
          lo stato nel frattempo, questo update non trova più nulla da
          aggiornare (matched_count 0) e ritorna False."""
        now = datetime.now(timezone.utc)
        now_iso_str = now.isoformat()
        stale_before_iso = (now - timedelta(seconds=stale_after_seconds)).isoformat()

        try:
            await self.collection.insert_one({
                "automation_id": automation_id, "user_id": user_id,
                "target_type": target_type, "target_id": target_id,
                "status": "processing", "attempts": 0, "last_error": None,
                "claimed_at": now_iso_str, "updated_at": now_iso_str,
            })
            return True
        except DuplicateKeyError:
            pass  # un record esiste già: proviamo comunque a "rubarlo" sotto, se in uno stato riprenotabile

        or_conditions = [
            {"status": "error"},
            {"status": "processing", "claimed_at": {"$lt": stale_before_iso}},
        ]
        if cooldown_days:
            cooldown_cutoff_iso = (now - timedelta(days=cooldown_days)).isoformat()
            or_conditions.append({"status": "ok", "updated_at": {"$lt": cooldown_cutoff_iso}})

        result = await self.collection.update_one(
            {"automation_id": automation_id, "target_id": target_id, "$or": or_conditions},
            {"$set": {"status": "processing", "claimed_at": now_iso_str, "updated_at": now_iso_str}},
        )
        return result.matched_count == 1

    async def upsert(self, automation_id: str, user_id: str, target_type: str, target_id: str, data: dict) -> None:
        await self.collection.update_one(
            {"automation_id": automation_id, "target_id": target_id},
            {"$set": {
                "automation_id": automation_id,
                "user_id": user_id,
                "target_type": target_type,
                "target_id": target_id,
                **data,
            }},
            upsert=True,
        )

    async def find_many_by_automation(self, automation_id: str, limit: int = 200) -> list:
        return await self.collection.find({"automation_id": automation_id}, {"_id": 0}) \
            .sort("updated_at", -1).to_list(limit)

    async def delete_by_automation(self, automation_id: str, user_id: str) -> None:
        """Ripulisce lo storico esecuzioni quando l'automazione stessa viene
        cancellata, per non lasciare record orfani in questa collection.
        Filtrato anche per user_id: automation_id da solo non basta a
        isolare i tenant, un id valido per un altro account non deve poter
        cancellare le sue esecuzioni (stesso principio già applicato al
        repository automation_repository.delete)."""
        await self.collection.delete_many({"automation_id": automation_id, "user_id": user_id})


automation_run_repository = AutomationRunRepository()

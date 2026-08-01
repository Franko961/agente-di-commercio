import hashlib
import io
import json
import logging
import zipfile
from datetime import datetime, timezone

from fastapi import HTTPException

from core.database import db
from core.security import verify_password
from core.rate_limit import check_and_record
from services.storage_service import storage_get, storage_delete, sanitize_filename
from services.subscription_service import subscription_service

logger = logging.getLogger(__name__)

# Ogni collection che contiene dati riconducibili a un utente, con
# l'etichetta usata nel file di export. Va mantenuta aggiornata quando si
# aggiunge una nuova collection user-scoped — è la stessa lista usata sia per
# l'esportazione (art. 20 GDPR) sia per la cancellazione (art. 17): dimenticare
# una collection qui la lascerebbe fuori da entrambe, con conseguenze opposte
# ma ugualmente serie (dati non esportati, o dati non cancellati).
USER_SCOPED_COLLECTIONS = {
    "clienti": "clients",
    "lead": "leads",
    "appuntamenti": "appointments",
    "offerte": "offers",
    "ordini": "orders",
    "provvigioni": "commissions",
    "spese": "expenses",
    "prodotti": "products",
    "mandanti": "mandanti",
    "documenti": "documents",
    "conversazioni_ai": "ai_logs",
    "log_azioni_ai": "ai_action_logs",
    "log_email": "email_logs",
    "automazioni": "automations",
    "connessione_google_calendar": "google_calendar_connections",
    "notifiche_automazioni": "automation_notifications",
    "esecuzioni_automazioni": "automation_runs",
    "richiesta_demo": "demo_requests",
}

# Ogni altra collection MongoDB realmente usata nel progetto (vedi
# tests/test_gdpr_service.py::test_ogni_collection_reale_e_classificata, che
# scansiona il codice e pretende che qualunque collection nuova sia elencata
# qui SOPRA o qui SOTTO — altrimenti chi la aggiunge deve fermarsi a
# decidere consapevolmente dove va, invece di dimenticarla per omissione),
# con la motivazione per cui NON è scoped per utente in export/cancellazione:
EXCLUDED_FROM_USER_SCOPED_COLLECTIONS = {
    # Il documento utente stesso: gestito direttamente (non "dati collegati
    # all'utente", è l'account stesso), vedi profilo/db.users.delete_one.
    "users",
    # Log di responsabilità amministrativa: si conserva deliberatamente
    # DOPO la cancellazione dell'account (vedi commento su delete_account
    # più sotto), non è un dato personale nel senso del diritto all'oblio.
    "admin_audit_log",
    # Telemetria operativa a breve termine, già con TTL nativo che la
    # elimina automaticamente indipendentemente da qualunque account
    # (rate_limit_events: 2 ore; system_events: 30 giorni; api_metrics_minute:
    # 7 giorni — vedi startup_service.py/core/observability.py) — non è
    # "il dato dell'utente" nel senso della portabilità, è un cruscotto di
    # salute del servizio.
    "rate_limit_events",
    "system_events",
    "api_metrics_minute",
    # Dedup tecnico dei webhook di pagamento, indicizzato per id evento
    # esterno (Stripe/PayPal), non per utente: non è dato "dell'utente" da
    # esportare, e la sua utilità (evitare doppie elaborazioni dello stesso
    # evento) non dipende dall'esistenza dell'account.
    "paypal_webhook_events",
    "stripe_webhook_events",
    # Contatori tecnici (es. numero ordine progressivo per utente): non
    # sono dati personali in sé (solo un intero), ma vanno comunque ripuliti
    # alla cancellazione account per igiene — gestito con una delete_one
    # mirata in delete_account() (la chiave è "order_number:{user_id}", non
    # un campo user_id filtrale con la stessa query generica delle altre
    # collection qui sopra).
    "counters",
    # Richieste dal form contatti pubblico: NON collegate a uno user_id (chi
    # scrive potrebbe non avere nemmeno un account SalesFly), quindi non
    # raggiungibili da un export/cancellazione account — non c'è uno user_id
    # da seguire. La loro retention è comunque limitata: pulizia periodica a
    # 24 mesi, stesso principio di demo_requests (vedi
    # CONTACT_REQUEST_RETENTION_DAYS in startup_service.py).
    "contact_requests",
    # Lock distribuiti per i cicli periodici multi-replica (vedi
    # repositories/job_lock_repository.py): un documento per NOME DI JOB
    # tecnico (es. "demo_reset", "health_alert"), non per utente — nessun
    # dato personale, nessuno user_id da seguire.
    "job_locks",
}

# Campi da rimuovere sempre dall'export e mai includere: segreti tecnici che
# non sono "i dati dell'utente" nel senso previsto dal diritto alla
# portabilità, e la cui esposizione sarebbe anzi un rischio di sicurezza
# (token OAuth Google Calendar, hash password).
_STRIP_FIELDS = {"password_hash", "google_access_token", "google_refresh_token", "_id"}


def _strip(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k not in _STRIP_FIELDS}


class GdprService:
    async def export_user_data(self, user: dict) -> bytes:
        """Esportazione completa (art. 20 GDPR, diritto alla portabilità):
        un unico file .zip con un JSON leggibile di tutti i dati strutturati
        più i file dei documenti caricati (non solo i loro metadati — il
        contenuto reale, altrimenti l'export sarebbe incompleto per la parte
        più sensibile, contratti/firme)."""
        user_id = user["id"]

        # Limite di frequenza: è un'operazione pesante (zip con tutti i
        # documenti, letti singolarmente da S3), non pensata per essere
        # richiamata di continuo — né per errore né per un uso malevolo di
        # una sessione compromessa.
        ok = await check_and_record("gdpr_export", user_id, max_attempts=5, window_minutes=60)
        if not ok:
            raise HTTPException(429, "Troppe richieste di esportazione, riprova più tardi")
        bundle = {
            "esportato_il": datetime.now(timezone.utc).isoformat(),
            "profilo": _strip(await db.users.find_one({"id": user_id}, {"_id": 0}) or {}),
        }
        for label, collection_name in USER_SCOPED_COLLECTIONS.items():
            docs = await db[collection_name].find({"user_id": user_id}, {"_id": 0}).to_list(20000)
            bundle[label] = [_strip(d) for d in docs]

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("dati.json", json.dumps(bundle, default=str, ensure_ascii=False, indent=2))

            # Documenti: contenuto reale dei file, non solo i metadati già
            # inclusi in dati.json. Recuperati singolarmente da S3 — se uno
            # fallisce (file mancante/corrotto), l'export prosegue comunque
            # con gli altri, annotando l'errore invece di far fallire tutto.
            seen_names = {}
            for doc in bundle["documenti"]:
                storage_path = doc.get("storage_path")
                if not storage_path:
                    continue
                try:
                    content, _ = storage_get(storage_path)
                    # sanitize_filename anche qui, non solo alla creazione del
                    # documento: un nome impostato da payload["name"] prima di
                    # questa modifica potrebbe ancora contenere separatori di
                    # percorso; qui è la difesa in profondità che impedisce
                    # comunque a un nome del genere di finire come "arcname"
                    # dentro lo zip (zipfile non protegge da solo da percorsi
                    # tipo "../../evil.sh" nel nome della voce).
                    name = sanitize_filename(doc.get("original_filename") or doc.get("name") or doc["id"])
                    seen_names[name] = seen_names.get(name, 0) + 1
                    if seen_names[name] > 1:
                        stem, _, ext = name.rpartition(".")
                        name = f"{stem or name} ({seen_names[name]}).{ext}" if ext else f"{name} ({seen_names[name]})"
                    zf.writestr(f"documenti/{name}", content)
                except Exception as e:
                    logger.warning(f"Export: impossibile includere il documento {doc.get('id')}: {e}")

        zip_buf.seek(0)
        return zip_buf.read()

    async def delete_account(self, user: dict, password: str) -> None:
        """Cancellazione account e cancellazione DEFINITIVA dei dati (art. 17
        GDPR, diritto all'oblio) — non un soft-delete: ogni documento viene
        rimosso davvero dal database, e i file su S3 vengono cancellati
        (non solo il loro record), altrimenti resterebbero comunque
        leggibili a chi conoscesse il percorso di storage.

        Richiede la password corrente come conferma: un'azione distruttiva e
        irreversibile non deve poter essere innescata da una sessione rubata
        senza che chi la esegue dimostri di conoscere la password — per
        questo, come per il login, i tentativi sono anche limitati nel
        tempo: senza, chi avesse solo il cookie di sessione (non la
        password, es. rubato via XSS o da un dispositivo condiviso) potrebbe
        provarne un numero illimitato per cancellare un account altrui."""
        user_id = user["id"]
        ok = await check_and_record("gdpr_delete_account", user_id, max_attempts=5, window_minutes=15)
        if not ok:
            raise HTTPException(429, "Troppi tentativi, riprova più tardi")

        full_user = await db.users.find_one({"id": user["id"]})
        if not full_user or not verify_password(password, full_user.get("password_hash", "")):
            raise HTTPException(403, "Password non corretta")

        # Ferma prima gli addebiti ricorrenti: cancellare l'account senza
        # disdire l'abbonamento lascerebbe l'utente a pagare per un servizio
        # che non esiste più.
        try:
            await subscription_service.cancel_subscription(user)
        except Exception as e:
            logger.warning(f"Cancellazione abbonamento durante eliminazione account fallita: {e}")

        # Cancella davvero i file dei documenti da S3, non solo i record.
        documents = await db.documents.find({"user_id": user_id}, {"_id": 0, "storage_path": 1}).to_list(20000)
        for doc in documents:
            storage_path = doc.get("storage_path")
            if not storage_path:
                continue
            try:
                storage_delete(storage_path)
            except Exception as e:
                logger.warning(f"Eliminazione file S3 durante eliminazione account fallita: {e}")

        for collection_name in USER_SCOPED_COLLECTIONS.values():
            await db[collection_name].delete_many({"user_id": user_id})

        # Contatore ordini: chiave "order_number:{user_id}" (vedi
        # order_repository.next_order_number), non un campo user_id
        # filtrabile con la query generica del loop sopra — va ripulito a
        # parte, altrimenti resterebbe orfano nel DB indefinitamente.
        await db.counters.delete_one({"_id": f"order_number:{user_id}"})

        # Traccia di sicurezza dell'eliminazione: si conserva DOPO la
        # cancellazione dell'account (a differenza dei dati sopra), ma
        # email e user_id restano dati riconducibili a una persona — non lo
        # si può considerare "non personale" solo perché vive nel log di
        # audit. La sua conservazione è comunque giustificata da un
        # interesse legittimo di sicurezza specifico (poter verificare, in
        # caso di contestazione "non sono stato io a cancellare il mio
        # account", che la richiesta di cancellazione era autenticata con
        # la password corretta — vedi verify_password sopra), non da
        # un'esenzione generica dal diritto alla protezione dei dati.
        # Applicati di conseguenza tutti gli accorgimenti richiesti in
        # questi casi:
        # - retention definita, non indefinita: TTL parziale dedicato solo
        #   a questo tipo di voce (SELF_DELETE_AUDIT_RETENTION_DAYS in
        #   startup_service.py, 12 mesi), diverso dall'audit amministrativo
        #   "normale" (azioni di uno staff admin su un altro utente), che
        #   resta senza scadenza per un motivo diverso (responsabilità
        #   verso terzi, non verso l'interessato stesso);
        # - minimizzazione: un solo campo con l'email (non più duplicata
        #   sia in "actor" sia in "detail" come prima di questa modifica);
        # - pseudonimizzazione: quel campo contiene l'hash SHA-256
        #   dell'email, non l'email in chiaro — sufficiente per confermare
        #   una email indicata da chi contesta la cancellazione, senza
        #   conservare il dato leggibile.
        try:
            email_hash = hashlib.sha256((full_user.get("email") or "").encode("utf-8")).hexdigest()
            await db.admin_audit_log.insert_one({
                "actor": "self",
                "action": "self_delete_account",
                "target_user_id": user_id,
                "detail": {"email_hash": email_hash},
                "created_at": datetime.now(timezone.utc),
            })
        except Exception:
            pass

        await db.users.delete_one({"id": user_id})


gdpr_service = GdprService()

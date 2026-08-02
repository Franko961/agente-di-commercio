import asyncio
import logging
from datetime import datetime, timezone

from core.database import db, close_db
from repositories.job_lock_repository import job_lock_repository
from services.storage_service import init_storage

logger = logging.getLogger(__name__)

GOOGLE_CALENDAR_SYNC_INTERVAL_SECONDS = 5 * 60

# Intervallo di controllo più breve della soglia di "bloccata" (5 minuti,
# vedi STUCK_EXECUTION_THRESHOLD_SECONDS in ai_service.py): un'azione bloccata
# viene quindi recuperata entro circa un minuto dal superamento della soglia,
# non solo al prossimo giro di sync di 5 minuti.
STUCK_AI_ACTION_CHECK_INTERVAL_SECONDS = 60

# Alert su anomalie: ogni 15 minuti si guarda il tasso di fallimento/errore
# degli ultimi 15 minuti; se supera la soglia (e il campione è abbastanza
# grande da non essere rumore, es. non allertare per 1 fallimento su 1
# richiesta) viene inviata un'email all'admin, con un tempo minimo tra un
# alert e il successivo per non spammare mentre il problema persiste.
ALERT_CHECK_INTERVAL_SECONDS = 15 * 60
ALERT_COOLDOWN_SECONDS = 60 * 60
ALERT_ERROR_RATE_THRESHOLD_PCT = 20
ALERT_MIN_SAMPLE_SIZE = 5

# Ogni quanto ripulire e riseminare i dati dell'account demo condiviso
# (is_demo=True). L'account è sola lettura sui dati CRM (ogni scrittura è
# già bloccata a monte da forbid_demo_write — vedi demo_reset_service.py per
# il dettaglio), quindi questo ciclo non serve più a "pulire le modifiche
# dei visitatori" come strategia primaria: è una rete di sicurezza residua
# e riporta comunque i dati seminati a uno stato pulito nel tempo.
# Abbastanza raro da non interrompere una sessione di prova in corso (una
# demo dura tipicamente pochi minuti), abbastanza frequente da non lasciare
# a lungo un eventuale dato residuo.
DEMO_RESET_INTERVAL_SECONDS = 6 * 60 * 60

# Ogni quanto finalizzare le disdette di abbonamento il cui periodo già
# pagato (cancel_at) è terminato: per Stripe è solo una rete di sicurezza
# (il webhook customer.subscription.deleted lo fa già alla scadenza reale),
# per PayPal è l'UNICO meccanismo che porta subscription_status a
# "cancelled" (PayPal non ha un evento equivalente a fine periodo, la
# cancellazione lato loro è già immediata alla richiesta — vedi
# subscription_service.cancel_subscription). Un'ora di ritardo massimo
# sull'aggiornamento del campo status è accettabile: l'accesso stesso è già
# bloccato da is_subscription_active() indipendentemente da questo ciclo.
CANCEL_FINALIZE_INTERVAL_SECONDS = 60 * 60

# Le richieste demo (form pubblico "richiedi accesso") contengono dati
# personali di contatto (nome, email, telefono, azienda, IP) raccolti senza
# un rapporto contrattuale in corso — per minimizzazione dei dati (GDPR) non
# vanno conservate a tempo indeterminato. 24 mesi è una finestra ragionevole
# per finalità di analisi commerciale/marketing, oltre la quale il dato non
# serve più allo scopo per cui è stato raccolto.
DEMO_REQUEST_RETENTION_DAYS = 730
DEMO_REQUEST_CLEANUP_INTERVAL_SECONDS = 24 * 60 * 60

# Stesso principio di DEMO_REQUEST_RETENTION_DAYS sopra: i messaggi dal form
# contatti pubblico (nome, email, telefono, messaggio) sono dati personali
# raccolti senza un rapporto contrattuale in corso — a differenza delle
# richieste demo, qui non viene nemmeno creato un account (nessun user_id da
# collegare), quindi questa è la SOLA rete di minimizzazione per questi dati.
CONTACT_REQUEST_RETENTION_DAYS = 730
CONTACT_REQUEST_CLEANUP_INTERVAL_SECONDS = 24 * 60 * 60

# Retention della voce di audit "self_delete_account" (vedi
# gdpr_service.delete_account): NON è coperta dall'assenza di TTL applicata
# al resto dell'audit amministrativo qui sotto — quella riguarda azioni di
# uno STAFF admin su un altro utente (interesse legittimo di
# responsabilità/sicurezza su terzi, senza scadenza), mentre qui l'"attore"
# e il "bersaglio" sono la STESSA persona che sta esercitando il proprio
# diritto all'oblio (art. 17 GDPR): conservare a tempo indeterminato
# l'email di chi ha appena chiesto la cancellazione dei propri dati non è
# minimizzazione. La motivazione per conservarla comunque un periodo
# limitato è di sicurezza (poter verificare, in caso di contestazione "non
# sono stato io a cancellare il mio account", che la richiesta risultava
# autenticata con la password corretta) — 12 mesi è una finestra
# ragionevole per questo tipo di contestazione, oltre la quale il dato non
# serve più allo scopo. L'email stessa viene salvata solo come hash (vedi
# gdpr_service.py), mai in chiaro.
SELF_DELETE_AUDIT_RETENTION_DAYS = 365

# Ognuno dei cicli sotto è protetto da job_lock_repository (vedi
# repositories/job_lock_repository.py) con una scadenza volutamente più
# breve del proprio intervallo: con più repliche Railway, solo l'istanza
# che vince il lock esegue il ciclo in quel giro; il lock scade comunque
# prima del giro successivo, così una qualunque replica (non
# necessariamente la stessa) può vincerlo la volta dopo. automation_engine
# fa eccezione: ha già una propria dedup più fine, per singola coppia
# automazione/target (vedi automation_run_repository.try_claim), quindi un
# lock a livello di intero ciclo non serve.
_gcal_sync_task = None
_stuck_ai_action_task = None
_health_alert_task = None
_automation_engine_task = None
_demo_reset_task = None
_cancel_finalize_task = None
_demo_request_cleanup_task = None
_contact_request_cleanup_task = None


async def _google_calendar_sync_loop() -> None:
    from services.google_calendar_service import google_calendar_service
    while True:
        try:
            await asyncio.sleep(GOOGLE_CALENDAR_SYNC_INTERVAL_SECONDS)
            if not await job_lock_repository.try_acquire("google_calendar_sync", ttl_seconds=GOOGLE_CALENDAR_SYNC_INTERVAL_SECONDS - 30):
                continue
            await google_calendar_service.sync_all_connected_accounts()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Ciclo di sync Google Calendar fallito: {e}")


async def _stuck_ai_action_cleanup_loop() -> None:
    """Recupera periodicamente le azioni AI rimaste bloccate in
    'in_esecuzione' (tipicamente per un crash/riavvio del server a metà
    dell'esecuzione confermata di una vendita o di una spesa), segnandole
    'fallita' invece di lasciarle bloccate per sempre. Non riesegue mai
    l'azione: vedi AiService.reclaim_stuck_executions per i dettagli."""
    from services.ai_service import ai_service
    while True:
        try:
            await asyncio.sleep(STUCK_AI_ACTION_CHECK_INTERVAL_SECONDS)
            if not await job_lock_repository.try_acquire("stuck_ai_action_cleanup", ttl_seconds=STUCK_AI_ACTION_CHECK_INTERVAL_SECONDS - 15):
                continue
            reclaimed = await ai_service.reclaim_stuck_executions()
            if reclaimed:
                logger.warning(
                    f"{reclaimed} azione/i AI bloccata/e in 'in_esecuzione' da "
                    "troppo tempo: segnata/e come 'fallita'."
                )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Ciclo di recupero azioni AI bloccate fallito: {e}")


async def _demo_reset_loop() -> None:
    from services.demo_reset_service import demo_reset_service
    while True:
        try:
            await asyncio.sleep(DEMO_RESET_INTERVAL_SECONDS)
            if not await job_lock_repository.try_acquire("demo_reset", ttl_seconds=DEMO_RESET_INTERVAL_SECONDS - 300):
                continue
            count = await demo_reset_service.reset_all_demo_accounts()
            if count:
                logger.info(f"Reset periodico demo: {count} account ripuliti e riseminati")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Ciclo di reset periodico account demo fallito: {e}")


async def _cancel_finalize_loop() -> None:
    """Porta a 'cancelled' gli abbonamenti il cui periodo già pagato
    (cancel_at) è terminato. Vedi CANCEL_FINALIZE_INTERVAL_SECONDS per il
    perché serve soprattutto per PayPal."""
    while True:
        try:
            await asyncio.sleep(CANCEL_FINALIZE_INTERVAL_SECONDS)
            if not await job_lock_repository.try_acquire("cancel_finalize", ttl_seconds=CANCEL_FINALIZE_INTERVAL_SECONDS - 300):
                continue
            now_iso = datetime.now(timezone.utc).isoformat()
            result = await db.users.update_many(
                {"subscription_status": "active", "cancel_at": {"$ne": None, "$lte": now_iso}},
                {"$set": {"subscription_status": "cancelled"}, "$unset": {"cancel_at": ""}},
            )
            if result.modified_count:
                logger.info(f"Finalizzate {result.modified_count} disdette di abbonamento con periodo pagato scaduto")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Ciclo di finalizzazione disdette fallito: {e}")


async def _demo_request_cleanup_loop() -> None:
    """Elimina periodicamente le richieste demo più vecchie di
    DEMO_REQUEST_RETENTION_DAYS (vedi commento lì sopra sul perché)."""
    from datetime import timedelta
    from repositories.demo_request_repository import demo_request_repository
    while True:
        try:
            await asyncio.sleep(DEMO_REQUEST_CLEANUP_INTERVAL_SECONDS)
            if not await job_lock_repository.try_acquire("demo_request_cleanup", ttl_seconds=DEMO_REQUEST_CLEANUP_INTERVAL_SECONDS - 300):
                continue
            cutoff = (datetime.now(timezone.utc) - timedelta(days=DEMO_REQUEST_RETENTION_DAYS)).isoformat()
            deleted = await demo_request_repository.delete_older_than(cutoff)
            if deleted:
                logger.info(f"Pulizia richieste demo: eliminate {deleted} richieste più vecchie di {DEMO_REQUEST_RETENTION_DAYS} giorni")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Ciclo di pulizia richieste demo fallito: {e}")


async def _contact_request_cleanup_loop() -> None:
    """Elimina periodicamente i messaggi dal form contatti più vecchi di
    CONTACT_REQUEST_RETENTION_DAYS (vedi commento lì sopra sul perché)."""
    from datetime import timedelta
    from repositories.contact_request_repository import contact_request_repository
    while True:
        try:
            await asyncio.sleep(CONTACT_REQUEST_CLEANUP_INTERVAL_SECONDS)
            if not await job_lock_repository.try_acquire("contact_request_cleanup", ttl_seconds=CONTACT_REQUEST_CLEANUP_INTERVAL_SECONDS - 300):
                continue
            cutoff = (datetime.now(timezone.utc) - timedelta(days=CONTACT_REQUEST_RETENTION_DAYS)).isoformat()
            deleted = await contact_request_repository.delete_older_than(cutoff)
            if deleted:
                logger.info(f"Pulizia messaggi contatti: eliminati {deleted} messaggi più vecchi di {CONTACT_REQUEST_RETENTION_DAYS} giorni")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Ciclo di pulizia messaggi contatti fallito: {e}")


# Endpoint le cui risposte d'errore sono l'esito ATTESO di un controllo, non
# un sintomo di guasto: GET /api/auth/me risponde 401 ogni volta che chi
# naviga il sito non ha (più) una sessione valida — visitatore anonimo,
# sessione scaduta, logout — che è la risposta corretta a "sono
# autenticato?", non un errore di sistema. Includerlo nell'alert anomalie
# genera falsi allarmi ad ogni manciata di visite anonime, specialmente con
# poco traffico (con MIN_SAMPLE_SIZE=5 bastano 2 richieste su 5 per superare
# la soglia del 20%).
_BENIGN_ENDPOINT_ERRORS = {("GET", "/api/auth/me")}


def _endpoint_problems(most_errors: list) -> list:
    """Filtra health['endpoints']['most_errors'] escludendo le combinazioni
    endpoint+status note come attese (vedi _BENIGN_ENDPOINT_ERRORS), e
    ritorna le righe di descrizione per l'email di alert per quelle
    rimanenti che superano le soglie di campione/tasso d'errore. Estratta
    dal ciclo principale per poter essere testata senza dover far girare
    l'intero loop asincrono."""
    problems = []
    for e in most_errors:
        if (e["method"], e["path"]) in _BENIGN_ENDPOINT_ERRORS:
            continue
        if e["count"] >= ALERT_MIN_SAMPLE_SIZE and e["error_rate_pct"] >= ALERT_ERROR_RATE_THRESHOLD_PCT:
            problems.append(
                f"{e['method']} {e['path']}: {e['error_rate_pct']}% errori "
                f"({e['status_4xx'] + e['status_5xx']}/{e['count']})"
            )
    return problems


async def _health_alert_loop() -> None:
    """Controlla periodicamente il tasso di fallimento di chiamate AI, invii
    email, sync Calendar ed endpoint API nella finestra recente, avvisando
    l'admin via email (già configurata tramite ADMIN_NOTIFY_EMAIL, nessun
    servizio nuovo da collegare) se supera una soglia — con un tempo minimo
    tra un alert e il successivo per non spammare mentre il problema persiste.

    Il cooldown anti-spam vive nello stesso job_lock_repository usato per
    evitare il doppio controllo (vedi commento sopra _gcal_sync_task): dopo
    un invio riuscito, il lock viene esteso fino a ALERT_COOLDOWN_SECONDS
    invece della sua normale, breve scadenza. Prima era una variabile di
    processo (_last_alert_sent_at): con più repliche Railway, ognuna aveva
    il proprio cooldown "privato", quindi un problema persistente poteva
    generare un alert per replica invece di uno solo condiviso."""
    from services.health_service import health_service
    from services.email_service import send_email
    from core.config import ADMIN_NOTIFY_EMAIL

    while True:
        try:
            await asyncio.sleep(ALERT_CHECK_INTERVAL_SECONDS)
            lock_owner = await job_lock_repository.try_acquire("health_alert", ttl_seconds=ALERT_CHECK_INTERVAL_SECONDS - 60)
            if not lock_owner:
                continue
            health = await health_service.get_health(hours=ALERT_CHECK_INTERVAL_SECONDS / 3600)

            problems = []
            for key, label in [("ai", "chiamate AI"), ("email", "invii email"), ("calendar_sync", "sync Google Calendar"), ("automation_run", "esecuzioni automazioni")]:
                stats = health[key]
                if stats["total"] >= ALERT_MIN_SAMPLE_SIZE and stats["failure_rate_pct"] >= ALERT_ERROR_RATE_THRESHOLD_PCT:
                    problems.append(f"{label}: {stats['failure_rate_pct']}% di fallimenti ({stats['failure']}/{stats['total']})")
            problems.extend(_endpoint_problems(health["endpoints"]["most_errors"]))

            if not problems:
                continue

            body = "".join(f"<li>{p}</li>" for p in problems)
            sent = await send_email(
                ADMIN_NOTIFY_EMAIL,
                "⚠️ Salesfly — anomalie rilevate",
                f"<p>Rilevate le seguenti anomalie negli ultimi {ALERT_CHECK_INTERVAL_SECONDS // 60} minuti:</p><ul>{body}</ul>",
            )
            if sent:
                await job_lock_repository.extend("health_alert", lock_owner, ttl_seconds=ALERT_COOLDOWN_SECONDS)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Ciclo di controllo anomalie fallito: {e}")


async def _automation_engine_loop() -> None:
    """Ciclo periodico del motore delle automazioni personalizzabili
    (services.automation_engine): controlla le condizioni di tutte le
    regole attive di tutti gli utenti ed esegue le azioni corrispondenti
    (promemoria, task, email di follow-up). Vedi automation_engine.py per
    il dettaglio di valutazione/esecuzione/dedup."""
    from core.config import AUTOMATION_ENGINE_INTERVAL_SECONDS
    from services.automation_engine import automation_engine
    while True:
        try:
            await asyncio.sleep(AUTOMATION_ENGINE_INTERVAL_SECONDS)
            summary = await automation_engine.run_cycle()
            if summary["executed"] or summary["errors"]:
                logger.info(f"Ciclo automazioni: {summary}")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Ciclo motore automazioni fallito: {e}")


async def run_startup() -> None:
    # Init object storage (non-blocking on failure)
    try:
        if init_storage():
            logger.info("Object storage initialized")
        else:
            logger.warning("Object storage NOT initialized — uploads will fail")
    except Exception as e:
        logger.error(f"Storage init error: {e}")

    await db.users.create_index("email", unique=True)
    await db.clients.create_index([("user_id", 1)])
    await db.offers.create_index([("user_id", 1)])
    await db.documents.create_index([("user_id", 1), ("is_deleted", 1)])
    # Queste cinque collection sono lette per intero ad ogni caricamento della
    # dashboard (get_stats/get_today_brief), filtrate per user_id: senza
    # indice, ogni query è una scansione completa della collection su TUTTI
    # gli utenti, non solo un filtro sull'utente corrente.
    await db.leads.create_index([("user_id", 1)])
    await db.appointments.create_index([("user_id", 1)])
    await db.commissions.create_index([("user_id", 1)])
    await db.expenses.create_index([("user_id", 1)])
    await db.orders.create_index([("user_id", 1)])
    # Indice univoco su (user_id, numero_ordine): next_order_number() (vedi
    # repositories/order_repository.py) è già atomico via $inc e non collide
    # mai da solo, ma numero_ordine resta un campo modificabile a mano da
    # form (creazione/modifica ordine) — un valore digitato dall'utente
    # potrebbe altrimenti collidere con uno già esistente senza che nulla lo
    # impedisca. Partial: esclude i (rari) ordini storici privi del campo,
    # applicando il vincolo solo dove numero_ordine è presente.
    await db.orders.create_index(
        [("user_id", 1), ("numero_ordine", 1)],
        unique=True,
        partialFilterExpression={"numero_ordine": {"$exists": True}},
    )
    # Indice univoco su (user_id, source_offer_id): find_by_source_offer()
    # (vedi order_repository/order_service.create_from_offer) fa già da check
    # preventivo prima di creare l'ordine da un'offerta, ma da solo è un
    # check-then-act — due richieste concorrenti sulla stessa offerta (es. il
    # pulsante di stato e la firma digitale quasi simultanei) potrebbero
    # superarlo entrambe prima che il primo insert completi, creando due
    # ordini per la stessa offerta. Partial con $type "string": si applica
    # solo agli ordini generati da un'offerta, non ai normali ordini creati a
    # mano, che hanno tutti source_offer_id=None e altrimenti collidirebbero
    # tra loro (un $exists semplice includerebbe anche i null).
    await db.orders.create_index(
        [("user_id", 1), ("source_offer_id", 1)],
        unique=True,
        partialFilterExpression={"source_offer_id": {"$type": "string"}},
    )
    # TTL: gli eventi di rate limiting più vecchi di 2 ore vengono eliminati
    # automaticamente da MongoDB (le finestre usate sono tutte <= 15 minuti).
    await db.rate_limit_events.create_index("created_at", expireAfterSeconds=7200)
    # Indice composto: find_many() filtra sempre per user_id e ordina per
    # created_at desc, quindi questo indice copre sia il filtro che il sort.
    await db.ai_action_logs.create_index([("user_id", 1), ("created_at", -1)])
    # Indice per il recupero periodico delle azioni bloccate in
    # 'in_esecuzione' (reclaim_stale_executions), che filtra su questi due
    # campi senza scoping per utente.
    await db.ai_action_logs.create_index([("status", 1), ("execution_started_at", 1)])

    # Telemetria (vedi core/observability.py): TTL a 30/7 giorni — è un
    # cruscotto di salute recente, non un archivio permanente. L'indice su
    # (category, created_at) copre l'aggregazione per categoria usata da
    # health_service; quello su created_at da solo copre l'aggregazione per
    # endpoint/minuto in api_metrics_minute.
    await db.system_events.create_index([("category", 1), ("created_at", -1)])
    await db.system_events.create_index("created_at", expireAfterSeconds=30 * 24 * 3600)
    await db.api_metrics_minute.create_index("created_at", expireAfterSeconds=7 * 24 * 3600)
    # Audit amministrativo: nessun TTL di default, va conservato (è un log
    # di responsabilità, non solo di salute operativa) — vale per le azioni
    # di uno staff admin su un altro utente. Le voci "self_delete_account"
    # sono un caso diverso (vedi SELF_DELETE_AUDIT_RETENTION_DAYS sopra) e
    # hanno un TTL parziale dedicato, solo su quel tipo di voce.
    await db.admin_audit_log.create_index([("created_at", -1)])
    await db.admin_audit_log.create_index(
        "created_at",
        expireAfterSeconds=SELF_DELETE_AUDIT_RETENTION_DAYS * 24 * 3600,
        partialFilterExpression={"action": "self_delete_account"},
    )

    # Indici usati dal motore automazioni: dedup/retry per (automation_id,
    # target_id) e lettura notifiche per utente ordinate per data.
    await db.automation_runs.create_index([("automation_id", 1), ("target_id", 1)], unique=True)
    await db.automation_notifications.create_index([("user_id", 1), ("created_at", -1)])

    # L'indice univoco (user_id, period) limitava a una sola provvigione
    # manuale per mese — troppo restrittivo una volta aggiunti mandante/
    # cliente/tipo (es. un premio per un mandante e una rettifica per un
    # altro nello stesso mese). Va rimosso esplicitamente: creare solo il
    # nuovo indice non basta, quello univoco esistente in produzione
    # continuerebbe a rifiutare righe multiple sullo stesso mese finché non
    # viene tolto. drop_index in un try: un database nuovo (o dove è già
    # stato tolto) non ha questo indice da rimuovere, non deve bloccare
    # l'avvio dell'app.
    try:
        await db.manual_commissions.drop_index([("user_id", 1), ("period", 1)])
    except Exception:
        pass
    await db.manual_commissions.create_index([("user_id", 1)])

    global _gcal_sync_task, _stuck_ai_action_task, _health_alert_task, _automation_engine_task, _demo_reset_task, _cancel_finalize_task, _demo_request_cleanup_task, _contact_request_cleanup_task
    _gcal_sync_task = asyncio.create_task(_google_calendar_sync_loop())
    _stuck_ai_action_task = asyncio.create_task(_stuck_ai_action_cleanup_loop())
    _health_alert_task = asyncio.create_task(_health_alert_loop())
    _automation_engine_task = asyncio.create_task(_automation_engine_loop())
    _demo_reset_task = asyncio.create_task(_demo_reset_loop())
    _cancel_finalize_task = asyncio.create_task(_cancel_finalize_loop())
    _demo_request_cleanup_task = asyncio.create_task(_demo_request_cleanup_loop())
    _contact_request_cleanup_task = asyncio.create_task(_contact_request_cleanup_loop())


async def run_shutdown() -> None:
    if _gcal_sync_task:
        _gcal_sync_task.cancel()
    if _stuck_ai_action_task:
        _stuck_ai_action_task.cancel()
    if _health_alert_task:
        _health_alert_task.cancel()
    if _automation_engine_task:
        _automation_engine_task.cancel()
    if _demo_reset_task:
        _demo_reset_task.cancel()
    if _cancel_finalize_task:
        _cancel_finalize_task.cancel()
    if _demo_request_cleanup_task:
        _demo_request_cleanup_task.cancel()
    if _contact_request_cleanup_task:
        _contact_request_cleanup_task.cancel()
    close_db()

import asyncio
import logging

from repositories.job_lock_repository import job_lock_repository

logger = logging.getLogger(__name__)

GOOGLE_CALENDAR_SYNC_INTERVAL_SECONDS = 5 * 60

# Alert su anomalie: ogni 15 minuti si guarda il tasso di fallimento/errore
# degli ultimi 15 minuti; se supera la soglia (e il campione è abbastanza
# grande da non essere rumore, es. non allertare per 1 fallimento su 1
# richiesta) viene inviata un'email all'admin, con un tempo minimo tra un
# alert e il successivo per non spammare mentre il problema persiste.
ALERT_CHECK_INTERVAL_SECONDS = 15 * 60
ALERT_COOLDOWN_SECONDS = 60 * 60
ALERT_ERROR_RATE_THRESHOLD_PCT = 20
ALERT_MIN_SAMPLE_SIZE = 5

# Controlla periodicamente che le spese generate automaticamente da un
# compenso Personale o un costo Flotta (source "personale"/"flotta") siano
# ancora coerenti con il documento che le ha generate — vedi
# services/reconciliation_service.py per il perché possono divergere (niente
# transazione Mongo sul flusso a due scritture). Non ripara nulla da solo,
# avvisa solo l'admin via email per una revisione manuale: un'incoerenza
# economica non va corretta in automatico senza che una persona la veda
# prima. Ogni giorno è sufficiente: non è un problema che richieda una
# reazione entro minuti/ore, a differenza degli alert di anomalie sopra.
RECONCILIATION_CHECK_INTERVAL_SECONDS = 24 * 60 * 60


async def _google_calendar_sync_loop() -> None:
    from services.google_calendar_service import google_calendar_service

    while True:
        try:
            await asyncio.sleep(GOOGLE_CALENDAR_SYNC_INTERVAL_SECONDS)
            if not await job_lock_repository.try_acquire(
                "google_calendar_sync",
                ttl_seconds=GOOGLE_CALENDAR_SYNC_INTERVAL_SECONDS - 30,
            ):
                continue
            await google_calendar_service.sync_all_connected_accounts()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Ciclo di sync Google Calendar fallito: {e}")


async def _reconciliation_check_loop() -> None:
    """Segnala (via email admin) le spese Personale/Flotta orfane e i
    compensi/costi il cui expense_id non punta più a nessuna spesa. Vedi
    services/reconciliation_service.py e il commento sopra
    RECONCILIATION_CHECK_INTERVAL_SECONDS per il perché."""
    from core.config import ADMIN_NOTIFY_EMAIL
    from services.email_service import send_email
    from services.reconciliation_service import reconciliation_service

    while True:
        try:
            await asyncio.sleep(RECONCILIATION_CHECK_INTERVAL_SECONDS)
            if not await job_lock_repository.try_acquire(
                "reconciliation_check",
                ttl_seconds=RECONCILIATION_CHECK_INTERVAL_SECONDS - 300,
            ):
                continue
            result = await reconciliation_service.find_inconsistencies()
            orphan_expenses = result["orphan_expenses"]
            orphan_links = result["orphan_links"]
            if not orphan_expenses and not orphan_links:
                continue

            logger.warning(
                f"Riconciliazione Personale/Flotta: {len(orphan_expenses)} spese orfane, "
                f"{len(orphan_links)} compensi/costi senza spesa collegata"
            )
            rows = "".join(
                f"<li>Spesa orfana {e['expense_id']} (source={e['source']}, utente {e['user_id']})</li>"
                for e in orphan_expenses
            ) + "".join(
                f"<li>{l['source'].capitalize()} {l['id']} senza spesa collegata (utente {l['user_id']})</li>"
                for l in orphan_links
            )
            await send_email(
                ADMIN_NOTIFY_EMAIL,
                "⚠️ Salesfly — incoerenze Personale/Flotta ↔ Spese",
                f"<p>Trovate {len(orphan_expenses) + len(orphan_links)} incoerenze da rivedere manualmente:</p><ul>{rows}</ul>",
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Ciclo di riconciliazione Personale/Flotta fallito: {e}")


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
        if (
            e["count"] >= ALERT_MIN_SAMPLE_SIZE
            and e["error_rate_pct"] >= ALERT_ERROR_RATE_THRESHOLD_PCT
        ):
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
    evitare il doppio controllo (vedi commento sopra _gcal_sync_task in
    services.startup.scheduler): dopo un invio riuscito, il lock viene esteso
    fino a ALERT_COOLDOWN_SECONDS invece della sua normale, breve scadenza.
    Prima era una variabile di processo (_last_alert_sent_at): con più
    repliche Railway, ognuna aveva il proprio cooldown "privato", quindi un
    problema persistente poteva generare un alert per replica invece di uno
    solo condiviso."""
    from core.config import ADMIN_NOTIFY_EMAIL
    from services.email_service import send_email
    from services.health_service import health_service

    while True:
        try:
            await asyncio.sleep(ALERT_CHECK_INTERVAL_SECONDS)
            lock_owner = await job_lock_repository.try_acquire(
                "health_alert", ttl_seconds=ALERT_CHECK_INTERVAL_SECONDS - 60
            )
            if not lock_owner:
                continue
            health = await health_service.get_health(
                hours=ALERT_CHECK_INTERVAL_SECONDS / 3600
            )

            problems = []
            for key, label in [
                ("ai", "chiamate AI"),
                ("email", "invii email"),
                ("calendar_sync", "sync Google Calendar"),
                ("automation_run", "esecuzioni automazioni"),
            ]:
                stats = health[key]
                if (
                    stats["total"] >= ALERT_MIN_SAMPLE_SIZE
                    and stats["failure_rate_pct"] >= ALERT_ERROR_RATE_THRESHOLD_PCT
                ):
                    problems.append(
                        f"{label}: {stats['failure_rate_pct']}% di fallimenti ({stats['failure']}/{stats['total']})"
                    )
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
                await job_lock_repository.extend(
                    "health_alert", lock_owner, ttl_seconds=ALERT_COOLDOWN_SECONDS
                )
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

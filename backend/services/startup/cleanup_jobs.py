import asyncio
import logging
from datetime import datetime, timezone

from core.database import db
from repositories.job_lock_repository import job_lock_repository

logger = logging.getLogger(__name__)

# Intervallo di controllo più breve della soglia di "bloccata" (5 minuti,
# vedi STUCK_EXECUTION_THRESHOLD_SECONDS in ai_service.py): un'azione bloccata
# viene quindi recuperata entro circa un minuto dal superamento della soglia,
# non solo al prossimo giro di sync di 5 minuti.
STUCK_AI_ACTION_CHECK_INTERVAL_SECONDS = 60

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

# Un documento eliminato dall'utente (DELETE /api/documents/{id} o
# /api/employee-documents/{id}) resta recuperabile per questo numero di
# giorni (soft-delete, vedi document_repository.soft_delete) prima che
# services/document_trash_service lo cancelli per davvero, DB e file S3
# inclusi. 30 giorni è lo stesso ordine di grandezza usato comunemente per
# un "cestino" (es. Google Drive, Dropbox): abbastanza per rimediare a un
# click sbagliato, non così lungo da vanificare lo scopo della pulizia
# (spazio di storage occupato indefinitamente, il problema che risolve).
DOCUMENT_TRASH_RETENTION_DAYS = 30
DOCUMENT_TRASH_CLEANUP_INTERVAL_SECONDS = 24 * 60 * 60


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
            if not await job_lock_repository.try_acquire(
                "stuck_ai_action_cleanup",
                ttl_seconds=STUCK_AI_ACTION_CHECK_INTERVAL_SECONDS - 15,
            ):
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
            if not await job_lock_repository.try_acquire(
                "demo_reset", ttl_seconds=DEMO_RESET_INTERVAL_SECONDS - 300
            ):
                continue
            count = await demo_reset_service.reset_all_demo_accounts()
            if count:
                logger.info(
                    f"Reset periodico demo: {count} account ripuliti e riseminati"
                )
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
            if not await job_lock_repository.try_acquire(
                "cancel_finalize", ttl_seconds=CANCEL_FINALIZE_INTERVAL_SECONDS - 300
            ):
                continue
            now_iso = datetime.now(timezone.utc).isoformat()
            result = await db.users.update_many(
                {
                    "subscription_status": "active",
                    "cancel_at": {"$ne": None, "$lte": now_iso},
                },
                {
                    "$set": {"subscription_status": "cancelled"},
                    "$unset": {"cancel_at": ""},
                },
            )
            if result.modified_count:
                logger.info(
                    f"Finalizzate {result.modified_count} disdette di abbonamento con periodo pagato scaduto"
                )
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
            if not await job_lock_repository.try_acquire(
                "demo_request_cleanup",
                ttl_seconds=DEMO_REQUEST_CLEANUP_INTERVAL_SECONDS - 300,
            ):
                continue
            cutoff = (
                datetime.now(timezone.utc) - timedelta(days=DEMO_REQUEST_RETENTION_DAYS)
            ).isoformat()
            deleted = await demo_request_repository.delete_older_than(cutoff)
            if deleted:
                logger.info(
                    f"Pulizia richieste demo: eliminate {deleted} richieste più vecchie di {DEMO_REQUEST_RETENTION_DAYS} giorni"
                )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Ciclo di pulizia richieste demo fallito: {e}")


async def _document_trash_cleanup_loop() -> None:
    """Cancella per davvero (DB + file S3) i documenti che l'utente ha
    eliminato (soft-delete) più di DOCUMENT_TRASH_RETENTION_DAYS giorni fa.
    Vedi services/document_trash_service.py e il commento sopra
    DOCUMENT_TRASH_RETENTION_DAYS per il perché serve."""
    from services.document_trash_service import document_trash_service

    while True:
        try:
            await asyncio.sleep(DOCUMENT_TRASH_CLEANUP_INTERVAL_SECONDS)
            if not await job_lock_repository.try_acquire(
                "document_trash_cleanup",
                ttl_seconds=DOCUMENT_TRASH_CLEANUP_INTERVAL_SECONDS - 300,
            ):
                continue
            purged = await document_trash_service.purge_expired(
                DOCUMENT_TRASH_RETENTION_DAYS
            )
            if purged:
                logger.info(
                    f"Pulizia cestino documenti: eliminati definitivamente {purged} documenti più vecchi di {DOCUMENT_TRASH_RETENTION_DAYS} giorni"
                )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Ciclo di pulizia cestino documenti fallito: {e}")


async def _contact_request_cleanup_loop() -> None:
    """Elimina periodicamente i messaggi dal form contatti più vecchi di
    CONTACT_REQUEST_RETENTION_DAYS (vedi commento lì sopra sul perché)."""
    from datetime import timedelta

    from repositories.contact_request_repository import contact_request_repository

    while True:
        try:
            await asyncio.sleep(CONTACT_REQUEST_CLEANUP_INTERVAL_SECONDS)
            if not await job_lock_repository.try_acquire(
                "contact_request_cleanup",
                ttl_seconds=CONTACT_REQUEST_CLEANUP_INTERVAL_SECONDS - 300,
            ):
                continue
            cutoff = (
                datetime.now(timezone.utc)
                - timedelta(days=CONTACT_REQUEST_RETENTION_DAYS)
            ).isoformat()
            deleted = await contact_request_repository.delete_older_than(cutoff)
            if deleted:
                logger.info(
                    f"Pulizia messaggi contatti: eliminati {deleted} messaggi più vecchi di {CONTACT_REQUEST_RETENTION_DAYS} giorni"
                )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Ciclo di pulizia messaggi contatti fallito: {e}")

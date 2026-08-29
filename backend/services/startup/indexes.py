from core.database import db

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


async def create_indexes() -> None:
    await db.users.create_index("email", unique=True)
    # clients/offers: l'indice su solo (user_id) creato qui in passato viene
    # sostituito più sotto da uno composto (user_id, mandante_id/mandante_ids)
    # — un indice composto serve già da solo anche le query che filtrano solo
    # su user_id (prefisso), quindi il vecchio va tolto esplicitamente invece
    # di lasciarlo duplicato e inutile in produzione (stesso principio già
    # usato per manual_commissions/automation_runs più sotto in questa funzione).
    try:
        await db.clients.drop_index([("user_id", 1)])
    except Exception:
        pass
    try:
        await db.offers.drop_index([("user_id", 1)])
    except Exception:
        pass
    await db.documents.create_index([("user_id", 1), ("is_deleted", 1)])
    # Non filtrato per user_id: usato dal ciclo periodico di pulizia cestino
    # (services.startup.cleanup_jobs._document_trash_cleanup_loop), che
    # scansiona i documenti soft-deleted di TUTTI gli utenti.
    await db.documents.create_index([("is_deleted", 1), ("deleted_at", 1)])
    await db.employee_documents.create_index([("is_deleted", 1), ("deleted_at", 1)])
    # Queste cinque collection sono lette per intero ad ogni caricamento della
    # dashboard (get_stats/get_today_brief), filtrate per user_id: senza
    # indice, ogni query è una scansione completa della collection su TUTTI
    # gli utenti, non solo un filtro sull'utente corrente.
    # Copre sia find_many (elenco per dipendente, ordinato per clock_in)
    # sia find_open_session (la sessione ancora aperta, se esiste).
    await db.attendance_sessions.create_index(
        [("employee_id", 1), ("user_id", 1), ("clock_in", -1)]
    )
    # Indice parziale univoco: al massimo UN documento con clock_out=null
    # per dipendente. find_open_session() poi insert() in
    # attendance_service.clock_in_kiosk non è atomico da solo — due
    # timbrature d'ingresso simultanee dello stesso dipendente (es. doppio
    # tocco sul chiosco) potrebbero entrambe superare il controllo prima
    # che la prima abbia scritto, creando due sessioni aperte. Questo
    # indice è l'ultima linea di difesa: la seconda insert_one fallisce con
    # DuplicateKeyError, tradotto in ConflictError da
    # attendance_repository.insert.
    await db.attendance_sessions.create_index(
        [("employee_id", 1), ("user_id", 1)],
        unique=True,
        partialFilterExpression={"clock_out": None},
        name="unique_open_session_per_employee",
    )
    # (user_id, clock_in) senza employee_id in testa: serve a
    # find_clocked_in_between (vedi attendance_service.today_summary), che
    # filtra per TUTTI i dipendenti dell'utente in un colpo solo — l'indice
    # sopra (che parte da employee_id) non aiuterebbe qui, la query non lo
    # userebbe in modo efficiente senza filtrare anche per employee_id.
    await db.attendance_sessions.create_index([("user_id", 1), ("clock_in", 1)])
    # Indice univoco su (user_id, plate): find_by_plate() in
    # vehicle_service.create_vehicle/update_vehicle è già un check
    # preventivo, ma da solo è un check-then-act — due richieste di
    # creazione concorrenti con la stessa targa (già normalizzata da
    # models.vehicle.normalize_plate) potrebbero entrambe superarlo prima
    # che il primo insert completi. Questo indice è l'ultima linea di
    # difesa: la seconda insert_one/update_one fallisce con
    # DuplicateKeyError, tradotto in ValidationAppError da
    # vehicle_repository — stesso messaggio già usato dal pre-check.
    await db.vehicles.create_index([("user_id", 1), ("plate", 1)], unique=True)
    await db.leads.create_index([("user_id", 1)])
    await db.appointments.create_index([("user_id", 1)])
    # commissions/expenses/orders: stesso principio di clients/offers sopra
    # — il vecchio indice su solo (user_id) va tolto, un indice composto più
    # sotto lo sostituisce e lo serve già come prefisso.
    try:
        await db.commissions.drop_index([("user_id", 1)])
    except Exception:
        pass
    try:
        await db.expenses.drop_index([("user_id", 1)])
    except Exception:
        pass
    try:
        await db.orders.drop_index([("user_id", 1)])
    except Exception:
        pass
    # Filtro per mandante attivo: clients/offers/commissions/orders sono
    # tutte interrogate anche con {"user_id": ..., "mandante_id"/"mandante_ids": ...}
    # quando l'utente ha selezionato un mandante specifico nella barra
    # laterale (non solo "Tutti i mandanti") — sia dalle pagine di elenco
    # (Clienti/Offerte/Provvigioni/Ordini) sia da dashboard_service. Con il
    # solo indice su (user_id), quella query filtra ancora per mandante in
    # memoria dopo aver caricato TUTTI i documenti dell'utente. mandante_ids
    # su clients è un array (relazione molti-a-molti cliente↔mandante): un
    # indice composto su un campo array è comunque valido in MongoDB
    # (multikey index), copre lo stesso caso d'uso.
    await db.clients.create_index([("user_id", 1), ("mandante_ids", 1)])
    await db.offers.create_index([("user_id", 1), ("mandante_id", 1)])
    await db.commissions.create_index([("user_id", 1), ("mandante_id", 1)])
    await db.orders.create_index([("user_id", 1), ("mandante_id", 1)])
    # find_many() filtra sempre per user_id, opzionalmente per categoria e/o
    # intervallo di date, e ordina sempre per date desc — questo indice copre
    # sia il filtro sulla data sia il sort, non solo l'uguaglianza su user_id.
    await db.expenses.create_index([("user_id", 1), ("date", -1)])
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
    # rate_limit_events è passata da "un documento per tentativo" a "un
    # documento per (kind, key)" con un array di timestamp (vedi
    # core/rate_limit.check_and_record — fix della corsa tra il conteggio e
    # la scrittura, non più atomici separatamente). Il vecchio indice TTL su
    # created_at non esiste più in questo schema, va tolto esplicitamente
    # (drop_index in un try: un database nuovo non ce l'ha da rimuovere).
    try:
        await db.rate_limit_events.drop_index([("created_at", 1)])
    except Exception:
        pass
    # Indice univoco: find_one_and_update(upsert=True) su (kind, key) da solo
    # è un check-then-act per una chiave MAI vista prima — due chiamate
    # concorrenti potrebbero entrambe tentare di crearla. Questo indice è
    # l'ultima linea di difesa (la seconda perde con DuplicateKeyError,
    # gestito con un retry in check_and_record), stesso principio già usato
    # altrove in questa funzione (vehicles, orders, automation_runs).
    await db.rate_limit_events.create_index([("kind", 1), ("key", 1)], unique=True)
    # TTL su last_updated (non più su un singolo tentativo): 2 ore coprono
    # con margine la finestra più ampia usata oggi (60 minuti) — non è
    # comunque il meccanismo che garantisce la correttezza della finestra
    # scorrevole (quello lo fa il $filter dentro check_and_record ad ogni
    # chiamata), solo pulizia delle chiavi ormai inattive.
    await db.rate_limit_events.create_index("last_updated", expireAfterSeconds=7200)
    # Indice univoco su event_id: rende atomica _claim_webhook_event_once()
    # (vedi subscription_service.py) — un insert_one che fallisce da solo
    # con DuplicateKeyError alla seconda consegna dello stesso evento
    # webhook, invece del precedente "cerca poi eventualmente inserisci"
    # (due operazioni separate, quindi non atomico: due consegne quasi
    # simultanee dello stesso evento — Stripe e PayPal dichiarano entrambi
    # di poterlo fare — potevano passare il controllo prima che una delle
    # due registrasse l'id, elaborando l'evento due volte).
    await db.stripe_webhook_events.create_index("event_id", unique=True)
    await db.paypal_webhook_events.create_index("event_id", unique=True)
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
    await db.api_metrics_minute.create_index(
        "created_at", expireAfterSeconds=7 * 24 * 3600
    )
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
    #
    # L'indice univoco include anche user_id (non solo automation_id,
    # target_id): non cambia quali documenti vengono considerati duplicati
    # (automation_id è già globalmente univoco — gen_id() — quindi non può
    # comparire con due user_id diversi), ma rende esplicito nel modello
    # dati che l'isolamento tra utenti fa parte della chiave, invece di
    # dipendere solo dalla disciplina del codice applicativo (vedi il fix in
    # automation_run_repository.delete_by_automation). automation_id resta
    # il PRIMO campo dell'indice, non user_id: find_one/find_many_by_automation/
    # delete_by_automation filtrano tutte per automation_id (a volte da solo,
    # a volte con altri campi), e un indice composto è utile per una query
    # solo se i suoi campi iniziali coincidono con quelli del filtro — con
    # user_id in testa, quelle query smetterebbero di usare l'indice.
    #
    # drop_index in un try: un database nuovo (o dove è già stato aggiornato)
    # non ha il vecchio indice a 2 campi da rimuovere, non deve bloccare
    # l'avvio dell'app (stesso principio già usato sotto per manual_commissions).
    try:
        await db.automation_runs.drop_index([("automation_id", 1), ("target_id", 1)])
    except Exception:
        pass
    await db.automation_runs.create_index(
        [("automation_id", 1), ("user_id", 1), ("target_id", 1)], unique=True
    )
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

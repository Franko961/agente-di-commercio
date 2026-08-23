import asyncio
import logging
import requests
from datetime import datetime, timezone
from fastapi import HTTPException, Request
from pymongo.errors import DuplicateKeyError

from core.config import (
    PLANS, TRIAL_DAYS, STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET,
    PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, PAYPAL_API_BASE, PAYPAL_WEBHOOK_ID,
    FRONTEND_URL,
)
from core.database import db
from core.security import verify_password
from core.subscription_utils import is_subscription_active
from core.rate_limit import check_and_record
from repositories.user_repository import user_repository

logger = logging.getLogger(__name__)

# Collection per l'idempotenza dei webhook PayPal: PayPal può reinviare lo stesso
# evento più volte, quindi teniamo traccia degli id già processati.
paypal_webhook_events = db.paypal_webhook_events

# Stesso principio per Stripe: anche Stripe può reinviare lo stesso evento
# più volte (retry su timeout/errore nostro, o solo per garanzia di
# consegna) — nessun handler qui sotto ha oggi un effetto collaterale non
# idempotente, ma tracciare gli id già processati evita che lo diventi in
# futuro senza che ce ne accorgiamo (difesa preventiva, stesso schema già
# in uso per PayPal).
stripe_webhook_events = db.stripe_webhook_events

# Stati PayPal che consideriamo "abbonamento attivo": la sola creazione (APPROVAL_PENDING)
# non basta, va confermato ACTIVE prima di sbloccare qualunque funzionalità a pagamento.
PAYPAL_ACTIVE_STATUSES = {"ACTIVE"}

# Alias mantenuto per compatibilità: la logica vive ora in core/subscription_utils.py
# (core non può dipendere da services, quindi la fonte di verità è lì).
subscription_active = is_subscription_active


async def _claim_webhook_event_once(collection, event_id: str, event_type: str) -> bool:
    """Reclama atomicamente un event_id di webhook (Stripe o PayPal):
    ritorna True solo alla PRIMA chiamata che ci riesce, False per ogni
    successiva (duplicato). Prima, "cerca poi eventualmente inserisci" erano
    due operazioni separate: due consegne quasi simultanee dello stesso
    evento (entrambi i provider dichiarano esplicitamente di poter reinviare
    lo stesso evento più volte) potevano passare il controllo find_one
    prima che una delle due scrivesse, elaborando l'evento due volte.
    insert_one fallisce da solo con DuplicateKeyError sul secondo tentativo
    grazie all'indice univoco su event_id (creato in startup_service.py) —
    un'unica operazione atomica lato server, nessuna finestra residua."""
    try:
        await collection.insert_one({"event_id": event_id, "event_type": event_type})
        return True
    except DuplicateKeyError:
        return False


class SubscriptionService:
    def __init__(self, repo=user_repository):
        self.repo = repo

    async def get_plans(self) -> dict:
        return {
            "plans": [{"id": k, **v} for k, v in PLANS.items()],
            "trial_days": TRIAL_DAYS,
        }

    async def _forbid_if_demo(self, user_id: str) -> dict:
        """L'account demo condiviso non deve poter avviare pagamenti/abbonamenti
        reali (Stripe/PayPal) né cancellarli: nessun visitatore anonimo deve
        poter toccare denaro vero o lo stato di fatturazione condiviso."""
        u = await self.repo.find_by_id(user_id)
        if u and u.get("is_demo"):
            raise HTTPException(403, "Questa azione non è disponibile nell'account demo")
        return u

    async def get_status(self, user: dict) -> dict:
        u = await self.repo.find_by_id(user["id"])
        return {
            "plan": u.get("plan", "base"),
            "status": u.get("subscription_status", "trial"),
            "trial_ends_at": u.get("trial_ends_at"),
            "cancel_at": u.get("cancel_at"),
            "active": subscription_active(u),
        }

    async def create_checkout_for_expired_account(self, payload: dict, ip_address: str = None) -> dict:
        """Avvia un checkout Stripe per un account con trial scaduto (quindi bloccato al
        login). Non richiede un cookie di sessione valido: verifica email+password una
        tantum per confermare che sia davvero il titolare dell'account, poi procede come
        create_stripe_session. Usato dalla schermata di pagamento mostrata al posto del
        login quando i 14 giorni di prova sono terminati."""
        email = (payload.get("email") or "").lower().strip()

        # Verifica una password proprio come /auth/login: stessa protezione
        # contro i tentativi ripetuti, altrimenti questo endpoint pubblico
        # sarebbe un secondo punto da cui tentare il brute-force di una
        # password senza incappare nel limite già impostato sul login.
        if email:
            email_ok = await check_and_record("checkout_expired_email", email, max_attempts=10, window_minutes=15)
            if not email_ok:
                raise HTTPException(status_code=429, detail="Troppi tentativi, riprova più tardi")
        if ip_address:
            ip_ok = await check_and_record("checkout_expired_ip", ip_address, max_attempts=30, window_minutes=15)
            if not ip_ok:
                raise HTTPException(status_code=429, detail="Troppi tentativi, riprova più tardi")

        password = payload.get("password") or ""
        user = await self.repo.find_by_email(email)
        if not user or not verify_password(password, user.get("password_hash", "")):
            raise HTTPException(status_code=401, detail="Credenziali non valide")
        return await self.create_stripe_session(user, payload)

    async def create_stripe_session(self, user: dict, payload: dict) -> dict:
        if not STRIPE_SECRET_KEY:
            raise HTTPException(500, "Stripe non configurato")

        plan_id = payload.get("plan", "base")
        plan = PLANS.get(plan_id)
        if not plan:
            raise HTTPException(400, "Piano non valido")

        try:
            import stripe
            stripe.api_key = STRIPE_SECRET_KEY

            # Crea o recupera customer Stripe
            u = await self._forbid_if_demo(user["id"])
            customer_id = u.get("stripe_customer_id")
            if not customer_id:
                customer = stripe.Customer.create(email=user["email"], name=u.get("name", ""))
                customer_id = customer.id
                await self.repo.update_by_id(user["id"], {"stripe_customer_id": customer_id})

            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                mode="subscription",
                line_items=[{"price": plan["stripe_price_id"], "quantity": 1}],
                success_url=f"{payload.get('return_url', FRONTEND_URL)}/abbonamento?success=stripe",
                cancel_url=f"{payload.get('return_url', FRONTEND_URL)}/abbonamento?cancelled=1",
                metadata={"user_id": user["id"], "plan": plan_id},
            )
            return {"url": session.url}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Stripe session error: {e}")
            raise HTTPException(500, str(e)[:200])

    async def handle_stripe_webhook(self, request: Request) -> dict:
        if not STRIPE_SECRET_KEY:
            raise HTTPException(500, "Stripe non configurato")
        # Fail-closed come il percorso PayPal (_verify_paypal_webhook_signature
        # rifiuta se PAYPAL_WEBHOOK_ID manca): senza questo controllo,
        # STRIPE_WEBHOOK_SECRET vuoto (default in core/config.py se la env
        # var non è impostata) farebbe verificare la firma con una chiave
        # HMAC vuota — non un errore per la libreria stripe, ma una "firma"
        # calcolabile da chiunque, che accetterebbe eventi Stripe falsificati
        # (es. un checkout.session.completed fabbricato che attiva un piano
        # a pagamento gratis).
        if not STRIPE_WEBHOOK_SECRET:
            logger.error("STRIPE_WEBHOOK_SECRET non configurato: rifiuto il webhook")
            raise HTTPException(500, "Stripe non configurato")
        try:
            import stripe
            stripe.api_key = STRIPE_SECRET_KEY
            payload = await request.body()
            sig = request.headers.get("stripe-signature", "")
            event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
        except Exception as e:
            raise HTTPException(400, str(e))

        event_id = event.get("id")
        if event_id and not await _claim_webhook_event_once(stripe_webhook_events, event_id, event.get("type")):
            return {"ok": True, "duplicate": True}

        if event["type"] == "checkout.session.completed":
            meta = event["data"]["object"].get("metadata", {})
            user_id = meta.get("user_id")
            plan = meta.get("plan", "base")
            sub_id = event["data"]["object"].get("subscription")
            if user_id:
                await self.repo.update_by_id(user_id, {
                    "plan": plan,
                    "subscription_status": "active",
                    "stripe_subscription_id": sub_id,
                })
        elif event["type"] in ("customer.subscription.deleted", "customer.subscription.paused"):
            # Con cancel_at_period_end=True (vedi cancel_subscription), questo
            # evento arriva solo alla vera data di fine periodo, non subito
            # alla richiesta di disdetta: è il momento corretto per tagliare
            # davvero l'accesso e ripulire cancel_at.
            sub = event["data"]["object"]
            await self.repo.update_by_stripe_subscription_id(
                sub["id"], {"subscription_status": "cancelled", "cancel_at": None}
            )
        elif event["type"] == "customer.subscription.updated":
            # Un rinnovo che fallisce (carta scaduta, fondi insufficienti) NON
            # genera checkout.session.completed né customer.subscription.deleted
            # (quest'ultimo arriva solo se/quando Stripe esaurisce i tentativi
            # di recupero automatici — anche settimane dopo): senza gestire
            # anche questo evento, un rinnovo fallito restava invisibile
            # all'app e l'utente manteneva l'accesso mentre l'incasso non
            # arrivava. Rispecchia direttamente lo status che Stripe riporta
            # (active/past_due/unpaid/...) invece di inventare una logica di
            # grace period nostra: i tentativi di recupero restano quelli
            # configurati su Stripe (Smart Retries), e quando un tentativo
            # successivo va a buon fine questo stesso evento torna a status
            # "active", riattivando l'accesso automaticamente.
            sub = event["data"]["object"]
            stripe_status = sub.get("status")
            if stripe_status:
                mapped = "cancelled" if stripe_status == "canceled" else stripe_status
                await self.repo.update_by_stripe_subscription_id(sub["id"], {"subscription_status": mapped})
        return {"ok": True}

    # ---- Helper PayPal ---------------------------------------------------
    # async + asyncio.to_thread attorno a `requests` (sincrona): senza,
    # ciascuna di queste chiamate bloccherebbe l'intero event loop del
    # worker per la durata della richiesta HTTP a PayPal (fino al timeout di
    # 10s) — non solo la richiesta che l'ha innescata, ma OGNI altra
    # richiesta in corso su quello stesso worker (login, dashboard, ecc.).
    # Stesso principio già applicato a Google Calendar in
    # services/google_calendar_service.py.

    async def _paypal_token(self) -> str:
        if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
            raise HTTPException(500, "PayPal non configurato")

        def _fetch():
            resp = requests.post(
                f"{PAYPAL_API_BASE}/v1/oauth2/token",
                auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
                data={"grant_type": "client_credentials"},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()["access_token"]

        return await asyncio.to_thread(_fetch)

    async def _paypal_get_subscription(self, subscription_id: str) -> dict:
        """Interroga direttamente PayPal per lo stato reale dell'abbonamento.
        Non ci si fida mai della sola conferma inviata dal frontend."""
        token = await self._paypal_token()

        def _fetch():
            return requests.get(
                f"{PAYPAL_API_BASE}/v1/billing/subscriptions/{subscription_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )

        resp = await asyncio.to_thread(_fetch)
        if resp.status_code != 200:
            raise HTTPException(400, "Abbonamento PayPal non trovato")
        return resp.json()

    async def _verify_paypal_webhook_signature(self, headers, raw_body: bytes, event: dict) -> bool:
        if not PAYPAL_WEBHOOK_ID:
            logger.error("PAYPAL_WEBHOOK_ID non configurato: rifiuto il webhook")
            return False
        token = await self._paypal_token()

        def _verify():
            return requests.post(
                f"{PAYPAL_API_BASE}/v1/notifications/verify-webhook-signature",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "transmission_id": headers.get("paypal-transmission-id"),
                    "transmission_time": headers.get("paypal-transmission-time"),
                    "cert_url": headers.get("paypal-cert-url"),
                    "auth_algo": headers.get("paypal-auth-algo"),
                    "transmission_sig": headers.get("paypal-transmission-sig"),
                    "webhook_id": PAYPAL_WEBHOOK_ID,
                    "webhook_event": event,
                },
                timeout=10,
            )

        resp = await asyncio.to_thread(_verify)
        if resp.status_code != 200:
            return False
        return resp.json().get("verification_status") == "SUCCESS"

    # ---- PayPal: capture lato frontend + conferma lato server -----------

    async def create_paypal_subscription(self, user: dict, payload: dict) -> dict:
        """Crea l'abbonamento lato PayPal con un return_url che punta davvero
        al nostro frontend, invece di affidarci a un link statico che non
        permette di controllare dove l'utente viene reindirizzato dopo il
        pagamento."""
        await self._forbid_if_demo(user["id"])
        plan_id = payload.get("plan", "base")
        plan = PLANS.get(plan_id)
        if not plan or not plan.get("paypal_plan_id"):
            raise HTTPException(400, "Piano PayPal non configurato")

        return_base = payload.get("return_url", FRONTEND_URL)
        token = await self._paypal_token()

        def _create():
            return requests.post(
                f"{PAYPAL_API_BASE}/v1/billing/subscriptions",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "plan_id": plan["paypal_plan_id"],
                    "application_context": {
                        "brand_name": "Salesfly",
                        "return_url": f"{return_base}/abbonamento?paypal_return=1",
                        "cancel_url": f"{return_base}/abbonamento?cancelled=1",
                    },
                },
                timeout=10,
            )

        resp = await asyncio.to_thread(_create)
        if resp.status_code not in (200, 201):
            logger.error(f"Errore creazione abbonamento PayPal: {resp.status_code} {resp.text[:300]}")
            raise HTTPException(500, "Errore avvio pagamento PayPal")

        data = resp.json()
        approve_url = next((l["href"] for l in data.get("links", []) if l.get("rel") == "approve"), None)
        if not approve_url:
            raise HTTPException(500, "PayPal non ha restituito un link di approvazione")

        # Registra QUALE subscription_id ci aspettiamo da questo utente prima
        # di reindirizzarlo a PayPal: paypal_capture() lo confermerà contro
        # questo valore invece di fidarsi ciecamente del subscription_id che
        # il frontend rimanda indietro — altrimenti chiunque conoscesse un
        # subscription_id reale e ACTIVE di un altro utente potrebbe legarlo
        # al proprio account (PayPal conferma solo che l'id è reale e attivo,
        # non a chi appartiene lato nostro).
        await self.repo.update_by_id(user["id"], {"pending_paypal_subscription_id": data["id"]})

        return {"approve_url": approve_url, "subscription_id": data["id"]}

    async def paypal_capture(self, user: dict, payload: dict) -> dict:
        """Conferma abbonamento PayPal dopo approvazione nel frontend.
        Il frontend segnala solo che l'utente ha approvato: il backend
        interroga sempre PayPal per lo stato reale prima di attivare
        qualunque funzionalità a pagamento."""
        u = await self._forbid_if_demo(user["id"])
        subscription_id = payload.get("subscription_id")
        if not subscription_id:
            raise HTTPException(400, "subscription_id mancante")

        # Il subscription_id deve essere quello che QUESTO account si
        # aspettava (impostato da create_paypal_subscription) o quello già
        # legato ad esso in precedenza (ricattura/retry sullo stesso
        # abbonamento) — mai un id arbitrario passato nel payload, che PayPal
        # confermerebbe comunque come reale/attivo indipendentemente da chi
        # lo sta presentando.
        expected_ids = {u.get("pending_paypal_subscription_id"), u.get("paypal_subscription_id")}
        expected_ids.discard(None)
        if subscription_id not in expected_ids:
            raise HTTPException(403, "Questo abbonamento PayPal non risulta creato per questo account")

        subscription = await self._paypal_get_subscription(subscription_id)

        # Non ci fidiamo del piano dichiarato dal frontend: lo deriviamo dal
        # plan_id che PayPal ci restituisce, altrimenti un client malevolo (o
        # bacato) potrebbe dichiarare "pro" avendo davvero pagato solo "base".
        real_paypal_plan_id = subscription.get("plan_id")
        plan_id = next(
            (k for k, v in PLANS.items() if v.get("paypal_plan_id") == real_paypal_plan_id),
            payload.get("plan", "base"),  # fallback solo se non riusciamo a mappare
        )

        status = subscription.get("status")
        if status not in PAYPAL_ACTIVE_STATUSES:
            # Non attiviamo nulla: l'abbonamento esiste ma non è (ancora) attivo
            # secondo PayPal. Il webhook lo attiverà quando/se arriverà ACTIVE.
            await self.repo.update_by_id(user["id"], {
                "plan": plan_id,
                "subscription_status": "pending",
                "paypal_subscription_id": subscription_id,
                "pending_paypal_subscription_id": None,
            })
            return {"ok": True, "status": "pending"}

        await self.repo.update_by_id(user["id"], {
            "plan": plan_id,
            "subscription_status": "active",
            "paypal_subscription_id": subscription_id,
            "pending_paypal_subscription_id": None,
        })
        return {"ok": True, "status": "active"}

    # ---- PayPal: webhook lato server (fonte di verità) -------------------

    async def handle_paypal_webhook(self, request: Request) -> dict:
        raw_body = await request.body()
        event = await request.json()

        if not await self._verify_paypal_webhook_signature(request.headers, raw_body, event):
            raise HTTPException(400, "Firma webhook PayPal non valida")

        event_id = event.get("id")
        # Idempotenza: PayPal può reinviare lo stesso evento più volte.
        if event_id and not await _claim_webhook_event_once(paypal_webhook_events, event_id, event.get("event_type")):
            return {"ok": True, "duplicate": True}

        event_type = event.get("event_type")
        resource = event.get("resource", {})
        subscription_id = resource.get("id") or resource.get("billing_agreement_id")

        if not subscription_id:
            return {"ok": True, "ignored": True}

        if event_type == "BILLING.SUBSCRIPTION.ACTIVATED":
            await self.repo.update_by_paypal_subscription_id(subscription_id, {"subscription_status": "active"})
        elif event_type == "BILLING.SUBSCRIPTION.CANCELLED":
            # PayPal non supporta una cancellazione differita a fine periodo:
            # quando cancel_subscription() cancella lato PayPal, questo evento
            # arriva quasi subito. Se cancel_at è già impostato (disdetta
            # avviata dalla nostra app, con la data di fine periodo già
            # pagato salvata), NON tagliamo subito l'accesso: ci pensa il
            # ciclo periodico di pulizia quando cancel_at sarà passato.
            # Solo se manca cancel_at (disdetta fatta direttamente su PayPal,
            # fuori dalla nostra app) tagliamo subito, perché in quel caso
            # nessuna promessa di accesso fino a fine periodo è stata fatta.
            existing_user = await self.repo.find_by_paypal_subscription_id(subscription_id)
            if not (existing_user and existing_user.get("cancel_at")):
                await self.repo.update_by_paypal_subscription_id(subscription_id, {"subscription_status": "cancelled"})
        elif event_type == "BILLING.SUBSCRIPTION.SUSPENDED":
            await self.repo.update_by_paypal_subscription_id(subscription_id, {"subscription_status": "suspended"})
        elif event_type == "BILLING.SUBSCRIPTION.EXPIRED":
            await self.repo.update_by_paypal_subscription_id(subscription_id, {"subscription_status": "expired"})
        elif event_type == "PAYMENT.SALE.DENIED":
            await self.repo.update_by_paypal_subscription_id(subscription_id, {"subscription_status": "payment_failed"})
        elif event_type == "PAYMENT.SALE.COMPLETED":
            # Un addebito riuscito dopo un tentativo precedente fallito
            # (PAYMENT.SALE.DENIED sopra) deve ripristinare l'accesso: senza
            # questo, un cliente che ha pagato regolarmente al secondo
            # tentativo restava bloccato con subscription_status ancora
            # "payment_failed", perché nessun altro evento lo riportava ad
            # "active". Tocca solo chi era davvero in payment_failed: un
            # abbonamento già attivo, sospeso o cancellato non va toccato da
            # un evento di pagamento riuscito che potrebbe riferirsi a un
            # rinnovo qualunque, non necessariamente un recupero.
            existing_user = await self.repo.find_by_paypal_subscription_id(subscription_id)
            if existing_user and existing_user.get("subscription_status") == "payment_failed":
                await self.repo.update_by_paypal_subscription_id(subscription_id, {"subscription_status": "active"})

        return {"ok": True}

    async def cancel_subscription(self, user: dict) -> dict:
        """Disdice l'abbonamento SENZA tagliare subito l'accesso: l'utente
        ha già pagato il periodo in corso, quindi deve poterlo usare fino
        alla fine (coerente col testo mostrato in Subscription.jsx). Invece
        di cancellare subito, calcoliamo la data di fine periodo già pagato
        e la salviamo in cancel_at: subscription_status resta 'active' fino
        a quella data (vedi is_subscription_active), poi passa a 'cancelled'
        tramite il webhook Stripe (alla vera scadenza) o il ciclo periodico
        di pulizia (per PayPal, che non ha un evento equivalente)."""
        u = await self._forbid_if_demo(user["id"])
        cancel_at = None

        # Traccia, per ciascun provider configurato, se l'azione di
        # cancellazione lato provider è DAVVERO andata a buon fine — non solo
        # se non ha sollevato un'eccezione: una risposta HTTP non-2xx da
        # PayPal, ad esempio, non fa sollevare requests.post da sola. Serve a
        # decidere sotto se è sicuro marcare l'abbonamento come cancellato
        # nel nostro DB: se un provider è configurato ma la sua chiamata non
        # è confermata riuscita, Stripe/PayPal continuerebbero comunque ad
        # addebitare il cliente anche se qui segniamo "cancellato" e gli
        # togliamo l'accesso — il peggio di entrambi i mondi.
        stripe_attempted = bool(u.get("stripe_subscription_id") and STRIPE_SECRET_KEY)
        stripe_succeeded = False
        paypal_attempted = bool(u.get("paypal_subscription_id") and PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET)
        paypal_succeeded = False

        # Stripe: cancel_at_period_end invece di cancellare subito — è Stripe
        # stesso a tenere traccia della data di fine periodo e a mandare il
        # webhook customer.subscription.deleted solo quando arriva, non ora.
        if stripe_attempted:
            try:
                import stripe
                stripe.api_key = STRIPE_SECRET_KEY
                sub = stripe.Subscription.modify(u["stripe_subscription_id"], cancel_at_period_end=True)
                period_end = sub.get("current_period_end")
                if period_end:
                    cancel_at = datetime.fromtimestamp(period_end, tz=timezone.utc).isoformat()
                stripe_succeeded = True
            except Exception as e:
                logger.warning(f"Stripe cancel error: {e}")

        # PayPal non offre una cancellazione differita: l'unica API disponibile
        # ferma subito i rinnovi futuri. Per onorare comunque "accesso fino a
        # fine periodo pagato", leggiamo prima la prossima data di rinnovo
        # (il periodo già pagato termina lì) come cancel_at, poi cancelliamo.
        if paypal_attempted:
            try:
                subscription = await self._paypal_get_subscription(u["paypal_subscription_id"])
                next_billing = subscription.get("billing_info", {}).get("next_billing_time")
                if next_billing and not cancel_at:
                    cancel_at = next_billing
            except Exception as e:
                logger.warning(f"PayPal get subscription error: {e}")
            try:
                token = await self._paypal_token()

                def _cancel():
                    return requests.post(
                        f"{PAYPAL_API_BASE}/v1/billing/subscriptions/{u['paypal_subscription_id']}/cancel",
                        headers={"Authorization": f"Bearer {token}"},
                        json={"reason": "Cancellato dall'utente"},
                        timeout=10,
                    )

                resp = await asyncio.to_thread(_cancel)
                # PayPal risponde 204 No Content quando la cancellazione va a
                # buon fine: requests non solleva un'eccezione da sola per
                # uno status non-2xx, va controllato esplicitamente.
                if resp.status_code in (200, 204):
                    paypal_succeeded = True
                else:
                    logger.warning(f"PayPal cancel error: status {resp.status_code} {resp.text[:200]}")
            except Exception as e:
                logger.warning(f"PayPal cancel error: {e}")

        if cancel_at:
            await self.repo.update_by_id(user["id"], {"cancel_at": cancel_at})
        elif not stripe_attempted and not paypal_attempted:
            # Nessun provider configurato per questo utente: non c'è nessun
            # addebito ricorrente reale da fermare, sicuro cancellare subito.
            await self.repo.update_by_id(user["id"], {"subscription_status": "cancelled"})
        elif (stripe_attempted and not stripe_succeeded) or (paypal_attempted and not paypal_succeeded):
            # Un provider è configurato ma non abbiamo la conferma che la
            # cancellazione sia davvero avvenuta lì: NON scriviamo
            # "cancelled" nel nostro DB, altrimenti l'utente perderebbe
            # l'accesso mentre il provider continua ad addebitarlo.
            raise HTTPException(502, "Non siamo riusciti a completare la disdetta con il fornitore di pagamento. Riprova tra poco o contattaci.")
        else:
            # Provider configurato e cancellazione confermata riuscita, ma
            # senza una data di fine periodo derivabile (raro, es. Stripe non
            # ha restituito current_period_end): cancellare subito è corretto
            # qui, la cancellazione lato provider è davvero avvenuta.
            await self.repo.update_by_id(user["id"], {"subscription_status": "cancelled"})
        return {"ok": True}


subscription_service = SubscriptionService()

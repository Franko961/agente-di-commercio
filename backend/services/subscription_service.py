import logging
import requests
from fastapi import HTTPException, Request

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

# Stati PayPal che consideriamo "abbonamento attivo": la sola creazione (APPROVAL_PENDING)
# non basta, va confermato ACTIVE prima di sbloccare qualunque funzionalità a pagamento.
PAYPAL_ACTIVE_STATUSES = {"ACTIVE"}

# Alias mantenuto per compatibilità: la logica vive ora in core/subscription_utils.py
# (core non può dipendere da services, quindi la fonte di verità è lì).
subscription_active = is_subscription_active


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
        try:
            import stripe
            stripe.api_key = STRIPE_SECRET_KEY
            payload = await request.body()
            sig = request.headers.get("stripe-signature", "")
            event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
        except Exception as e:
            raise HTTPException(400, str(e))

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
            sub = event["data"]["object"]
            await self.repo.update_by_stripe_subscription_id(sub["id"], {"subscription_status": "cancelled"})
        return {"ok": True}

    # ---- Helper PayPal ---------------------------------------------------

    def _paypal_token(self) -> str:
        if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
            raise HTTPException(500, "PayPal non configurato")
        resp = requests.post(
            f"{PAYPAL_API_BASE}/v1/oauth2/token",
            auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
            data={"grant_type": "client_credentials"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def _paypal_get_subscription(self, subscription_id: str) -> dict:
        """Interroga direttamente PayPal per lo stato reale dell'abbonamento.
        Non ci si fida mai della sola conferma inviata dal frontend."""
        token = self._paypal_token()
        resp = requests.get(
            f"{PAYPAL_API_BASE}/v1/billing/subscriptions/{subscription_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if resp.status_code != 200:
            raise HTTPException(400, "Abbonamento PayPal non trovato")
        return resp.json()

    def _verify_paypal_webhook_signature(self, headers, raw_body: bytes, event: dict) -> bool:
        if not PAYPAL_WEBHOOK_ID:
            logger.error("PAYPAL_WEBHOOK_ID non configurato: rifiuto il webhook")
            return False
        token = self._paypal_token()
        resp = requests.post(
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
        token = self._paypal_token()
        resp = requests.post(
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
        if resp.status_code not in (200, 201):
            logger.error(f"Errore creazione abbonamento PayPal: {resp.status_code} {resp.text[:300]}")
            raise HTTPException(500, "Errore avvio pagamento PayPal")

        data = resp.json()
        approve_url = next((l["href"] for l in data.get("links", []) if l.get("rel") == "approve"), None)
        if not approve_url:
            raise HTTPException(500, "PayPal non ha restituito un link di approvazione")

        return {"approve_url": approve_url, "subscription_id": data["id"]}

    async def paypal_capture(self, user: dict, payload: dict) -> dict:
        """Conferma abbonamento PayPal dopo approvazione nel frontend.
        Il frontend segnala solo che l'utente ha approvato: il backend
        interroga sempre PayPal per lo stato reale prima di attivare
        qualunque funzionalità a pagamento."""
        await self._forbid_if_demo(user["id"])
        subscription_id = payload.get("subscription_id")
        if not subscription_id:
            raise HTTPException(400, "subscription_id mancante")

        subscription = self._paypal_get_subscription(subscription_id)

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
            })
            return {"ok": True, "status": "pending"}

        await self.repo.update_by_id(user["id"], {
            "plan": plan_id,
            "subscription_status": "active",
            "paypal_subscription_id": subscription_id,
        })
        return {"ok": True, "status": "active"}

    # ---- PayPal: webhook lato server (fonte di verità) -------------------

    async def handle_paypal_webhook(self, request: Request) -> dict:
        raw_body = await request.body()
        event = await request.json()

        if not self._verify_paypal_webhook_signature(request.headers, raw_body, event):
            raise HTTPException(400, "Firma webhook PayPal non valida")

        event_id = event.get("id")
        if event_id:
            # Idempotenza: PayPal può reinviare lo stesso evento più volte.
            existing = await paypal_webhook_events.find_one({"event_id": event_id})
            if existing:
                return {"ok": True, "duplicate": True}
            await paypal_webhook_events.insert_one({"event_id": event_id, "event_type": event.get("event_type")})

        event_type = event.get("event_type")
        resource = event.get("resource", {})
        subscription_id = resource.get("id") or resource.get("billing_agreement_id")

        if not subscription_id:
            return {"ok": True, "ignored": True}

        if event_type == "BILLING.SUBSCRIPTION.ACTIVATED":
            await self.repo.update_by_paypal_subscription_id(subscription_id, {"subscription_status": "active"})
        elif event_type == "BILLING.SUBSCRIPTION.CANCELLED":
            await self.repo.update_by_paypal_subscription_id(subscription_id, {"subscription_status": "cancelled"})
        elif event_type == "BILLING.SUBSCRIPTION.SUSPENDED":
            await self.repo.update_by_paypal_subscription_id(subscription_id, {"subscription_status": "suspended"})
        elif event_type == "BILLING.SUBSCRIPTION.EXPIRED":
            await self.repo.update_by_paypal_subscription_id(subscription_id, {"subscription_status": "expired"})
        elif event_type == "PAYMENT.SALE.DENIED":
            await self.repo.update_by_paypal_subscription_id(subscription_id, {"subscription_status": "payment_failed"})
        # PAYMENT.SALE.COMPLETED: rinnovo riuscito, nessun cambio di stato necessario
        # oltre a restare "active"; loggato per audit tramite paypal_webhook_events.

        return {"ok": True}

    async def cancel_subscription(self, user: dict) -> dict:
        u = await self._forbid_if_demo(user["id"])
        # Cancella su Stripe se presente
        if u.get("stripe_subscription_id") and STRIPE_SECRET_KEY:
            try:
                import stripe
                stripe.api_key = STRIPE_SECRET_KEY
                stripe.Subscription.cancel(u["stripe_subscription_id"])
            except Exception as e:
                logger.warning(f"Stripe cancel error: {e}")
        # Cancella su PayPal se presente — prima d'ora questo ramo non
        # esisteva: la cancellazione lato PayPal avveniva solo se l'utente la
        # faceva direttamente sul proprio account PayPal (il nostro webhook
        # se ne accorgeva a cose fatte, ma non la richiedevamo mai noi).
        if u.get("paypal_subscription_id") and PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET:
            try:
                token = self._paypal_token()
                requests.post(
                    f"{PAYPAL_API_BASE}/v1/billing/subscriptions/{u['paypal_subscription_id']}/cancel",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"reason": "Cancellato dall'utente"},
                    timeout=10,
                )
            except Exception as e:
                logger.warning(f"PayPal cancel error: {e}")
        await self.repo.update_by_id(user["id"], {"subscription_status": "cancelled"})
        return {"ok": True}


subscription_service = SubscriptionService()

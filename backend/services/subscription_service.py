import logging
from datetime import datetime, timezone
from fastapi import HTTPException, Request

from core.config import PLANS, STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
from repositories.user_repository import user_repository

logger = logging.getLogger(__name__)


def subscription_active(user: dict) -> bool:
    status = user.get("subscription_status", "trial")
    if status == "active":
        return True
    if status == "trial":
        trial_end = user.get("trial_ends_at", "")
        try:
            end = datetime.fromisoformat(trial_end.replace("Z", "+00:00"))
            return datetime.now(timezone.utc) < end
        except Exception:
            return True
    return False


class SubscriptionService:
    def __init__(self, repo=user_repository):
        self.repo = repo

    async def get_plans(self) -> list:
        return [{"id": k, **v} for k, v in PLANS.items()]

    async def get_status(self, user: dict) -> dict:
        u = await self.repo.find_by_id(user["id"])
        return {
            "plan": u.get("plan", "base"),
            "status": u.get("subscription_status", "trial"),
            "trial_ends_at": u.get("trial_ends_at"),
            "active": subscription_active(u),
        }

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
            u = await self.repo.find_by_id(user["id"])
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
                success_url=f"{payload.get('return_url', 'https://salesfly.netlify.app')}/abbonamento?success=stripe",
                cancel_url=f"{payload.get('return_url', 'https://salesfly.netlify.app')}/abbonamento?cancelled=1",
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

    async def paypal_capture(self, user: dict, payload: dict) -> dict:
        """Conferma abbonamento PayPal dopo approvazione."""
        subscription_id = payload.get("subscription_id")
        plan_id = payload.get("plan", "base")
        if not subscription_id:
            raise HTTPException(400, "subscription_id mancante")
        await self.repo.update_by_id(user["id"], {
            "plan": plan_id,
            "subscription_status": "active",
            "paypal_subscription_id": subscription_id,
        })
        return {"ok": True}

    async def cancel_subscription(self, user: dict) -> dict:
        u = await self.repo.find_by_id(user["id"])
        # Cancella su Stripe se presente
        if u.get("stripe_subscription_id") and STRIPE_SECRET_KEY:
            try:
                import stripe
                stripe.api_key = STRIPE_SECRET_KEY
                stripe.Subscription.cancel(u["stripe_subscription_id"])
            except Exception as e:
                logger.warning(f"Stripe cancel error: {e}")
        await self.repo.update_by_id(user["id"], {"subscription_status": "cancelled"})
        return {"ok": True}


subscription_service = SubscriptionService()

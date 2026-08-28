import api from "../api";

// Astrazione per il dominio "abbonamento" — backend/routers/subscription.py.
// Non include /stripe-webhook e /paypal-webhook: sono chiamate
// server-to-server (Stripe/PayPal → backend), mai invocate dal frontend.

export function getPlans() {
  return api.get("/subscription/plans").then(({ data }) => data);
}

export function getSubscriptionStatus() {
  return api.get("/subscription/status").then(({ data }) => data);
}

export function getPaymentHistory() {
  return api.get("/subscription/payment-history").then(({ data }) => data);
}

export function createStripeSession(payload) {
  return api.post("/subscription/create-stripe-session", payload).then(({ data }) => data);
}

export function checkoutExpired(payload) {
  return api.post("/subscription/checkout-expired", payload).then(({ data }) => data);
}

export function createPaypalOrder(payload) {
  return api.post("/subscription/paypal-create", payload).then(({ data }) => data);
}

export function capturePaypalOrder(payload) {
  return api.post("/subscription/paypal-capture", payload).then(({ data }) => data);
}

export function cancelSubscription() {
  return api.post("/subscription/cancel").then(({ data }) => data);
}

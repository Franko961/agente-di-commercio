import api from "../api";

// Astrazione per il dominio "autenticazione" — backend/routers/auth.py.
// Non compreso nell'elenco iniziale di domini, aggiunto per coerenza. Non
// include POST /auth/make-admin: endpoint di bootstrap non chiamato da
// nessuna pagina (stessa esclusione già fatta in api/admin.js).

export function getMe() {
  return api.get("/auth/me").then(({ data }) => data);
}

export function login(email, password) {
  return api.post("/auth/login", { email, password }).then(({ data }) => data);
}

export function register(name, email, password, plan = "base") {
  return api.post("/auth/register", { name, email, password, plan }).then(({ data }) => data);
}

export function logout() {
  return api.post("/auth/logout").then(({ data }) => data);
}

export function exitImpersonation() {
  return api.post("/auth/exit-impersonation").then(({ data }) => data);
}

export function markOnboardingSeen() {
  return api.post("/auth/onboarding-seen").then(({ data }) => data);
}

export function markCapterraReviewDismissed() {
  return api.post("/auth/capterra-review-dismissed").then(({ data }) => data);
}

export function forgotPassword(email) {
  return api.post("/auth/forgot-password", { email }).then(({ data }) => data);
}

export function resetPassword(token, newPassword) {
  return api.post("/auth/reset-password", { token, new_password: newPassword }).then(({ data }) => data);
}

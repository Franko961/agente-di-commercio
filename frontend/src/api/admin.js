import api from "../api";

// Astrazione per il dominio "amministrazione" — backend/routers/admin.py.
// Non compreso nell'elenco iniziale di domini, aggiunto per coerenza. Non
// include POST /auth/make-admin: endpoint di bootstrap non chiamato da
// nessuna pagina (promozione ad admin fatta manualmente, non da UI).

export function getAdminStats() {
  return api.get("/admin/stats").then(({ data }) => data);
}

export function listAdminUsers(page = 1, limit = 50) {
  return api.get(`/admin/users?page=${page}&limit=${limit}`).then(({ data }) => data);
}

export function updateAdminUser(id, payload) {
  return api.patch(`/admin/users/${id}`, payload).then(({ data }) => data);
}

export function deleteAdminUser(id) {
  return api.delete(`/admin/users/${id}`).then(({ data }) => data);
}

export function impersonateUser(id, payload) {
  return api.post(`/admin/users/${id}/impersonate`, payload).then(({ data }) => data);
}

export function getAdminHealth(hours) {
  return api.get("/admin/health", { params: { hours } }).then(({ data }) => data);
}

export function getAuditLog(page = 1, limit = 50) {
  return api.get("/admin/audit-log", { params: { page, limit } }).then(({ data }) => data);
}

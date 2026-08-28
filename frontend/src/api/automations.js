import api from "../api";

// Astrazione per il dominio "automazioni" — backend/routers/automations.py.
// Non compreso nell'elenco iniziale di domini, aggiunto per coerenza: usato
// da pages/Automations.jsx, pages/Flotta.jsx (promemoria scadenze mezzi) e
// components/NotificationBell.jsx (notifiche in-app).

export function listAutomations() {
  return api.get("/automations").then(({ data }) => data);
}

export function createAutomation(payload) {
  return api.post("/automations", payload).then(({ data }) => data);
}

export function updateAutomation(id, payload) {
  return api.put(`/automations/${id}`, payload).then(({ data }) => data);
}

export function deleteAutomation(id) {
  return api.delete(`/automations/${id}`).then(({ data }) => data);
}

export function getAutomationRuns(id) {
  return api.get(`/automations/${id}/runs`).then(({ data }) => data);
}

// --- Notifiche in-app (NotificationBell.jsx) ---

export function listNotifications() {
  return api.get("/automations/notifications").then(({ data }) => data);
}

export function markNotificationRead(id) {
  return api.put(`/automations/notifications/${id}/read`).then(({ data }) => data);
}

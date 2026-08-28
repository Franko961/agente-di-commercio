import api from "../api";

// Astrazione per il dominio "integrazioni" — backend/routers/integrations.py
// (solo Google Calendar oggi). Non compreso nell'elenco iniziale di domini,
// aggiunto per coerenza. Non include /callback: è il redirect OAuth che
// Google chiama direttamente sul backend, mai invocato dal frontend.

export function getGoogleCalendarStatus() {
  return api.get("/integrations/google/status").then(({ data }) => data);
}

export function connectGoogleCalendar() {
  return api.get("/integrations/google/connect").then(({ data }) => data);
}

export function disconnectGoogleCalendar() {
  return api.post("/integrations/google/disconnect").then(({ data }) => data);
}

export function syncGoogleCalendar() {
  return api.post("/integrations/google/sync").then(({ data }) => data);
}

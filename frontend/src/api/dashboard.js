import api from "../api";

// Astrazione per il dominio "dashboard" — backend/routers/dashboard.py.
// Non compreso nell'elenco iniziale di domini, aggiunto per coerenza.

export function getDashboardStats(mandanteId) {
  return api.get("/dashboard/stats", { params: { mandante_id: mandanteId } }).then(({ data }) => data);
}

export function getDashboardToday(mandanteId) {
  return api.get("/dashboard/today", { params: { mandante_id: mandanteId } }).then(({ data }) => data);
}

import api from "../api";

// Astrazione per il dominio "provvigioni" — backend/routers/commissions.py.
// Non compreso nell'elenco iniziale di domini, aggiunto per coerenza.

export function listCommissions(params = {}) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") qs.append(k, v);
  }
  const query = qs.toString();
  return api.get(`/commissions${query ? `?${query}` : ""}`).then(({ data }) => data);
}

export function getBonusSummary() {
  return api.get("/commissions/bonus-summary").then(({ data }) => data);
}

export function updateCommissionStatus(id, status) {
  return api.patch(`/commissions/${id}/status`, { status }).then(({ data }) => data);
}

export function deleteCommission(id) {
  return api.delete(`/commissions/${id}`).then(({ data }) => data);
}

// --- Provvigioni inserite manualmente (fuori dal flusso ordini) ---

export function listManualCommissions() {
  return api.get("/commissions/manual").then(({ data }) => data);
}

export function createManualCommission(payload) {
  return api.post("/commissions/manual", payload).then(({ data }) => data);
}

export function updateManualCommission(id, payload) {
  return api.put(`/commissions/manual/${id}`, payload).then(({ data }) => data);
}

export function deleteManualCommission(id) {
  return api.delete(`/commissions/manual/${id}`).then(({ data }) => data);
}

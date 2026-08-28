import api from "../api";

// Astrazione per il dominio "mandanti" — backend/routers/mandanti.py.
// Non compreso nell'elenco iniziale di domini (clients/leads/orders/offers/
// employees/attendance/vehicles/documents/ai/subscription) ma aggiunto per
// coerenza: usato da più pagine (Offers.jsx, Ordini.jsx, Flotta.jsx,
// contexts/MandanteContext.jsx — quest'ultimo non ancora migrato).

export function listMandanti() {
  return api.get("/mandanti").then(({ data }) => data);
}

export function createMandante(payload) {
  return api.post("/mandanti", payload).then(({ data }) => data);
}

export function updateMandante(id, payload) {
  return api.put(`/mandanti/${id}`, payload).then(({ data }) => data);
}

export function deleteMandante(id) {
  return api.delete(`/mandanti/${id}`).then(({ data }) => data);
}

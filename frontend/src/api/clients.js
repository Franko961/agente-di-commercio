import api from "../api";

// Astrazione per il dominio "clienti" — centralizza gli endpoint di
// backend/routers/clients.py invece di lasciare `api.get/post/...` sparsi
// nelle pagine. Ogni funzione ritorna direttamente `data` (non l'intera
// risposta axios): le pagine chiamanti non devono destrutturare `{ data }`.

export function listClients(params = {}) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") qs.append(k, v);
  }
  const query = qs.toString();
  return api.get(`/clients${query ? `?${query}` : ""}`).then(({ data }) => data);
}

export function getClient(id) {
  return api.get(`/clients/${id}`).then(({ data }) => data);
}

export function createClient(payload) {
  return api.post("/clients", payload).then(({ data }) => data);
}

export function updateClient(id, payload) {
  return api.put(`/clients/${id}`, payload).then(({ data }) => data);
}

export function deleteClient(id) {
  return api.delete(`/clients/${id}`).then(({ data }) => data);
}

// Vedi frontend/src/pages/ImportClienti.jsx: righe già mappate/validate
// lato client prima di questa chiamata (vedi MAX_ROWS/MAX_FILE_SIZE_BYTES lì).
export function bulkImportClients(payload) {
  return api.post("/clients/bulk", payload).then(({ data }) => data);
}

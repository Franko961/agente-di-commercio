import api from "../api";

// Astrazione per il dominio "offerte" — backend/routers/offers.py.

export function listOffers(params = {}) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") qs.append(k, v);
  }
  const query = qs.toString();
  return api.get(`/offers${query ? `?${query}` : ""}`).then(({ data }) => data);
}

export function createOffer(payload) {
  return api.post("/offers", payload).then(({ data }) => data);
}

export function updateOffer(id, payload) {
  return api.put(`/offers/${id}`, payload).then(({ data }) => data);
}

export function updateOfferStatus(id, status) {
  return api.patch(`/offers/${id}/status`, { status }).then(({ data }) => data);
}

// Firma dell'offerta da parte del cliente (SignaturePad.jsx, PDF con prezzi
// — vedi caci_srl_extra_modules per il perché NON è riusato per altre firme).
export function signOffer(id, payload) {
  return api.post(`/offers/${id}/sign`, payload).then(({ data }) => data);
}

export function deleteOffer(id) {
  return api.delete(`/offers/${id}`).then(({ data }) => data);
}

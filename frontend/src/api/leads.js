import api from "../api";

// Astrazione per il dominio "lead" — backend/routers/leads.py.

export function listLeads(params = {}) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") qs.append(k, v);
  }
  const query = qs.toString();
  return api.get(`/leads${query ? `?${query}` : ""}`).then(({ data }) => data);
}

export function createLead(payload) {
  return api.post("/leads", payload).then(({ data }) => data);
}

export function updateLead(id, payload) {
  return api.put(`/leads/${id}`, payload).then(({ data }) => data);
}

export function updateLeadStatus(id, status) {
  return api.patch(`/leads/${id}/status`, { status }).then(({ data }) => data);
}

export function logLeadContact(id, payload) {
  return api.post(`/leads/${id}/log-contact`, payload).then(({ data }) => data);
}

export function deleteLead(id) {
  return api.delete(`/leads/${id}`).then(({ data }) => data);
}

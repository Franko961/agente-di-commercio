import api from "../api";

// Astrazione per il dominio "feedback" — backend/routers/feedback.py.
// Non compreso nell'elenco iniziale di domini, aggiunto per coerenza: usato
// da Settings.jsx (invio), Landing.jsx (testimonianze pubbliche, non ancora
// migrata) e Admin.jsx (moderazione, non ancora migrata).

export function submitFeedback(payload) {
  return api.post("/feedback", payload).then(({ data }) => data);
}

export function getPublicFeedback() {
  return api.get("/feedback/public").then(({ data }) => data);
}

// --- Moderazione (Admin.jsx) ---

export function listFeedbackAdmin() {
  return api.get("/admin/feedback").then(({ data }) => data);
}

export function setFeedbackApproved(id, approved) {
  return api.patch(`/admin/feedback/${id}`, { approved }).then(({ data }) => data);
}

export function deleteFeedback(id) {
  return api.delete(`/admin/feedback/${id}`).then(({ data }) => data);
}

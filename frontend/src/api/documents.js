import api from "../api";

// Astrazione per il dominio "documenti" (archivio collegato ai clienti) —
// backend/routers/documents.py. Dominio distinto dai documenti del
// dipendente (vedi api/employees.js: listEmployeeDocuments e affini).

export function listDocuments(params = {}) {
  const qs = new URLSearchParams(params).toString();
  return api.get(`/documents${qs ? `?${qs}` : ""}`).then(({ data }) => data);
}

// `config` opzionale (es. { onUploadProgress }) passato ad axios cosi'
// com'e' — usato da pages/Documents.jsx per la barra di avanzamento upload.
export function uploadDocument(formData, config = {}) {
  return api.post("/documents/upload", formData, config).then(({ data }) => data);
}

export function updateDocument(id, payload) {
  return api.patch(`/documents/${id}`, payload).then(({ data }) => data);
}

export function getDocumentSignedUrl(id) {
  return api.get(`/documents/${id}/signed-url`).then(({ data }) => data);
}

export function deleteDocument(id) {
  return api.delete(`/documents/${id}`).then(({ data }) => data);
}

import api from "../api";

// Astrazione per il dominio "privacy/GDPR" — backend/routers/gdpr.py
// (prefix /api/privacy). Non compreso nell'elenco iniziale di domini,
// aggiunto per coerenza.

// Ritorna la response axios completa (non solo `data`): il chiamante deve
// leggere `response.data` come Blob per costruire il download del .zip.
export function exportMyData() {
  return api.get("/privacy/export", { responseType: "blob" });
}

export function deleteMyAccount(password) {
  return api.post("/privacy/delete-account", { password }).then(({ data }) => data);
}

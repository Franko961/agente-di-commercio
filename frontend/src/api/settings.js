import api from "../api";

// Astrazione per il dominio "impostazioni account" — backend/routers/settings.py.
// Non compreso nell'elenco iniziale di domini, aggiunto per coerenza.

export function getGoals() {
  return api.get("/settings/goals").then(({ data }) => data);
}
export function updateGoals(payload) {
  return api.put("/settings/goals", payload).then(({ data }) => data);
}

export function getAddresses() {
  return api.get("/settings/addresses").then(({ data }) => data);
}
export function updateAddresses(payload) {
  return api.put("/settings/addresses", payload).then(({ data }) => data);
}

export function getLeaveSettings() {
  return api.get("/settings/leave").then(({ data }) => data);
}
export function updateLeaveSettings(payload) {
  return api.put("/settings/leave", payload).then(({ data }) => data);
}

export function getCompanySettings() {
  return api.get("/settings/company").then(({ data }) => data);
}
export function updateCompanySettings(payload) {
  return api.put("/settings/company", payload).then(({ data }) => data);
}

// --- Chiosco QR di timbratura: token e rigenerazione (non il chiosco
// pubblico in sé, vedi api/attendance.js per quello) ---
export function getAttendanceKiosk() {
  return api.get("/settings/attendance-kiosk").then(({ data }) => data);
}
export function regenerateAttendanceKiosk() {
  return api.post("/settings/attendance-kiosk/regenerate").then(({ data }) => data);
}

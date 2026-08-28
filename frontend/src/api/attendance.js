import api from "../api";

// Astrazione per il dominio "presenze" — backend/routers/attendance.py, che
// espone tre router distinti sotto lo stesso file backend:
//   - per dipendente: /api/employees/{eid}/attendance
//   - a livello account: /api/attendance/{calendar,expected,today-summary,export.xlsx}
//   - chiosco pubblico (senza login): /api/attendance/kiosk/{token}/...
// Vedi anche api/employees.js per il PIN del chiosco (regenerateEmployeePin).

// --- Sessioni per dipendente (usato da employee-detail/tabs/PresenzeTab.jsx) ---

export function listEmployeeAttendance(employeeId) {
  return api.get(`/employees/${employeeId}/attendance`).then(({ data }) => data);
}
export function createAttendance(employeeId, payload) {
  return api.post(`/employees/${employeeId}/attendance`, payload).then(({ data }) => data);
}
export function updateAttendance(employeeId, id, payload) {
  return api.patch(`/employees/${employeeId}/attendance/${id}`, payload).then(({ data }) => data);
}
export function deleteAttendance(employeeId, id) {
  return api.delete(`/employees/${employeeId}/attendance/${id}`).then(({ data }) => data);
}

// --- Vista account-wide (usato da pages/Presenze.jsx) ---

export function getAttendanceCalendar(params = {}) {
  const qs = new URLSearchParams(params).toString();
  return api.get(`/attendance/calendar${qs ? `?${qs}` : ""}`).then(({ data }) => data);
}
export function getAttendanceExpected(params = {}) {
  const qs = new URLSearchParams(params).toString();
  return api.get(`/attendance/expected${qs ? `?${qs}` : ""}`).then(({ data }) => data);
}
export function getAttendanceTodaySummary() {
  return api.get("/attendance/today-summary").then(({ data }) => data);
}

// --- Chiosco QR di timbratura (pages/Timbra.jsx, senza login: usa il token
// nel percorso, non un cookie di sessione) ---

export function getKioskEmployees(token) {
  return api.get(`/attendance/kiosk/${token}/employees`).then(({ data }) => data);
}
export function kioskClockIn(token, payload) {
  return api.post(`/attendance/kiosk/${token}/clock-in`, payload).then(({ data }) => data);
}
export function kioskClockOut(token, payload) {
  return api.post(`/attendance/kiosk/${token}/clock-out`, payload).then(({ data }) => data);
}

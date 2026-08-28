import api from "../api";

// Astrazione per il dominio "personale" — backend/routers/employees.py e i
// router dei sotto-domini per-dipendente (equipment, compensation,
// disciplinary-actions, documents, leave-requests). Modulo extra opt-in
// (vedi core.security.EXTRA_MODULE_KEYS e caci_srl_extra_modules).

// --- Dipendenti ---

export function listEmployees(params = {}) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") qs.append(k, v);
  }
  const query = qs.toString();
  return api.get(`/employees${query ? `?${query}` : ""}`).then(({ data }) => data);
}

export function getEmployeeDetail(id) {
  return api.get(`/employees/${id}/detail`).then(({ data }) => data);
}

export function getEmployeeActivity(id) {
  return api.get(`/employees/${id}/activity`).then(({ data }) => data);
}

export function getEmployeeAiSummary(id) {
  return api.get(`/employees/${id}/ai-summary`).then(({ data }) => data);
}

export function createEmployee(payload) {
  return api.post("/employees", payload).then(({ data }) => data);
}

export function updateEmployee(id, payload) {
  return api.put(`/employees/${id}`, payload).then(({ data }) => data);
}

export function setEmployeeActive(id, active) {
  return api.patch(`/employees/${id}/active`, { active }).then(({ data }) => data);
}

export function regenerateEmployeeToken(id) {
  return api.post(`/employees/${id}/regenerate-token`).then(({ data }) => data);
}

export function deleteEmployee(id) {
  return api.delete(`/employees/${id}`).then(({ data }) => data);
}

// --- PIN chiosco presenze (vedi anche api/attendance.js per il chiosco stesso) ---

export function regenerateEmployeePin(id) {
  return api.post(`/employees/${id}/attendance/pin`).then(({ data }) => data);
}

// --- Richieste di assenza (ferie/permessi/malattia) ---

export function listLeaveRequests(params = {}) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") qs.append(k, v);
  }
  const query = qs.toString();
  return api.get(`/leave-requests${query ? `?${query}` : ""}`).then(({ data }) => data);
}

export function getLeaveRequestsCalendar(params = {}) {
  const qs = new URLSearchParams(params).toString();
  return api.get(`/leave-requests/calendar${qs ? `?${qs}` : ""}`).then(({ data }) => data);
}

export function decideLeaveRequest(id, payload) {
  return api.patch(`/leave-requests/${id}/decision`, payload).then(({ data }) => data);
}

export function setLeaveRequestCertificate(id, certificateReceived) {
  return api.patch(`/leave-requests/${id}/certificate`, { certificate_received: certificateReceived }).then(({ data }) => data);
}

export function deleteLeaveRequest(id) {
  return api.delete(`/leave-requests/${id}`).then(({ data }) => data);
}

// Creazione da parte dell'admin per conto di un dipendente specifico
// (diversa dal link pubblico self-service /richiedi-assenza/{token}).
export function createLeaveRequestForEmployee(employeeId, payload) {
  return api.post(`/employees/${employeeId}/leave-requests`, payload).then(({ data }) => data);
}

// --- Pagine pubbliche self-service (nessuna autenticazione, link personale
// via token) — RichiediAssenza.jsx ---

export function getEmployeeByToken(token) {
  return api.get(`/employees/by-token/${token}`).then(({ data }) => data);
}

export function submitLeaveRequest(payload) {
  return api.post("/leave-requests", payload).then(({ data }) => data);
}

// --- Dotazione (equipment) ---

export function listEquipment(employeeId) {
  return api.get(`/employees/${employeeId}/equipment`).then(({ data }) => data);
}
export function createEquipment(employeeId, payload) {
  return api.post(`/employees/${employeeId}/equipment`, payload).then(({ data }) => data);
}
export function updateEquipment(employeeId, id, payload) {
  return api.put(`/employees/${employeeId}/equipment/${id}`, payload).then(({ data }) => data);
}
export function deleteEquipment(employeeId, id) {
  return api.delete(`/employees/${employeeId}/equipment/${id}`).then(({ data }) => data);
}

// --- Compensi ---

export function listCompensation(employeeId) {
  return api.get(`/employees/${employeeId}/compensation`).then(({ data }) => data);
}
export function createCompensation(employeeId, payload) {
  return api.post(`/employees/${employeeId}/compensation`, payload).then(({ data }) => data);
}
export function updateCompensation(employeeId, id, payload) {
  return api.put(`/employees/${employeeId}/compensation/${id}`, payload).then(({ data }) => data);
}
export function deleteCompensation(employeeId, id) {
  return api.delete(`/employees/${employeeId}/compensation/${id}`).then(({ data }) => data);
}

// --- Contestazioni disciplinari ---

export function listDisciplinaryActions(employeeId) {
  return api.get(`/employees/${employeeId}/disciplinary-actions`).then(({ data }) => data);
}
export function createDisciplinaryAction(employeeId, payload) {
  return api.post(`/employees/${employeeId}/disciplinary-actions`, payload).then(({ data }) => data);
}
export function updateDisciplinaryAction(employeeId, id, payload) {
  return api.put(`/employees/${employeeId}/disciplinary-actions/${id}`, payload).then(({ data }) => data);
}
export function deleteDisciplinaryAction(employeeId, id) {
  return api.delete(`/employees/${employeeId}/disciplinary-actions/${id}`).then(({ data }) => data);
}

// --- Documenti del dipendente (dominio distinto da api/documents.js, che
// copre invece i documenti collegati ai CLIENTI) ---

export function listEmployeeDocuments(employeeId) {
  return api.get(`/employees/${employeeId}/documents`).then(({ data }) => data);
}
export function uploadEmployeeDocument(employeeId, formData) {
  return api.post(`/employees/${employeeId}/documents/upload`, formData).then(({ data }) => data);
}
export function deleteEmployeeDocument(employeeId, id) {
  return api.delete(`/employees/${employeeId}/documents/${id}`).then(({ data }) => data);
}

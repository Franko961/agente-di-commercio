import api from "../api";

// Astrazione per il dominio "appuntamenti" — backend/routers/appointments.py.
// Non compreso nell'elenco iniziale di domini, aggiunto per coerenza: usato
// da Agenda.jsx e, per createAppointmentsBulk, anche da MapView.jsx (giro
// visite ottimizzato che genera più appuntamenti in un colpo solo).

export function listAppointments() {
  return api.get("/appointments").then(({ data }) => data);
}

export function createAppointment(payload) {
  return api.post("/appointments", payload).then(({ data }) => data);
}

export function createAppointmentsBulk(appointments) {
  return api.post("/appointments/bulk", { appointments }).then(({ data }) => data);
}

export function updateAppointment(id, payload) {
  return api.put(`/appointments/${id}`, payload).then(({ data }) => data);
}

export function deleteAppointment(id) {
  return api.delete(`/appointments/${id}`).then(({ data }) => data);
}

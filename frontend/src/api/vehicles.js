import api from "../api";

// Astrazione per il dominio "flotta" — backend/routers/vehicles.py,
// vehicle_deadlines.py, vehicle_costs.py, cargo_loads.py. Modulo extra
// opt-in (vedi core.security.EXTRA_MODULE_KEYS e caci_srl_extra_modules).

// --- Mezzi ---

export function listVehicles(params = {}) {
  const qs = new URLSearchParams(params).toString();
  return api.get(`/vehicles${qs ? `?${qs}` : ""}`).then(({ data }) => data);
}
export function createVehicle(payload) {
  return api.post("/vehicles", payload).then(({ data }) => data);
}
export function updateVehicle(id, payload) {
  return api.put(`/vehicles/${id}`, payload).then(({ data }) => data);
}
export function setVehicleActive(id, active) {
  return api.patch(`/vehicles/${id}/active`, { active }).then(({ data }) => data);
}
export function deleteVehicle(id) {
  return api.delete(`/vehicles/${id}`).then(({ data }) => data);
}

// --- Scadenze documentali ---

export function listVehicleDeadlines(params = {}) {
  const qs = new URLSearchParams(params).toString();
  return api.get(`/vehicle-deadlines${qs ? `?${qs}` : ""}`).then(({ data }) => data);
}
export function createVehicleDeadline(payload) {
  return api.post("/vehicle-deadlines", payload).then(({ data }) => data);
}
export function updateVehicleDeadline(id, payload) {
  return api.put(`/vehicle-deadlines/${id}`, payload).then(({ data }) => data);
}
export function deleteVehicleDeadline(id) {
  return api.delete(`/vehicle-deadlines/${id}`).then(({ data }) => data);
}

// --- Costi (genera automaticamente una Spesa collegata, vedi
// caci_srl_extra_modules — non duplicare qui, resta lato backend) ---

export function listVehicleCosts(params = {}) {
  const qs = new URLSearchParams(params).toString();
  return api.get(`/vehicle-costs${qs ? `?${qs}` : ""}`).then(({ data }) => data);
}
export function createVehicleCost(payload) {
  return api.post("/vehicle-costs", payload).then(({ data }) => data);
}
export function updateVehicleCost(id, payload) {
  return api.put(`/vehicle-costs/${id}`, payload).then(({ data }) => data);
}
export function deleteVehicleCost(id) {
  return api.delete(`/vehicle-costs/${id}`).then(({ data }) => data);
}

// --- Carichi trasportati ---

export function listCargoLoads(params = {}) {
  const qs = new URLSearchParams(params).toString();
  return api.get(`/cargo-loads${qs ? `?${qs}` : ""}`).then(({ data }) => data);
}
export function createCargoLoad(payload) {
  return api.post("/cargo-loads", payload).then(({ data }) => data);
}
export function updateCargoLoad(id, payload) {
  return api.put(`/cargo-loads/${id}`, payload).then(({ data }) => data);
}
export function signCargoLoad(id, payload) {
  return api.post(`/cargo-loads/${id}/sign`, payload).then(({ data }) => data);
}
export function deleteCargoLoad(id) {
  return api.delete(`/cargo-loads/${id}`).then(({ data }) => data);
}

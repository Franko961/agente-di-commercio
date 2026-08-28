import api from "../api";

// Astrazione per il dominio "pianificazione giro visite" —
// backend/routers/route_planning.py. Non compreso nell'elenco iniziale di
// domini, aggiunto per coerenza: usato solo da MapView.jsx.

export function optimizeRoute(payload) {
  return api.post("/route-planning/optimize", payload).then(({ data }) => data);
}

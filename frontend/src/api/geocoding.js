import api from "../api";

// Astrazione per il dominio "geocodifica" — backend/routers/geocoding.py.
// Non compreso nell'elenco iniziale di domini, aggiunto per coerenza: usato
// solo da MapView.jsx (ricerca indirizzo libero sulla mappa).

export function geocodeAddress(query) {
  return api.get("/geocode", { params: { q: query } }).then(({ data }) => data);
}

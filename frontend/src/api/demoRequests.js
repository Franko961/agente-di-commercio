import api from "../api";

// Astrazione per il dominio "richieste demo" — backend/routers/demo_requests.py.
// Non compreso nell'elenco iniziale di domini, aggiunto per coerenza. Usato
// da RichiediDemo.jsx (form pubblico sul sito).

export function createDemoRequest(payload) {
  return api.post("/demo-requests", payload).then(({ data }) => data);
}

// Non ancora usata da nessuna pagina (nessun elenco richieste demo in
// Admin.jsx oggi) — esposta qui solo perché il router backend la offre.
export function listDemoRequests() {
  return api.get("/demo-requests").then(({ data }) => data);
}

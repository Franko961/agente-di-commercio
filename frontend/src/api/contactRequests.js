import api from "../api";

// Astrazione per il dominio "richieste di contatto" —
// backend/routers/contact.py. Non compreso nell'elenco iniziale di domini,
// aggiunto per coerenza. Usato da Contatti.jsx (form pubblico sul sito).

export function createContactRequest(payload) {
  return api.post("/contact-requests", payload).then(({ data }) => data);
}

// Non ancora usata da nessuna pagina (nessun elenco richieste contatto in
// Admin.jsx oggi) — esposta qui solo perché il router backend la offre.
export function listContactRequests() {
  return api.get("/contact-requests").then(({ data }) => data);
}

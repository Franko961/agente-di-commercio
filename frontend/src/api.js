import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API_BASE = `${BACKEND_URL}/api`;

const api = axios.create({ baseURL: API_BASE, withCredentials: true });

// Se una richiesta autenticata torna 402, il trial dell'utente è scaduto a metà
// sessione (era già loggato quando sono passati i 14 giorni). Lo rimandiamo al
// login, che riconosce questo stato e mostra la schermata di pagamento al posto
// del form — invece di lasciarlo bloccato su una pagina che non funziona più.
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err?.response?.status === 402 && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login?scaduto=1";
    }
    return Promise.reject(err);
  }
);

export default api;

import { createContext, useContext, useEffect, useState } from "react";
import {
  getMe, login as loginApi, register as registerApi, logout as logoutApi,
  exitImpersonation as exitImpersonationApi, markOnboardingSeen as markOnboardingSeenApi,
  markCapterraReviewDismissed as markCapterraReviewDismissedApi,
} from "../api/auth";

const AuthContext = createContext(null);

// access_token è httpOnly apposta (vedi set_auth_cookie in core/security.py):
// il JS non può leggerlo per sapere in anticipo se una sessione esiste già.
// Questo flag NON è un dato di sicurezza (la sessione vera è sempre e solo
// il cookie httpOnly, verificato lato server) — è solo un suggerimento
// locale per evitare la chiamata a /auth/me quando sappiamo già con
// certezza che non c'è nessuna sessione da controllare (es. un visitatore
// anonimo sulla homepage pubblica): senza, ogni caricamento di OGNI pagina
// pubblica generava un 401 in console (segnalato da PageSpeed Insights) e
// una richiesta di rete sprecata, anche per chi non si è mai loggato.
const HAS_SESSION_HINT_KEY = "sf_has_session";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (localStorage.getItem(HAS_SESSION_HINT_KEY) !== "1") {
      setLoading(false);
      return;
    }
    getMe()
      .then((data) => setUser(data))
      .catch(() => {
        // Suggerimento non più valido (es. cookie di sessione scaduto dopo
        // 7 giorni): lo rimuoviamo per non ripetere la chiamata a vuoto a
        // ogni pagina finché l'utente non rifà login esplicitamente.
        localStorage.removeItem(HAS_SESSION_HINT_KEY);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    const data = await loginApi(email, password);
    localStorage.setItem(HAS_SESSION_HINT_KEY, "1");
    setUser(data);
    return data;
  };

  const register = async (name, email, password, plan="base") => {
    const data = await registerApi(name, email, password, plan);
    localStorage.setItem(HAS_SESSION_HINT_KEY, "1");
    setUser(data);
    return data;
  };

  const logout = async () => {
    try { await logoutApi(); } catch (e) {}
    localStorage.removeItem(HAS_SESSION_HINT_KEY);
    setUser(null);
  };

  // Ricarica l'intera pagina (invece di limitarsi a un setUser locale):
  // il cookie di sessione è già stato sostituito lato server prima di
  // chiamare questa funzione (vedi Admin.jsx e ImpersonationBanner in
  // Layout.jsx), e con lui va ricaricato anche tutto lo stato dipendente
  // dall'utente sparso nell'app (mandanti, notifiche, ecc.), non solo
  // "user" in questo context.
  const exitImpersonation = async () => {
    try { await exitImpersonationApi(); } catch (e) {}
    window.location.href = "/app/admin";
  };

  const markOnboardingSeen = async () => {
    // Ottimista: nasconde subito la guida anche se la chiamata al backend
    // fallisse o fosse lenta, così l'utente non resta bloccato a guardarla.
    setUser((prev) => (prev ? { ...prev, onboarding_seen: true } : prev));
    try { await markOnboardingSeenApi(); } catch (e) {}
  };

  const dismissCapterraReview = async () => {
    // Stesso pattern ottimista di markOnboardingSeen.
    setUser((prev) => (prev ? { ...prev, capterra_review_dismissed: true } : prev));
    try { await markCapterraReviewDismissedApi(); } catch (e) {}
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, markOnboardingSeen, dismissCapterraReview, exitImpersonation }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);

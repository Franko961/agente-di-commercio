import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { setSessionRecordingEnabled } from "../lib/analytics";
import { useCookieConsent } from "../contexts/CookieConsentContext";

// Attiva la registrazione di sessione PostHog SOLO sulle pagine pubbliche,
// mai dentro /app: essendo una SPA con un unico index.html, senza questo
// componente lo stesso script girerebbe identico anche nell'area
// autenticata del CRM (nomi clienti, importi, documenti, conversazioni AI).
// Non fa nulla se l'utente non ha ancora dato consenso analytics (PostHog
// non è nemmeno caricato in quel caso, vedi lib/analytics.js).
//
// Dipende anche da "consent", non solo dal path: PostHog viene caricato in
// modo asincrono DOPO che l'utente accetta (vedi CookieConsentContext), in
// un momento che non coincide con un cambio di rotta — senza "consent" tra
// le dipendenze, accettare il consenso su una pagina pubblica senza mai
// navigare altrove lascerebbe la registrazione disattivata per sempre,
// perché l'effetto non ririeseguirebbe la valutazione.
export default function AnalyticsRouteGuard() {
  const location = useLocation();
  const { consent } = useCookieConsent();

  useEffect(() => {
    setSessionRecordingEnabled(!location.pathname.startsWith("/app"));
  }, [location.pathname, consent]);

  return null;
}

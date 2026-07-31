import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { loadGoogleAnalytics, loadPostHog, optOutPostHog } from "../lib/analytics";

// Persistenza locale della scelta di consenso: nessun cookie/analytics non
// essenziale viene caricato finché l'utente non ha scelto esplicitamente
// (banner in CookieConsentBanner.jsx) — prima di questo, GA e PostHog
// partivano incondizionatamente da public/index.html.
const STORAGE_KEY = "salesfly_cookie_consent_v1";

function readStoredConsent() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function writeStoredConsent(value) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
  } catch {
    // localStorage non disponibile (es. modalità privata restrittiva): la
    // scelta semplicemente non persiste tra le sessioni, non è un errore
    // che deve bloccare l'uso del sito.
  }
}

const CookieConsentContext = createContext(null);

export function CookieConsentProvider({ children }) {
  const [consent, setConsent] = useState(() => readStoredConsent());
  const [bannerOpen, setBannerOpen] = useState(() => readStoredConsent() === null);

  useEffect(() => {
    if (consent?.analytics) {
      loadGoogleAnalytics();
      loadPostHog();
    }
  }, [consent]);

  const acceptAll = useCallback(() => {
    const value = { analytics: true, decidedAt: new Date().toISOString() };
    writeStoredConsent(value);
    setConsent(value);
    setBannerOpen(false);
  }, []);

  const rejectAll = useCallback(() => {
    const value = { analytics: false, decidedAt: new Date().toISOString() };
    writeStoredConsent(value);
    setConsent(value);
    setBannerOpen(false);
    optOutPostHog();
  }, []);

  const openPreferences = useCallback(() => setBannerOpen(true), []);
  const closePreferences = useCallback(() => setBannerOpen(false), []);

  return (
    <CookieConsentContext.Provider
      value={{ consent, bannerOpen, acceptAll, rejectAll, openPreferences, closePreferences }}
    >
      {children}
    </CookieConsentContext.Provider>
  );
}

export function useCookieConsent() {
  const ctx = useContext(CookieConsentContext);
  if (!ctx) throw new Error("useCookieConsent va usato dentro CookieConsentProvider");
  return ctx;
}

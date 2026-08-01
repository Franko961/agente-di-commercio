import { Link } from "react-router-dom";
import { useCookieConsent } from "../contexts/CookieConsentContext";

export default function CookieConsentBanner() {
  const { bannerOpen, acceptAll, rejectAll, closePreferences, consent } = useCookieConsent();
  if (!bannerOpen) return null;

  // Se si riapre da "Preferenze cookie" con una scelta già fatta, permette
  // di chiudere senza essere costretti a ridecidere adesso.
  const alreadyDecided = consent !== null && consent !== undefined;

  return (
    <div className="fixed bottom-0 inset-x-0 z-[100] bg-white border-t border-[#E4E4E1] shadow-[0_-4px_16px_rgba(0,0,0,0.08)] px-6 py-4">
      <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-start md:items-center gap-4">
        <p className="text-[13px] text-[#52525B] flex-1">
          Usiamo i cookie tecnici necessari al funzionamento del sito, sempre attivi. Con il tuo
          consenso, usiamo anche cookie di analisi (Google Analytics, PostHog) per capire come viene
          usato il sito. Nell'area gestionale autenticata — dove vedi i dati reali dei tuoi clienti —
          non registriamo mai le sessioni. Puoi cambiare la tua scelta in qualsiasi momento dalla
          pagina{" "}
          <Link to="/privacy" className="underline text-[#0A192F]">Privacy</Link>.
        </p>
        <div className="flex gap-2 shrink-0">
          {alreadyDecided && (
            <button
              onClick={closePreferences}
              className="px-3 py-2 text-[13px] font-medium text-[#A1A1AA] hover:text-[#52525B]"
            >
              Chiudi
            </button>
          )}
          <button
            onClick={rejectAll}
            className="px-4 py-2 text-[13px] font-medium border border-[#E4E4E1] rounded-md hover:bg-[#F9F9F8]"
          >
            Rifiuta
          </button>
          <button
            onClick={acceptAll}
            className="px-4 py-2 text-[13px] font-medium bg-[#0A192F] text-white rounded-md hover:bg-[#172A45]"
          >
            Accetta
          </button>
        </div>
      </div>
    </div>
  );
}

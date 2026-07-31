import { Facebook } from "lucide-react";
import { useCookieConsent } from "../contexts/CookieConsentContext";

export default function PublicFooter() {
  const { openPreferences } = useCookieConsent();
  return (
    <footer className="border-t border-[#E4E4E1] py-6 px-6">
      <div className="max-w-5xl mx-auto flex items-center justify-center gap-3 text-[12px] text-[#A1A1AA] flex-wrap">
        <span>© 2026 SALESFLY. · Gestionale per agenti di commercio</span>
        <button onClick={openPreferences} className="underline hover:text-[#52525B]">
          Preferenze cookie
        </button>
        <a
          href="https://www.facebook.com/salesflycrm"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="SalesFly su Facebook"
          className="w-8 h-8 flex items-center justify-center rounded-full bg-[#0A192F] text-white hover:bg-[#FF5A00] transition-colors shrink-0"
        >
          <Facebook className="w-4 h-4" />
        </a>
      </div>
    </footer>
  );
}

import { Facebook, Star } from "lucide-react";
import { useCookieConsent } from "../contexts/CookieConsentContext";

export default function PublicFooter() {
  const { openPreferences } = useCookieConsent();
  return (
    <footer className="border-t border-[#E4E4E1] py-6 px-6">
      <div className="max-w-5xl mx-auto flex items-center justify-center gap-3 text-[12px] text-[#6B6B72] flex-wrap">
        <span>© 2026 SALESFLY. · Gestionale per agenti di commercio</span>
        <button onClick={openPreferences} className="underline hover:text-[#52525B]">
          Preferenze cookie
        </button>
        <a
          href="https://www.facebook.com/salesflycrm"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="SalesFly su Facebook"
          className="w-8 h-8 flex items-center justify-center rounded-full bg-[#0A192F] text-white hover:bg-[#B23E00] transition-colors shrink-0"
        >
          <Facebook className="w-4 h-4" />
        </a>
        <a
          href="https://www.capterra.com/p/10182022/Salesfly/"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="SalesFly su Capterra"
          className="w-8 h-8 flex items-center justify-center rounded-full bg-[#0A192F] text-white hover:bg-[#B23E00] transition-colors shrink-0"
        >
          <Star className="w-4 h-4" />
        </a>
      </div>
    </footer>
  );
}

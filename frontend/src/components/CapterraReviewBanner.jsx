import { Star, X } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";

const CAPTERRA_URL = "https://www.capterra.com/p/10182022/Salesfly/";
const DAYS_BEFORE_SHOWING = 14;

// Banner discreto (non un modale, non urgente come ImpersonationBanner)
// che invita a lasciare una recensione su Capterra — solo a chi ha avuto
// il tempo di farsi un'idea reale del prodotto (14 giorni dall'iscrizione,
// la durata della prova gratuita) e non l'ha già chiuso. Stesso schema
// "chiudi una volta per sempre" di OnboardingTour/onboarding_seen: campo
// piatto sul documento utente, aggiornato in modo ottimista da
// AuthContext.dismissCapterraReview.
export default function CapterraReviewBanner() {
  const { user, dismissCapterraReview } = useAuth();

  if (!user || user.capterra_review_dismissed || !user.created_at) return null;
  const daysSinceCreated = (Date.now() - new Date(user.created_at).getTime()) / 86400000;
  if (daysSinceCreated < DAYS_BEFORE_SHOWING) return null;

  return (
    <div className="mx-4 md:mx-6 mt-4 bg-[#FFF7ED] border border-[#FED7AA] rounded-lg px-4 py-3 flex items-center gap-3 flex-wrap">
      <Star className="w-4 h-4 text-[#B23E00] shrink-0" />
      <p className="flex-1 min-w-[200px] text-[13px] text-[#0A0A0A]">
        Usi SalesFly da un po': una recensione su Capterra ci aiuta a farci conoscere da altri agenti come te.
      </p>
      <a
        href={CAPTERRA_URL}
        target="_blank"
        rel="noopener noreferrer"
        onClick={dismissCapterraReview}
        className="text-[12px] font-bold text-[#B23E00] hover:underline shrink-0 whitespace-nowrap"
      >
        Lascia una recensione
      </a>
      <button
        onClick={dismissCapterraReview}
        aria-label="Chiudi"
        className="text-[#6B6B72] hover:text-[#0A0A0A] shrink-0"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

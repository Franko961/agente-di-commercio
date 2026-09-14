import { Link } from "react-router-dom";
import { ArrowRight, Sparkles } from "lucide-react";
import { trackEvent } from "@/lib/analytics";

// CTA condivisa da tutti e 4 i calcolatori (FirrCalculator,
// RitenutaEnasarcoCalculator, RegimeForfettarioCalculator,
// ScontoProvvigioneCalculator), inserita SUBITO dopo il blocco risultato —
// non solo nel banner statico a fondo pagina di CalcolatorePage.jsx, che
// resta ma è troppo lontano dal momento in cui il visitatore vede il
// proprio numero. Chi arriva da Google su un calcolatore è già un agente
// di commercio: non va convinto che gli serve SalesFly, va agganciato nel
// momento in cui il calcolatore gli ha appena risolto un problema reale.
// Compare anche dentro gli articoli blog (stesso componente riusato nel
// blocco "calculator" di BlogPost.jsx), non solo nelle pagine standalone
// /calcolatori/:slug.
export default function CalculatorCTA({ location }) {
  return (
    <div className="mt-4 pt-4 border-t border-[#E4E4E1] flex items-start gap-2.5">
      <Sparkles className="w-4 h-4 text-[#B23E00] shrink-0 mt-0.5" />
      <div>
        <p className="text-[13px] font-medium text-[#0A0A0A] mb-1">
          Vuoi tenere sotto controllo automaticamente provvigioni e mandanti?
        </p>
        <Link
          to="/richiedi-demo"
          onClick={() => trackEvent("cta_click", { location })}
          className="inline-flex items-center gap-1.5 text-[13px] font-bold text-[#B23E00] hover:text-[#e04e00] transition-colors"
        >
          Prova SalesFly gratis <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    </div>
  );
}

import { Suspense } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight } from "lucide-react";
import PublicHeader from "@/components/PublicHeader";
import PublicFooter from "@/components/PublicFooter";
import PageMeta from "@/components/PageMeta";
import { CALCULATORS } from "@/content/calculators";
import { trackEvent } from "@/lib/analytics";

// Pagina generica per un singolo calcolatore, montata una volta per
// calcolatore in App.jsx (<CalcolatorePage calcKey="firr" />, ecc.) invece
// di duplicare la stessa struttura di pagina 3 volte: stesso principio già
// applicato al blocco "cta" condiviso degli articoli blog. Dà a ogni
// calcolatore un URL proprio e indicizzabile — prima esistevano solo
// annegati dentro un articolo specifico, non linkabili da soli.
export default function CalcolatorePage({ calcKey }) {
  const navigate = useNavigate();
  const calc = CALCULATORS[calcKey];
  if (!calc) return null;
  const Calc = calc.component;

  return (
    <div className="min-h-screen bg-[#F9F9F8] flex flex-col">
      <PageMeta path={`/calcolatori/${calc.slug}`} />
      <PublicHeader />

      <main className="flex-1 max-w-2xl mx-auto px-6 py-12 w-full">
        <Link
          to="/calcolatori"
          className="inline-flex items-center gap-1.5 text-[13px] text-[#52525B] hover:text-[#0A192F] mb-6"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Tutti i calcolatori
        </Link>

        <h1 className="font-cabinet font-black text-3xl tracking-tight mb-3">{calc.title}</h1>
        <p className="text-[#52525B] text-[15px] mb-8">{calc.description}</p>

        <Suspense fallback={null}>
          <Calc />
        </Suspense>

        {calc.articleSlug && (
          <p className="text-[13px] text-[#52525B] mt-2">
            Il calcolo spiegato passo per passo:{" "}
            <Link to={`/blog/${calc.articleSlug}`} className="underline text-[#0A192F] font-medium">
              leggi la guida completa
            </Link>
          </p>
        )}

        <div className="mt-10 bg-[#0A192F] text-white rounded-xl p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="font-cabinet font-black text-lg mb-1">
              Questo calcolo, già fatto per ogni mandante
            </div>
            <p className="text-[14px] text-white/70">
              SalesFly applica automaticamente l'aliquota giusta a ogni provvigione, mandante per
              mandante — 14 giorni di prova gratuita, senza carta di credito.
            </p>
          </div>
          <button
            onClick={() => {
              trackEvent("cta_click", { location: "calcolatore_page", calculator: calc.slug });
              navigate("/richiedi-demo");
            }}
            className="shrink-0 inline-flex items-center gap-2 bg-[#B23E00] text-white rounded-lg px-5 py-3 text-[14px] font-bold hover:bg-[#e04e00] transition-colors whitespace-nowrap"
          >
            Inizia prova gratuita
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}

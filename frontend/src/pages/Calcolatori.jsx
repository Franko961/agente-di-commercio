import { Link } from "react-router-dom";
import { Calculator, ArrowRight } from "lucide-react";
import PublicHeader from "@/components/PublicHeader";
import PublicFooter from "@/components/PublicFooter";
import PageMeta from "@/components/PageMeta";
import { CALCULATORS } from "@/content/calculators";

// Hub che raccoglie tutti i calcolatori in un unico posto linkabile — prima
// ognuno esisteva solo annegato dentro un articolo blog specifico, senza un
// punto d'ingresso comune. Legge da content/calculators.js: un nuovo
// calcolatore aggiunto lì compare qui automaticamente, senza toccare
// questa pagina.
export default function Calcolatori() {
  return (
    <div className="min-h-screen bg-[#F9F9F8] flex flex-col">
      <PageMeta path="/calcolatori" />
      <PublicHeader />

      <main className="flex-1 max-w-3xl mx-auto px-6 py-16 w-full">
        <h1 className="font-cabinet font-black text-4xl tracking-tight mb-3">
          Calcolatori per agenti di commercio
        </h1>
        <p className="text-[#52525B] text-[15px] mb-10 max-w-xl">
          Strumenti gratuiti, senza registrazione: stime rapide su FIRR, ritenuta d'acconto,
          contributo ENASARCO e regime forfettario.
        </p>

        <div className="grid sm:grid-cols-2 gap-4">
          {Object.values(CALCULATORS).map((calc) => (
            <Link
              key={calc.slug}
              to={`/calcolatori/${calc.slug}`}
              className="group bg-white border border-[#E4E4E1] rounded-xl p-6 hover:border-[#0A192F] transition-colors"
            >
              <Calculator className="w-5 h-5 text-[#B23E00] mb-3" />
              <div className="font-cabinet font-bold text-[15px] mb-1.5">{calc.title}</div>
              <p className="text-[13px] text-[#52525B] mb-3">{calc.description}</p>
              <span className="inline-flex items-center gap-1 text-[13px] font-medium text-[#0A192F]">
                Apri il calcolatore
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
              </span>
            </Link>
          ))}
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}

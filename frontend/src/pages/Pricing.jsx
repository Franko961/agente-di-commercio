import { useNavigate } from "react-router-dom";
import { Check, Zap, Star } from "lucide-react";
import usePlans from "../hooks/usePlans";
import PublicHeader from "@/components/PublicHeader";
import PublicFooter from "@/components/PublicFooter";
import PageMeta from "@/components/PageMeta";
import Reveal from "@/components/Reveal";

export default function Pricing() {
  const navigate = useNavigate();
  const { plansById, trialDays, loading } = usePlans();
  const base = plansById.base;
  const pro = plansById.pro;

  if (loading || !base || !pro) {
    return <div className="min-h-screen flex items-center justify-center text-[#6B6B72]">Caricamento…</div>;
  }

  return (
    <div className="min-h-screen bg-[#F9F9F8] flex flex-col">
      <PageMeta
        path="/prezzi"
        description={`Piani ${base.name} (€${base.price_eur}/mese) e ${pro.name} (€${pro.price_eur}/mese) per il CRM SALESFLY. ${trialDays} giorni di prova gratuita, nessuna carta di credito richiesta.`}
      />
      <PublicHeader />

      <main className="flex-1 px-6 py-16 max-w-5xl mx-auto w-full">
        {/* Hero */}
        <div className="text-center mb-12">
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#B23E00] mb-3">Piani e prezzi</div>
          <h1 className="font-cabinet font-black text-4xl md:text-5xl tracking-tight mb-4">
            Semplice, trasparente,<br />senza sorprese.
          </h1>
          <p className="text-[16px] text-[#52525B] max-w-xl mx-auto">
            {trialDays} giorni di prova gratuita su tutti i piani. Nessuna carta di credito richiesta.
          </p>
          <p className="text-[13px] text-[#6B6B72] max-w-xl mx-auto mt-2">
            Dopo la prova, l'abbonamento si rinnova automaticamente ogni mese finché non lo disdici: nessun vincolo contrattuale.
          </p>
        </div>

        {/* Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-3xl mx-auto">

          {/* Base */}
          <Reveal className="bg-white border border-[#E4E4E1] rounded-xl p-8">
            <div className="flex items-center gap-2 mb-2">
              <Zap className="w-5 h-5 text-[#52525B]" />
              <span className="font-cabinet font-bold text-lg">{base.name}</span>
            </div>
            {base.tagline && <p className="text-[13px] text-[#52525B] mb-4">{base.tagline}</p>}
            <div className="mb-6">
              <span className="font-cabinet font-black text-4xl">€{base.price_eur}</span>
              <span className="text-[#52525B] text-[14px]">/mese</span>
              <div className="text-[12px] text-[#6B6B72] mt-1">€{(base.price_eur * 12).toFixed(0)}/anno · IVA non dovuta (regime forfettario)</div>
            </div>
            <button onClick={() => navigate("/richiedi-demo")}
              className="w-full py-3 border-2 border-[#0A192F] text-[#0A192F] rounded-lg text-[14px] font-bold mb-6 hover:bg-[#0A192F] hover:text-white transition-colors">
              Inizia prova gratuita
            </button>
            <div className="space-y-3">
              {[...base.features, `${trialDays} giorni di prova gratuita`].map(f => (
                <div key={f} className="flex items-start gap-2.5 text-[13px]">
                  <Check className="w-4 h-4 text-[#059669] shrink-0 mt-0.5" />
                  <span>{f}</span>
                </div>
              ))}
            </div>
          </Reveal>

          {/* Pro */}
          <Reveal delay={100} className="bg-[#0A192F] text-white rounded-xl p-8 relative overflow-hidden">
            <div className="absolute top-4 right-4 bg-[#B23E00] text-white font-mono text-[9px] uppercase tracking-widest px-2 py-1 rounded">
              Più popolare
            </div>
            <div className="flex items-center gap-2 mb-2">
              <Star className="w-5 h-5 text-[#B23E00]" />
              <span className="font-cabinet font-bold text-lg">{pro.name}</span>
            </div>
            {pro.tagline && <p className="text-[13px] text-white/70 mb-4">{pro.tagline}</p>}
            <div className="mb-6">
              <span className="font-cabinet font-black text-4xl">€{pro.price_eur}</span>
              <span className="text-white/60 text-[14px]">/mese</span>
              <div className="text-[12px] text-white/40 mt-1">€{(pro.price_eur * 12).toFixed(0)}/anno · IVA non dovuta (regime forfettario)</div>
            </div>
            <button onClick={() => navigate("/richiedi-demo")}
              className="w-full py-3 bg-[#B23E00] text-white rounded-lg text-[14px] font-bold mb-6 hover:bg-[#e04e00] transition-colors">
              Inizia prova gratuita
            </button>
            <div className="space-y-3">
              {pro.features.map(f => (
                <div key={f} className="flex items-start gap-2.5 text-[13px]">
                  <Check className="w-4 h-4 text-[#B23E00] shrink-0 mt-0.5" />
                  <span className="text-white/80">{f}</span>
                </div>
              ))}
            </div>
          </Reveal>
        </div>

        {/* FAQ */}
        <div className="mt-16 max-w-2xl mx-auto">
          <h2 className="font-cabinet font-black text-2xl mb-6 text-center">Domande frequenti</h2>
          <div className="space-y-4">
            {[
              ["Posso cambiare piano in qualsiasi momento?", "Sì, puoi passare da Base a Pro o viceversa: disdici il piano attuale dall'area abbonamento (resti attivo fino a fine periodo) e, una volta terminato, potrai attivare il nuovo piano. Per un cambio prima di allora, contattaci e ti aiutiamo noi."],
              ["Come funziona la prova gratuita?", `Hai ${trialDays} giorni per testare tutte le funzionalità senza inserire dati di pagamento. Al termine scegli il piano che preferisci.`],
              ["Posso cancellare quando voglio?", "Sì, nessun vincolo contrattuale. Puoi cancellare in qualsiasi momento dall'area abbonamento."],
              ["Quali metodi di pagamento accettate?", "Accettiamo carte di credito/debito tramite Stripe (Visa, Mastercard, Amex) e PayPal."],
            ].map(([q, a], i) => (
              <Reveal key={q} delay={i * 60} className="bg-white border border-[#E4E4E1] rounded-lg p-5">
                <div className="font-cabinet font-bold text-[14px] mb-2">{q}</div>
                <div className="text-[13px] text-[#52525B]">{a}</div>
              </Reveal>
            ))}
          </div>
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}

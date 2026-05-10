import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check, Zap, Star } from "lucide-react";

const FEATURES_BASE = [
  "Clienti e anagrafiche illimitati",
  "Agenda e appuntamenti",
  "Offerte e preventivi",
  "Provvigioni e scala premi",
  "Archivio documenti (S3)",
  "Pipeline lead (Kanban)",
  "Mappa clienti geolocalizzata",
  "Assistente AI (50 msg/mese)",
  "14 giorni di prova gratuita",
];

const FEATURES_PRO = [
  "Tutto il piano Base",
  "Assistente AI illimitato",
  "Memoria AI persistente",
  "AI può modificare il CRM",
  "Scala premi avanzata",
  "Statistiche per settore",
  "Esportazione CSV avanzata",
  "Supporto prioritario",
  "Aggiornamenti anticipati",
];

export default function Pricing() {
  const navigate = useNavigate();
  const [billing] = useState("monthly");

  return (
    <div className="min-h-screen bg-[#F9F9F8] flex flex-col">
      {/* Header */}
      <header className="border-b border-[#E4E4E1] bg-white px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-[#0A192F] rounded-md flex items-center justify-center">
            <span className="text-white font-cabinet font-black text-sm">A</span>
          </div>
          <span className="font-cabinet font-black text-lg">AGENTE.</span>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => navigate("/login")} className="text-[13px] text-[#52525B] hover:text-[#0A192F]">Accedi</button>
          <button onClick={() => navigate("/register")} className="px-4 py-2 bg-[#0A192F] text-white rounded-md text-[13px] font-medium">Inizia gratis</button>
        </div>
      </header>

      <main className="flex-1 px-6 py-16 max-w-5xl mx-auto w-full">
        {/* Hero */}
        <div className="text-center mb-12">
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00] mb-3">Piani e prezzi</div>
          <h1 className="font-cabinet font-black text-4xl md:text-5xl tracking-tight mb-4">
            Semplice, trasparente,<br />senza sorprese.
          </h1>
          <p className="text-[16px] text-[#52525B] max-w-xl mx-auto">
            14 giorni di prova gratuita su tutti i piani. Nessuna carta di credito richiesta.
          </p>
        </div>

        {/* Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-3xl mx-auto">

          {/* Base */}
          <div className="bg-white border border-[#E4E4E1] rounded-xl p-8">
            <div className="flex items-center gap-2 mb-4">
              <Zap className="w-5 h-5 text-[#52525B]" />
              <span className="font-cabinet font-bold text-lg">Base</span>
            </div>
            <div className="mb-6">
              <span className="font-cabinet font-black text-4xl">€6</span>
              <span className="text-[#52525B] text-[14px]">/mese</span>
              <div className="text-[12px] text-[#A1A1AA] mt-1">€72/anno · IVA esclusa</div>
            </div>
            <button onClick={() => navigate("/register?plan=base")}
              className="w-full py-3 border-2 border-[#0A192F] text-[#0A192F] rounded-lg text-[14px] font-bold mb-6 hover:bg-[#0A192F] hover:text-white transition-colors">
              Inizia prova gratuita
            </button>
            <div className="space-y-3">
              {FEATURES_BASE.map(f => (
                <div key={f} className="flex items-start gap-2.5 text-[13px]">
                  <Check className="w-4 h-4 text-[#059669] shrink-0 mt-0.5" />
                  <span>{f}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Pro */}
          <div className="bg-[#0A192F] text-white rounded-xl p-8 relative overflow-hidden">
            <div className="absolute top-4 right-4 bg-[#FF5A00] text-white font-mono text-[9px] uppercase tracking-widest px-2 py-1 rounded">
              Più popolare
            </div>
            <div className="flex items-center gap-2 mb-4">
              <Star className="w-5 h-5 text-[#FF5A00]" />
              <span className="font-cabinet font-bold text-lg">Pro</span>
            </div>
            <div className="mb-6">
              <span className="font-cabinet font-black text-4xl">€11</span>
              <span className="text-white/60 text-[14px]">/mese</span>
              <div className="text-[12px] text-white/40 mt-1">€132/anno · IVA esclusa</div>
            </div>
            <button onClick={() => navigate("/register?plan=pro")}
              className="w-full py-3 bg-[#FF5A00] text-white rounded-lg text-[14px] font-bold mb-6 hover:bg-[#e04e00] transition-colors">
              Inizia prova gratuita
            </button>
            <div className="space-y-3">
              {FEATURES_PRO.map(f => (
                <div key={f} className="flex items-start gap-2.5 text-[13px]">
                  <Check className="w-4 h-4 text-[#FF5A00] shrink-0 mt-0.5" />
                  <span className="text-white/80">{f}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* FAQ */}
        <div className="mt-16 max-w-2xl mx-auto">
          <h2 className="font-cabinet font-black text-2xl mb-6 text-center">Domande frequenti</h2>
          <div className="space-y-4">
            {[
              ["Posso cambiare piano in qualsiasi momento?", "Sì, puoi passare da Base a Pro o viceversa in qualsiasi momento. Il cambio è immediato."],
              ["Come funziona la prova gratuita?", "Hai 14 giorni per testare tutte le funzionalità senza inserire dati di pagamento. Al termine scegli il piano che preferisci."],
              ["Posso cancellare quando voglio?", "Sì, nessun vincolo contrattuale. Puoi cancellare in qualsiasi momento dall'area abbonamento."],
              ["Quali metodi di pagamento accettate?", "Accettiamo carte di credito/debito tramite Stripe (Visa, Mastercard, Amex) e PayPal."],
            ].map(([q, a]) => (
              <div key={q} className="bg-white border border-[#E4E4E1] rounded-lg p-5">
                <div className="font-cabinet font-bold text-[14px] mb-2">{q}</div>
                <div className="text-[13px] text-[#52525B]">{a}</div>
              </div>
            ))}
          </div>
        </div>
      </main>

      <footer className="border-t border-[#E4E4E1] py-6 text-center text-[12px] text-[#A1A1AA]">
        © 2026 AGENTE. · Gestionale per agenti di commercio
      </footer>
    </div>
  );
}

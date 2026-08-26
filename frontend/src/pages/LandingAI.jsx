import { Link, useNavigate } from "react-router-dom";
import {
  Sparkles, ArrowRight, ShieldCheck, UserPlus, CalendarPlus, KanbanSquare,
  StickyNote, FileText, Receipt, Search, Mic, CheckCircle2, Lock,
} from "lucide-react";
import PublicFooter from "@/components/PublicFooter";
import PageMeta from "@/components/PageMeta";
import usePlans from "../hooks/usePlans";

// Pagina di atterraggio dedicata a campagne pubblicitarie sull'assistente AI
// (la differenziazione più unica del prodotto), non collegata dalla
// navigazione principale — si arriva solo da un link diretto o da un
// annuncio. Header ridotto a logo + singola call-to-action (niente link di
// navigazione che distraggono dalla conversione, a differenza di
// PublicHeader usato dalle pagine raggiungibili dal menu).
//
// Ogni azione elencata sotto è una delle CRM_TOOLS realmente disponibili
// all'assistente (vedi backend/services/ai_service.py): non abbiamo scritto
// funzionalità che l'AI non può davvero eseguire.
const AZIONI_REALI = [
  { icon: UserPlus, title: "Aggiunge un cliente", desc: "\"Aggiungi il cliente Bar Rossi a Milano\" — il cliente è già in anagrafica." },
  { icon: CalendarPlus, title: "Fissa un appuntamento", desc: "\"Segna una visita da Bianchi Srl venerdì alle 10\" — appare subito in agenda." },
  { icon: KanbanSquare, title: "Aggiunge un lead", desc: "\"Nuovo lead: Verdi Impianti, contattato oggi\" — entra in pipeline." },
  { icon: StickyNote, title: "Aggiunge una nota", desc: "\"Segna che Rossi vuole essere richiamato a settembre\" — resta sulla scheda cliente." },
  { icon: FileText, title: "Prepara un'offerta", desc: "Ti propone l'offerta con prodotti e prezzi: la crea solo dopo la tua conferma." },
  { icon: Receipt, title: "Registra una spesa", desc: "\"Segna 40 euro di carburante\" — tracciata subito, categorizzata." },
  { icon: Search, title: "Cerca nel CRM", desc: "\"Quali clienti non visito da 3 mesi?\" — risposta immediata, dati veri." },
];

export default function LandingAI() {
  const navigate = useNavigate();
  const { trialDays } = usePlans();

  return (
    <div className="min-h-screen bg-[#F9F9F8]">
      <PageMeta path="/assistente-ai">
        <script type="application/ld+json">
          {JSON.stringify({
            "@context": "https://schema.org",
            "@type": "SoftwareApplication",
            name: "SALESFLY",
            applicationCategory: "BusinessApplication",
            operatingSystem: "Web",
            description:
              "L'assistente AI di SALESFLY aggiunge clienti, appuntamenti, lead e note nel CRM al posto tuo, non si limita a darti consigli.",
            url: "https://salesfly.it/assistente-ai",
          })}
        </script>
      </PageMeta>

      {/* Header minimo: solo logo + CTA, niente link di navigazione che
      distraggono da una pagina pensata per una singola azione. */}
      <header className="border-b border-[#E4E4E1] bg-white">
        <div className="px-6 py-4 flex items-center justify-between max-w-5xl mx-auto">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-9 h-9 flex items-center justify-center shrink-0">
              <img src="/logo-mark.webp" alt="SALESFLY" className="w-full h-full object-contain" />
            </div>
            <span className="font-cabinet font-black text-lg">SALESFLY.</span>
          </Link>
          <div className="flex items-center gap-3">
            <button onClick={() => navigate("/login")} className="hidden sm:inline-block text-[13px] text-[#52525B] hover:text-[#0A192F]">
              Accedi
            </button>
            <button
              onClick={() => navigate("/richiedi-demo")}
              className="px-4 py-2 bg-[#B23E00] text-white rounded-md text-[13px] font-bold hover:bg-[#e04e00] transition-colors"
            >
              Prova gratis
            </button>
          </div>
        </div>
      </header>

      <main>
        {/* Hero */}
        <section className="px-6 pt-14 pb-14 text-center">
          <div className="max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-1.5 font-mono text-[12px] font-bold uppercase tracking-[0.15em] text-[#B23E00] bg-[#B23E00]/10 border border-[#B23E00]/20 rounded-full px-4 py-1.5 mb-6">
              <Sparkles className="w-3.5 h-3.5" /> Assistente AI
            </div>
            <h1 className="font-cabinet font-black text-4xl md:text-5xl tracking-tight mb-5">
              L'unico CRM con un assistente che il lavoro non lo spiega. Lo fa.
            </h1>
            <p className="text-[16px] md:text-[18px] text-[#52525B] mb-8 max-w-2xl mx-auto">
              Altri assistenti AI nei CRM ti danno consigli da leggere. Il nostro apre il gestionale
              al posto tuo: parli o scrivi, e clienti, appuntamenti, lead e note sono già aggiornati —
              mentre tu sei ancora dal cliente.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <button
                onClick={() => navigate("/richiedi-demo")}
                className="w-full sm:w-auto px-6 py-3.5 bg-[#B23E00] text-white rounded-lg text-[15px] font-bold hover:bg-[#e04e00] transition-colors flex items-center justify-center gap-2"
              >
                Prova gratis {trialDays} giorni <ArrowRight className="w-4 h-4" />
              </button>
            </div>
            <div className="font-mono text-[11px] uppercase tracking-widest text-[#6B6B72] mt-4">
              Nessuna carta di credito richiesta
            </div>
          </div>
        </section>

        {/* Cosa fa davvero */}
        <section className="px-6 py-16 bg-white border-y border-[#E4E4E1]">
          <div className="max-w-5xl mx-auto">
            <div className="text-center mb-12">
              <h2 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight mb-3">
                Cosa fa davvero, non cosa "potrebbe" fare
              </h2>
              <p className="text-[15px] text-[#52525B] max-w-xl mx-auto">
                Ogni azione qui sotto è reale: puoi provarle tutte nella demo gratuita.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {AZIONI_REALI.map(({ icon: Icon, title, desc }) => (
                <div key={title} className="bg-[#F9F9F8] border border-[#E4E4E1] rounded-xl p-5">
                  <div className="w-10 h-10 bg-[#0A192F] rounded-lg flex items-center justify-center mb-4">
                    <Icon className="w-5 h-5 text-white" strokeWidth={1.75} />
                  </div>
                  <div className="font-cabinet font-bold text-[15px] mb-2">{title}</div>
                  <p className="text-[13px] text-[#52525B] leading-relaxed">{desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Come funziona */}
        <section className="px-6 py-16 max-w-4xl mx-auto">
          <h2 className="font-cabinet font-black text-3xl tracking-tight text-center mb-12">
            Tre secondi, non tre schermate
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              [Mic, "Parla o scrivi", "Anche dalla macchina, tra un cliente e l'altro: nessuna app diversa da aprire."],
              [CheckCircle2, "L'AI esegue (o chiede conferma)", "Clienti, appuntamenti, lead e note subito. Offerte e azioni più delicate, solo dopo il tuo sì."],
              [Lock, "Resta tutto tracciato", "Ogni azione eseguita dall'assistente è registrata: sai sempre cosa ha fatto e quando."],
            ].map(([Icon, t, d]) => (
              <div key={t}>
                <div className="w-11 h-11 bg-[#0A192F] rounded-lg flex items-center justify-center mb-4">
                  <Icon className="w-5 h-5 text-white" strokeWidth={1.75} />
                </div>
                <div className="font-cabinet font-bold text-[16px] mb-2">{t}</div>
                <p className="text-[13px] text-[#52525B] leading-relaxed">{d}</p>
              </div>
            ))}
          </div>
        </section>

        {/* CTA banda */}
        <section className="px-6 py-16 bg-[#0A192F]">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="font-cabinet font-black text-3xl md:text-4xl text-white tracking-tight mb-4">
              Prova l'assistente con i tuoi clienti veri
            </h2>
            <p className="text-white/60 text-[15px] mb-8 max-w-xl mx-auto">
              {trialDays} giorni gratis, nessuna carta di credito, nessun vincolo.
            </p>
            <button
              onClick={() => navigate("/richiedi-demo")}
              className="px-7 py-3.5 bg-[#B23E00] text-white rounded-lg text-[15px] font-bold hover:bg-[#e04e00] transition-colors inline-flex items-center gap-2"
            >
              Inizia gratis <ArrowRight className="w-4 h-4" />
            </button>
            <div className="flex items-center justify-center gap-2 mt-6 text-white/40 text-[12px] font-mono uppercase tracking-widest">
              <ShieldCheck className="w-4 h-4" /> Dati protetti · Conforme al GDPR
            </div>
          </div>
        </section>
      </main>

      <PublicFooter />
    </div>
  );
}

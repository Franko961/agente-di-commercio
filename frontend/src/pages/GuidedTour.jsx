import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import { ArrowRight, Sparkles, Zap } from "lucide-react";
import PublicHeader from "@/components/PublicHeader";
import PublicFooter from "@/components/PublicFooter";

// Cornice comune per ogni anteprima: ricostruzione stilizzata delle
// schermate reali (stessi colori/layout dell'app, dati di esempio), non
// screenshot veri — stesso principio già usato per il mockup telefono
// nella hero della landing.
function MockupFrame({ children }) {
  return (
    <div className="bg-white rounded-xl border border-[#E4E4E1] shadow-xl overflow-hidden w-full max-w-sm mx-auto md:mx-0">
      <div className="flex items-center gap-1.5 px-3 py-2 bg-[#F3F3F1] border-b border-[#E4E4E1]">
        <div className="w-2 h-2 rounded-full bg-[#DC2626]" />
        <div className="w-2 h-2 rounded-full bg-[#FF5A00]" />
        <div className="w-2 h-2 rounded-full bg-[#059669]" />
      </div>
      <div className="p-4 bg-[#F9F9F8] min-h-[260px] flex flex-col justify-center">
        {children}
      </div>
    </div>
  );
}

function DashboardVisual() {
  return (
    <MockupFrame>
      <div className="grid grid-cols-3 gap-2 mb-3">
        {[["7", "Visite"], ["2", "Scadenze"], ["€180", "Obiettivo"]].map(([v, l]) => (
          <div key={l} className="bg-white border border-[#E4E4E1] rounded-md p-2 text-center">
            <div className="font-cabinet font-black text-lg">{v}</div>
            <div className="text-[9px] text-[#52525B] font-mono uppercase tracking-widest">{l}</div>
          </div>
        ))}
      </div>
      <div className="bg-[#FFF7ED] border border-[#FED7AA] rounded-md p-2.5 flex items-start gap-2 mb-3">
        <Sparkles className="w-3.5 h-3.5 text-[#FF5A00] shrink-0 mt-0.5" />
        <div className="text-[11px] text-[#0A0A0A]">Visita prima Rossi Spa: l'offerta scade venerdì.</div>
      </div>
      <div className="bg-white border border-[#E4E4E1] rounded-md p-2.5">
        <div className="flex justify-between text-[10px] font-mono uppercase text-[#52525B] mb-1">
          <span>Fatturato del mese</span><span>72%</span>
        </div>
        <div className="h-1.5 bg-[#F3F3F1] rounded-full overflow-hidden">
          <div className="h-full bg-[#FF5A00]" style={{ width: "72%" }} />
        </div>
      </div>
    </MockupFrame>
  );
}

function ClientiVisual() {
  const clients = [
    ["RS", "Rossi Spa", "Ancona", "alto"],
    ["BT", "Bianchi Tessuti", "Pesaro", "medio"],
    ["CA", "Caffè Aurora", "Fermo", "alto"],
  ];
  return (
    <MockupFrame>
      <div className="space-y-2">
        {clients.map(([init, name, city, pot]) => (
          <div key={name} className="bg-white border border-[#E4E4E1] rounded-md p-2.5 flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-[#0A192F] text-white flex items-center justify-center font-cabinet font-bold text-[11px] shrink-0">{init}</div>
            <div className="min-w-0 flex-1">
              <div className="font-cabinet font-bold text-[12px] truncate">{name}</div>
              <div className="text-[10px] text-[#52525B]">{city}</div>
            </div>
            <div className={`text-[8px] font-mono uppercase px-1.5 py-0.5 rounded shrink-0 ${pot === "alto" ? "bg-[#05966915] text-[#059669]" : "bg-[#FF5A0015] text-[#FF5A00]"}`}>{pot}</div>
          </div>
        ))}
      </div>
    </MockupFrame>
  );
}

function LeadVisual() {
  const cols = [
    { label: "Nuovo", color: "#52525B", items: ["Ferramenta Blu"] },
    { label: "Contattato", color: "#0A192F", items: ["Studio Verdi"] },
    { label: "Trattativa", color: "#FF5A00", items: ["Bar Centrale", "Hotel Adria"] },
    { label: "Vinto", color: "#059669", items: ["Pasticceria Neri"] },
  ];
  return (
    <MockupFrame>
      <div className="grid grid-cols-4 gap-1.5">
        {cols.map((c) => (
          <div key={c.label} className="min-w-0">
            <div className="text-[6.5px] font-mono uppercase tracking-wide mb-1 truncate" style={{ color: c.color }}>{c.label}</div>
            <div className="space-y-1">
              {c.items.map((it) => (
                <div key={it} className="bg-white border border-[#E4E4E1] rounded p-1.5 text-[7.5px] font-medium leading-tight">{it}</div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </MockupFrame>
  );
}

function AgendaVisual() {
  const days = ["LUN", "MAR", "MER", "GIO", "VEN"];
  const appts = { 0: ["10:00 Studio Verdi"], 2: ["11:30 Bianchi"], 4: ["15:00 Caffè Aurora"] };
  return (
    <MockupFrame>
      <div className="grid grid-cols-5 gap-1">
        {days.map((d, i) => (
          <div key={d} className={`bg-white border rounded p-1 min-h-[100px] ${i === 2 ? "border-[#FF5A00]" : "border-[#E4E4E1]"}`}>
            <div className="text-[6px] font-mono text-[#A1A1AA] text-center">{d}</div>
            <div className="text-[10px] font-cabinet font-black text-center mb-1">{22 + i}</div>
            {(appts[i] || []).map((a) => (
              <div key={a} className="bg-[#0A192F0D] border-l-2 border-[#FF5A00] rounded-sm px-1 py-0.5 text-[6px] mb-0.5 leading-tight">{a}</div>
            ))}
          </div>
        ))}
      </div>
    </MockupFrame>
  );
}

function AutomazioniVisual() {
  const rules = [
    ["Cliente senza ordini da 90gg", "Crea promemoria"],
    ["Offerta in scadenza", "Invia email"],
    ["Compleanno cliente", "Invia promemoria"],
  ];
  return (
    <MockupFrame>
      <div className="space-y-2">
        {rules.map(([trig, act]) => (
          <div key={trig} className="bg-white border border-[#E4E4E1] rounded-md p-2.5 flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-[#FF5A00] flex items-center justify-center shrink-0">
              <Zap className="w-3 h-3 text-white" />
            </div>
            <div className="min-w-0">
              <div className="text-[9px] text-[#52525B] truncate"><span className="font-mono uppercase text-[7px] text-[#FF5A00]">Quando</span> {trig}</div>
              <div className="text-[9px] text-[#0A0A0A] font-medium truncate"><span className="font-mono uppercase text-[7px] text-[#0A192F]">Allora</span> {act}</div>
            </div>
          </div>
        ))}
      </div>
    </MockupFrame>
  );
}

function AIVisual() {
  return (
    <MockupFrame>
      <div className="space-y-2.5">
        <div className="flex gap-2 flex-row-reverse">
          <div className="w-5 h-5 rounded bg-[#0A192F] flex items-center justify-center shrink-0 text-white text-[7px] font-bold">TU</div>
          <div className="bg-[#0A192F] text-white rounded-md p-2 text-[10px] max-w-[75%]">Aggiungi una visita da Rossi Spa domani alle 10</div>
        </div>
        <div className="flex gap-2">
          <div className="w-5 h-5 rounded bg-[#FF5A00] flex items-center justify-center shrink-0"><Sparkles className="w-2.5 h-2.5 text-white" /></div>
          <div className="bg-white border border-[#E4E4E1] rounded-md p-2 text-[10px] max-w-[75%]">Fatto! Ho creato l'appuntamento con Rossi Spa domani alle 10:00. ✓</div>
        </div>
      </div>
    </MockupFrame>
  );
}

function GiroVisiteVisual() {
  const stops = ["Rossi Spa", "Bianchi Tessuti", "Caffè Aurora"];
  return (
    <MockupFrame>
      <div className="relative bg-[#E8ECF0] rounded-md h-24 mb-2.5 overflow-hidden">
        <svg viewBox="0 0 200 90" className="w-full h-full">
          <path d="M20,70 Q60,20 100,45 T180,20" fill="none" stroke="#FF5A00" strokeWidth="2" strokeDasharray="4 3" />
          {[[20, 70], [100, 45], [180, 20]].map(([x, y], i) => (
            <g key={i}>
              <circle cx={x} cy={y} r="7" fill="#0A192F" />
              <text x={x} y={y + 3} fontSize="8" fill="white" textAnchor="middle" fontWeight="bold">{i + 1}</text>
            </g>
          ))}
        </svg>
      </div>
      <div className="space-y-1.5">
        {stops.map((s, i) => (
          <div key={s} className="flex items-center gap-2 bg-white border border-[#E4E4E1] rounded-md p-1.5">
            <div className="w-4 h-4 rounded-full bg-[#0A192F] text-white flex items-center justify-center text-[8px] font-bold shrink-0">{i + 1}</div>
            <div className="text-[9px] font-medium truncate">{s}</div>
          </div>
        ))}
      </div>
    </MockupFrame>
  );
}

const STEPS = [
  {
    title: "Dashboard",
    sentence: "Un cruscotto che mostra subito cosa fare oggi: visite, offerte in scadenza e quanto manca al tuo obiettivo mensile.",
    Visual: DashboardVisual,
  },
  {
    title: "Clienti",
    sentence: "Tutti i tuoi clienti, contatti e storico visite in un unico posto, sempre a portata di mano.",
    Visual: ClientiVisual,
  },
  {
    title: "Lead",
    sentence: "Traccia ogni trattativa in una pipeline visuale, dalla prima chiamata alla firma.",
    Visual: LeadVisual,
  },
  {
    title: "Agenda",
    sentence: "Appuntamenti e promemoria organizzati automaticamente, senza dimenticare nessuna visita.",
    Visual: AgendaVisual,
  },
  {
    title: "Automazioni",
    sentence: "SalesFly può ricordarti automaticamente di contattare clienti, lead e offerte in scadenza.",
    Visual: AutomazioniVisual,
  },
  {
    title: "Assistente AI",
    sentence: "Parla o scrivi all'assistente: aggiunge clienti, appuntamenti e note al posto tuo.",
    Visual: AIVisual,
  },
  {
    title: "Giro visite",
    sentence: "Pianifica il giro visita ottimale e salvalo direttamente in agenda con un clic.",
    Visual: GiroVisiteVisual,
  },
];

function WelcomeScreen({ onStart }) {
  return (
    <div className="text-center max-w-lg mx-auto">
      <div className="w-16 h-16 mx-auto mb-6">
        <img src="/logo-mark.png" alt="SALESFLY" className="w-full h-full object-contain" />
      </div>
      <h1 className="font-cabinet font-black text-4xl md:text-5xl tracking-tight mb-4">Benvenuto in SalesFly.</h1>
      <p className="text-[16px] md:text-[18px] text-[#52525B] mb-8">
        Ti bastano 3 minuti per imparare le funzioni principali.
      </p>
      <button
        onClick={onStart}
        data-testid="tour-start-button"
        className="px-7 py-3.5 bg-[#FF5A00] text-white rounded-lg text-[15px] font-bold hover:bg-[#e04e00] transition-colors inline-flex items-center gap-2"
      >
        Inizia <ArrowRight className="w-4 h-4" />
      </button>
    </div>
  );
}

function TourStep({ step, index, total, onNext, onPrev, onSkip, isLast }) {
  const Visual = step.Visual;
  return (
    <div className="w-full max-w-4xl mx-auto">
      <div className="flex items-center justify-center gap-2 mb-10">
        {STEPS.map((_, i) => (
          <div key={i} className={`h-1.5 rounded-full transition-all ${i === index ? "w-8 bg-[#FF5A00]" : "w-1.5 bg-[#E4E4E1]"}`} />
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-10 items-center">
        <div className="order-2 md:order-1">
          <Visual />
        </div>
        <div className="order-1 md:order-2 text-center md:text-left">
          <div className="font-mono text-[11px] uppercase tracking-widest text-[#FF5A00] mb-2">
            {index + 1} di {total}
          </div>
          <h2 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight mb-4">{step.title}</h2>
          <p className="text-[16px] text-[#52525B] mb-8">{step.sentence}</p>
          <div className="flex items-center gap-3 justify-center md:justify-start">
            {index > 0 && (
              <button
                onClick={onPrev}
                data-testid="tour-prev-button"
                className="px-5 py-2.5 border-2 border-[#0A192F] text-[#0A192F] rounded-lg text-[14px] font-bold hover:bg-[#0A192F] hover:text-white transition-colors"
              >
                Indietro
              </button>
            )}
            <button
              onClick={onNext}
              data-testid="tour-next-button"
              className="px-5 py-2.5 bg-[#FF5A00] text-white rounded-lg text-[14px] font-bold hover:bg-[#e04e00] transition-colors flex items-center gap-2"
            >
              {isLast ? "Inizia gratis" : "Avanti"} <ArrowRight className="w-4 h-4" />
            </button>
          </div>
          {!isLast && (
            <button onClick={onSkip} className="mt-4 text-[13px] text-[#A1A1AA] hover:text-[#52525B] underline">
              Salta il tour
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default function GuidedTour() {
  const [started, setStarted] = useState(false);
  const [step, setStep] = useState(0);
  const navigate = useNavigate();
  const isLast = step === STEPS.length - 1;

  return (
    <div className="min-h-screen bg-[#F9F9F8] flex flex-col">
      <Helmet>
        <title>Tour guidato — SALESFLY</title>
        <meta name="description" content="Scopri in 3 minuti le funzioni principali di SALESFLY: dashboard, clienti, lead, agenda, automazioni, assistente AI e pianificatore giro visite." />
        <link rel="canonical" href="https://salesfly.it/tour" />
      </Helmet>

      <PublicHeader />

      <main className="flex-1 flex items-center justify-center px-6 py-16">
        {!started ? (
          <WelcomeScreen onStart={() => setStarted(true)} />
        ) : (
          <TourStep
            step={STEPS[step]}
            index={step}
            total={STEPS.length}
            isLast={isLast}
            onPrev={() => setStep((s) => Math.max(0, s - 1))}
            onNext={() => (isLast ? navigate("/richiedi-demo") : setStep((s) => s + 1))}
            onSkip={() => navigate("/")}
          />
        )}
      </main>

      <PublicFooter />
    </div>
  );
}

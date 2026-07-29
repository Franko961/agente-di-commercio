import { Link, useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import PublicHeader from "@/components/PublicHeader";
import PublicFooter from "@/components/PublicFooter";

// Illustrazioni originali (non screenshot dell'app): una scena semplice per
// beneficio, stesso linguaggio visivo (blob di sfondo tenue + forme piatte
// nei colori del brand) per restare coerenti tra loro pur essendo diverse
// dai mockup "schermata reale" usati nel tour guidato e nel centro assistenza.
function IllustrationFrame({ bg, children }) {
  return (
    <div className="relative w-full h-36 rounded-xl flex items-center justify-center overflow-hidden" style={{ background: bg }}>
      {children}
    </div>
  );
}

function GiroVisiteIllustration() {
  return (
    <IllustrationFrame bg="#0A192F0D">
      <svg viewBox="0 0 160 120" className="w-28 h-28">
        <circle cx="40" cy="90" r="2" fill="#0A192F" opacity="0.15" />
        <circle cx="120" cy="30" r="2" fill="#0A192F" opacity="0.15" />
        <circle cx="130" cy="95" r="2" fill="#0A192F" opacity="0.15" />
        <path d="M25,90 Q60,30 85,55 T135,25" fill="none" stroke="#FF5A00" strokeWidth="3" strokeDasharray="6 5" strokeLinecap="round" />
        <g>
          <circle cx="25" cy="90" r="9" fill="#0A192F" />
          <text x="25" y="94" fontSize="10" fill="white" textAnchor="middle" fontWeight="bold">1</text>
        </g>
        <g>
          <circle cx="85" cy="55" r="9" fill="#0A192F" />
          <text x="85" y="59" fontSize="10" fill="white" textAnchor="middle" fontWeight="bold">2</text>
        </g>
        <g>
          <circle cx="135" cy="25" r="10" fill="#FF5A00" />
          <text x="135" y="29" fontSize="10" fill="white" textAnchor="middle" fontWeight="bold">3</text>
        </g>
      </svg>
    </IllustrationFrame>
  );
}

function AIIllustration() {
  return (
    <IllustrationFrame bg="#FF5A000D">
      <svg viewBox="0 0 160 120" className="w-28 h-28">
        <path d="M35,35 h70 a12,12 0 0 1 12,12 v28 a12,12 0 0 1 -12,12 h-40 l-14,14 v-14 h-16 a12,12 0 0 1 -12,-12 v-28 a12,12 0 0 1 12,-12 z" fill="#0A192F" />
        <path d="M70 55 l4 9 9 4 -9 4 -4 9 -4 -9 -9 -4 9 -4 z" fill="#FF5A00" />
        <path d="M118 30 l2.5 5.5 5.5 2.5 -5.5 2.5 -2.5 5.5 -2.5 -5.5 -5.5 -2.5 5.5 -2.5 z" fill="#FF5A00" />
        <path d="M128 78 l2 4.5 4.5 2 -4.5 2 -2 4.5 -2 -4.5 -4.5 -2 4.5 -2 z" fill="#0A192F" opacity="0.5" />
      </svg>
    </IllustrationFrame>
  );
}

function ProvvigioniIllustration() {
  return (
    <IllustrationFrame bg="#0596690D">
      <svg viewBox="0 0 160 120" className="w-28 h-28">
        <ellipse cx="55" cy="88" rx="26" ry="9" fill="#FF5A00" />
        <ellipse cx="55" cy="80" rx="26" ry="9" fill="#FFB27A" />
        <ellipse cx="55" cy="72" rx="26" ry="9" fill="#FF5A00" />
        <text x="55" y="76" fontSize="11" fill="white" textAnchor="middle" fontWeight="bold">€</text>
        <path d="M95,70 L115,45 L125,55 L145,25" fill="none" stroke="#059669" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M133,25 h12 v12" fill="none" stroke="#059669" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </IllustrationFrame>
  );
}

function DocumentiIllustration() {
  return (
    <IllustrationFrame bg="#0A192F0D">
      <svg viewBox="0 0 160 120" className="w-28 h-28">
        <rect x="48" y="30" width="55" height="70" rx="6" fill="#E4E4E1" transform="rotate(-8 75 65)" />
        <rect x="55" y="26" width="55" height="70" rx="6" fill="#0A192F" transform="rotate(4 82 61)" />
        <rect x="52" y="24" width="55" height="70" rx="6" fill="white" stroke="#E4E4E1" strokeWidth="2" />
        <rect x="62" y="38" width="35" height="5" rx="2.5" fill="#FF5A00" />
        <rect x="62" y="50" width="35" height="4" rx="2" fill="#E4E4E1" />
        <rect x="62" y="59" width="35" height="4" rx="2" fill="#E4E4E1" />
        <rect x="62" y="68" width="22" height="4" rx="2" fill="#E4E4E1" />
      </svg>
    </IllustrationFrame>
  );
}

function AutomazioniIllustration() {
  return (
    <IllustrationFrame bg="#FF5A000D">
      <svg viewBox="0 0 160 120" className="w-28 h-28">
        <path d="M80,28 c-15,0 -24,12 -24,26 v16 l-8,10 h64 l-8,-10 v-16 c0,-14 -9,-26 -24,-26 z" fill="#0A192F" />
        <path d="M70,86 a10,10 0 0 0 20,0 z" fill="#0A192F" />
        <path d="M96,20 l7,14 15,2 -11,10 3,15 -14,-7 -14,7 3,-15 -11,-10 15,-2 z" fill="#FF5A00" />
      </svg>
    </IllustrationFrame>
  );
}

function ObiettiviIllustration() {
  return (
    <IllustrationFrame bg="#0A192F0D">
      <svg viewBox="0 0 160 120" className="w-28 h-28">
        <circle cx="60" cy="60" r="34" fill="none" stroke="#E4E4E1" strokeWidth="10" />
        <circle cx="60" cy="60" r="34" fill="none" stroke="#FF5A00" strokeWidth="10" strokeLinecap="round"
          strokeDasharray="181 214" transform="rotate(-90 60 60)" />
        <text x="60" y="66" fontSize="16" fill="#0A192F" textAnchor="middle" fontWeight="900">72%</text>
        <path d="M112,85 v-45 M124,85 v-25 M136,85 v-35" stroke="#0A192F" strokeWidth="7" strokeLinecap="round" />
      </svg>
    </IllustrationFrame>
  );
}

const BENEFITS = [
  {
    emoji: "📍",
    title: "Pianifica il giro visite in pochi secondi.",
    support: "Meno tempo perso in auto, più tempo dai clienti che contano davvero.",
    Illustration: GiroVisiteIllustration,
  },
  {
    emoji: "🤖",
    title: "Ricevi suggerimenti dall'AI sui clienti da contattare.",
    support: "Non rincorri più i clienti a caso: l'AI ti dice chi contattare e, se vuoi, aggiorna lei stessa il CRM al posto tuo.",
    Illustration: AIIllustration,
  },
  {
    emoji: "💰",
    title: "Calcola automaticamente le provvigioni.",
    support: "Niente più fogli di calcolo: sai sempre esattamente quanto hai guadagnato.",
    Illustration: ProvvigioniIllustration,
  },
  {
    emoji: "📄",
    title: "Gestisci offerte, ordini e documenti in un unico posto.",
    support: "Tutto lo storico di un cliente a portata di clic, senza cercare tra email e cartelle.",
    Illustration: DocumentiIllustration,
  },
  {
    emoji: "⚡",
    title: "Automatizza i promemoria per lead, clienti e offerte.",
    support: "Nessuna occasione persa per dimenticanza: ci pensa SalesFly a ricordartelo.",
    Illustration: AutomazioniIllustration,
  },
  {
    emoji: "📊",
    title: "Monitora obiettivi, fatturato e attività quotidiane.",
    support: "Sai sempre, in tempo reale, se sei in linea con i tuoi obiettivi del mese.",
    Illustration: ObiettiviIllustration,
  },
];

export default function WhySalesFly() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[#F9F9F8] flex flex-col">
      <title>Perché SalesFly — Il CRM per Agenti di Commercio</title>
      <meta
        name="description"
        content="L'unico CRM con un assistente che il lavoro non lo spiega: lo fa. Scopri i vantaggi concreti che SalesFly porta nella giornata di un agente di commercio plurimandatario."
      />
      <link rel="canonical" href="https://salesfly.it/perche-salesfly" />

      <PublicHeader />

      <main className="flex-1 px-6 py-16 max-w-5xl mx-auto w-full">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00] mb-4">Perché SalesFly</div>
          <h1 className="font-cabinet font-black text-4xl md:text-5xl tracking-tight mb-5">
            Lavora meno, vendi meglio.
          </h1>
          <p className="text-[16px] md:text-[18px] text-[#52525B]">
            Non è un elenco di funzioni: è quello che cambia davvero nella tua giornata quando smetti di fare a mano quello che SalesFly può fare per te.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-14">
          {BENEFITS.map(({ emoji, title, support, Illustration }) => (
            <div key={title} className="bg-white border border-[#E4E4E1] rounded-xl p-5 flex flex-col">
              <Illustration />
              <div className="mt-4">
                <div className="font-cabinet font-bold text-[15px] leading-snug mb-2">
                  <span className="mr-1.5">{emoji}</span>{title}
                </div>
                <p className="text-[13px] text-[#52525B] leading-relaxed">{support}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="text-center">
          <button
            onClick={() => navigate("/richiedi-demo")}
            className="px-7 py-3.5 bg-[#FF5A00] text-white rounded-lg text-[15px] font-bold hover:bg-[#e04e00] transition-colors inline-flex items-center gap-2"
          >
            Provalo gratis <ArrowRight className="w-4 h-4" />
          </button>
          <div className="mt-4">
            <Link to="/tour" className="text-[13px] text-[#52525B] hover:text-[#0A192F] underline">
              Preferisci vedere prima come funziona? Fai il tour guidato
            </Link>
          </div>
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}

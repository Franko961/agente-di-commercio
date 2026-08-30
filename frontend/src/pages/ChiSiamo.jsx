import { Link } from "react-router-dom";
import PublicHeader from "@/components/PublicHeader";
import PublicFooter from "@/components/PublicFooter";
import PageMeta from "@/components/PageMeta";
import Reveal from "@/components/Reveal";

// Illustrazione originale (non una foto), stesso linguaggio visivo delle
// grafiche di WhySalesFly.jsx (forme piatte nei colori del brand su uno
// sfondo tenue): racconta la storia in tre passaggi — il foglio Excel
// sovraffollato, la scintilla dell'idea, SalesFly ordinato e chiaro.
function FounderIllustration() {
  return (
    <div
      className="relative w-full h-40 md:h-48 rounded-xl flex items-center justify-center overflow-hidden mb-14"
      style={{ background: "#0A192F0D" }}
    >
      <svg viewBox="0 0 300 140" className="w-full max-w-md h-32 md:h-36">
        <g opacity="0.55">
          <rect x="20" y="30" width="70" height="80" rx="4" fill="none" stroke="#0A192F" strokeWidth="2" />
          <line x1="20" y1="46" x2="90" y2="46" stroke="#0A192F" strokeWidth="1.5" opacity="0.4" />
          <line x1="20" y1="62" x2="90" y2="62" stroke="#0A192F" strokeWidth="1.5" opacity="0.4" />
          <line x1="20" y1="78" x2="90" y2="78" stroke="#0A192F" strokeWidth="1.5" opacity="0.4" />
          <line x1="20" y1="94" x2="90" y2="94" stroke="#0A192F" strokeWidth="1.5" opacity="0.4" />
          <line x1="37.5" y1="30" x2="37.5" y2="110" stroke="#0A192F" strokeWidth="1.5" opacity="0.4" />
          <line x1="55" y1="30" x2="55" y2="110" stroke="#0A192F" strokeWidth="1.5" opacity="0.4" />
          <line x1="72.5" y1="30" x2="72.5" y2="110" stroke="#0A192F" strokeWidth="1.5" opacity="0.4" />
        </g>
        <path d="M150 26 l4 9 9 4 -9 4 -4 9 -4 -9 -9 -4 9 -4 z" fill="#B23E00" />
        <path d="M95,70 Q125,70 150,58" fill="none" stroke="#B23E00" strokeWidth="3" strokeDasharray="6 5" strokeLinecap="round" />
        <path d="M150,58 Q175,48 205,55" fill="none" stroke="#B23E00" strokeWidth="3" strokeDasharray="6 5" strokeLinecap="round" />
        <rect x="205" y="35" width="75" height="75" rx="8" fill="#0A192F" />
        <rect x="217" y="50" width="51" height="6" rx="3" fill="#B23E00" />
        <rect x="217" y="64" width="35" height="5" rx="2.5" fill="white" opacity="0.7" />
        <rect x="217" y="75" width="42" height="5" rx="2.5" fill="white" opacity="0.7" />
        <path d="M217,92 l8,8 16,-16" fill="none" stroke="#059669" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

export default function ChiSiamo() {
  return (
    <div className="min-h-screen bg-[#F9F9F8] flex flex-col">
      <PageMeta path="/chi-siamo" />
      <PublicHeader />

      <main className="flex-1 px-6 py-16 max-w-2xl mx-auto w-full">
        <Reveal className="text-center mb-14">
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#B23E00] mb-4">
            Chi siamo
          </div>
          <h1 className="font-cabinet font-black text-4xl md:text-5xl tracking-tight mb-5">
            Nato sul campo, non a tavolino
          </h1>
          <p className="text-[16px] md:text-[18px] text-[#52525B]">
            SalesFly non è il progetto di un team di prodotto che ha studiato il mercato degli
            agenti di commercio da fuori. È nato da chi quel mercato lo vive da vent'anni.
          </p>
        </Reveal>

        <Reveal delay={100}>
          <FounderIllustration />
        </Reveal>

        <Reveal as="article" delay={150}>
          <h2 className="font-cabinet font-black text-2xl mt-10 mb-4">Vent'anni sul campo</h2>
          <p className="text-[15px] leading-relaxed text-[#3F3F46] mb-4">
            Mi chiamo Franco Bruni e lavoro nella vendita da vent'anni, come agente di commercio.
            SalesFly nasce dalla mia stessa attività quotidiana, non da un'idea astratta di come
            "dovrebbe" lavorare un agente plurimandatario.
          </p>

          <h2 className="font-cabinet font-black text-2xl mt-10 mb-4">Il momento in cui è nata l'idea</h2>
          <p className="text-[15px] leading-relaxed text-[#3F3F46] mb-4">
            L'idea è nata sul campo, alla fine di un trimestre di lavoro, davanti all'ennesimo
            foglio Excel sovraffollato di schede clienti, provvigioni e scadenze. L'esigenza era
            semplice da dire e complicata da risolvere: gestire in modo pulito l'attività per più
            ditte mandanti contemporaneamente. Mi sono fatto tre domande, sempre le stesse:
          </p>
          <ul className="list-disc pl-5 space-y-2 my-4 text-[15px] text-[#3F3F46]">
            <li>
              Come faccio a sapere in tempo reale quale mandante mi sta rendendo di più e dove sto
              perdendo tempo?
            </li>
            <li>
              Perché devo adattare la mia operatività quotidiana a CRM generici e complessi,
              pensati per multinazionali con un unico catalogo?
            </li>
            <li>
              Come posso tracciare provvigioni, scaglioni, distinte e visite ai clienti sul
              territorio senza impazzire tra file diversi e calcoli manuali?
            </li>
          </ul>

          <h2 className="font-cabinet font-black text-2xl mt-10 mb-4">
            Perché i CRM esistenti non bastano
          </h2>
          <p className="text-[15px] leading-relaxed text-[#3F3F46] mb-4">
            I CRM tradizionali sono strutturati per aziende monomandatarie o per team di vendita
            strutturati, con dinamiche del tutto diverse dalle nostre. Non gestiscono in modo
            nativo la complessità di un agente plurimandatario o di un'agenzia di rappresentanza,
            che deve giostrare cataloghi separati, politiche provvigionali differenti, calcoli su
            minimali e massimali, e una rendicontazione chiara — mandante per mandante, non su un
            unico totale mescolato.
          </p>

          <h2 className="font-cabinet font-black text-2xl mt-10 mb-4">Perché SalesFly</h2>
          <p className="text-[15px] leading-relaxed text-[#3F3F46] mb-4">
            L'alternativa era continuare a ricamare formule su Excel, o pagare abbonamenti costosi
            per software pensati per tutt'altro tipo di azienda. Da questa frustrazione operativa
            è nata SalesFly: un CRM essenziale, veloce e progettato su misura per le esigenze
            reali di chi vende su più mandati. Ho iniziato a costruirlo nel dicembre 2024, e resta
            uno strumento pensato da un agente per altri agenti — non un prodotto generico
            adattato in un secondo momento al nostro lavoro.
          </p>
        </Reveal>

        <Reveal delay={200} className="text-center mt-14">
          <Link
            to="/richiedi-demo"
            className="px-7 py-3.5 bg-[#B23E00] text-white rounded-lg text-[15px] font-bold hover:bg-[#e04e00] transition-colors inline-flex items-center gap-2"
          >
            Prova SalesFly gratis
          </Link>
        </Reveal>
      </main>

      <PublicFooter />
    </div>
  );
}

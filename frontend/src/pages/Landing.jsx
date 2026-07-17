import { Link, useNavigate } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import {
  Users, KanbanSquare, CalendarDays, Map, FileText, Coins,
  Building2, Package, Sparkles, Zap, Check, ArrowRight, ShieldCheck,
} from "lucide-react";

const FEATURES = [
  { icon: Users, title: "Clienti & anagrafiche", desc: "Tutti i tuoi clienti, contatti e storico visite in un unico posto, sempre a portata di mano." },
  { icon: KanbanSquare, title: "Pipeline lead a Kanban", desc: "Traccia ogni trattativa dalla prima chiamata alla firma, senza perdere occasioni per strada." },
  { icon: CalendarDays, title: "Agenda integrata", desc: "Appuntamenti, promemoria e giri visita organizzati automaticamente per zona e priorità." },
  { icon: Map, title: "Mappa clienti geolocalizzata", desc: "Vedi a colpo d'occhio dove sono i tuoi clienti e ottimizza i giri di visita sul territorio." },
  { icon: FileText, title: "Offerte e preventivi", desc: "Crea e invia preventivi professionali in pochi click, con listini sempre aggiornati." },
  { icon: Coins, title: "Provvigioni automatiche", desc: "Calcolo automatico delle provvigioni per mandante, con scala premi e soglie di bonus." },
  { icon: Building2, title: "Multi-mandante", desc: "Gestisci più mandanti e listini contemporaneamente, ognuno con le proprie regole di commissione." },
  { icon: Sparkles, title: "Assistente AI", desc: "Aggiungi clienti, appuntamenti e note parlando o scrivendo: l'AI aggiorna il CRM al posto tuo." },
];

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[#F9F9F8]">
      <Helmet>
        <title>SALESFLY — Il CRM per Agenti di Commercio Plurimandatari</title>
        <meta
          name="description"
          content="SALESFLY è il gestionale pensato per agenti di commercio plurimandatari: clienti, agenda, provvigioni, offerte e assistente AI in un'unica piattaforma. Prova gratis 14 giorni."
        />
        <link rel="canonical" href="https://salesfly.it/" />
        <meta property="og:type" content="website" />
        <meta property="og:title" content="SALESFLY — Il CRM per Agenti di Commercio Plurimandatari" />
        <meta
          property="og:description"
          content="Clienti, agenda, provvigioni, offerte e assistente AI in un'unica piattaforma pensata per chi vive di visite e provvigioni."
        />
        <meta property="og:url" content="https://salesfly.it/" />
        <meta property="og:locale" content="it_IT" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="SALESFLY — Il CRM per Agenti di Commercio Plurimandatari" />
        <meta
          name="twitter:description"
          content="Clienti, agenda, provvigioni, offerte e assistente AI in un'unica piattaforma pensata per chi vive di visite e provvigioni."
        />
        <script type="application/ld+json">
          {JSON.stringify({
            "@context": "https://schema.org",
            "@type": "SoftwareApplication",
            name: "SALESFLY",
            applicationCategory: "BusinessApplication",
            operatingSystem: "Web",
            description:
              "Gestionale CRM per agenti di commercio plurimandatari: clienti, agenda, provvigioni, offerte e assistente AI.",
            offers: [
              { "@type": "Offer", name: "Base", price: "6.00", priceCurrency: "EUR" },
              { "@type": "Offer", name: "Pro", price: "11.00", priceCurrency: "EUR" },
            ],
            url: "https://salesfly.it/",
          })}
        </script>
      </Helmet>

      {/* Header */}
      <header className="border-b border-[#E4E4E1] bg-white px-6 py-4 flex items-center justify-between sticky top-0 z-30">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-9 h-9 flex items-center justify-center shrink-0">
            <img src="/logo-mark.png" alt="SALESFLY" className="w-full h-full object-contain" />
          </div>
          <span className="font-cabinet font-black text-lg">SALESFLY.</span>
        </Link>
        <nav className="hidden md:flex items-center gap-6 text-[13px] text-[#52525B]">
          <a href="#funzionalita" className="hover:text-[#0A192F]">Funzionalità</a>
          <Link to="/prezzi" className="hover:text-[#0A192F]">Prezzi</Link>
        </nav>
        <div className="flex items-center gap-3">
          <button onClick={() => navigate("/login")} className="text-[13px] text-[#52525B] hover:text-[#0A192F]">
            Accedi
          </button>
          <button
            onClick={() => navigate("/richiedi-demo")}
            className="px-4 py-2 bg-[#0A192F] text-white rounded-md text-[13px] font-medium hover:bg-[#172A45] transition-colors"
          >
            Inizia gratis
          </button>
        </div>
      </header>

      {/* Hero */}
      <main>
        <section className="px-6 pt-20 pb-16 max-w-5xl mx-auto text-center">
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00] mb-4">
            Il CRM per agenti plurimandatari
          </div>
          <h1 className="font-cabinet font-black text-4xl md:text-6xl tracking-tight mb-6 max-w-3xl mx-auto">
            Gestisci clienti, agenda e provvigioni. Tutto in un posto solo.
          </h1>
          <p className="text-[16px] md:text-[18px] text-[#52525B] max-w-2xl mx-auto mb-10">
            SALESFLY è il gestionale pensato per chi vive di visite, mandanti e provvigioni.
            Clienti, pipeline lead, agenda, offerte e calcolo provvigioni automatico, con
            un assistente AI che aggiorna il CRM per te.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <button
              onClick={() => navigate("/richiedi-demo")}
              className="w-full sm:w-auto px-6 py-3.5 bg-[#FF5A00] text-white rounded-lg text-[15px] font-bold hover:bg-[#e04e00] transition-colors flex items-center justify-center gap-2"
            >
              Prova gratis 14 giorni <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => navigate("/prezzi")}
              className="w-full sm:w-auto px-6 py-3.5 border-2 border-[#0A192F] text-[#0A192F] rounded-lg text-[15px] font-bold hover:bg-[#0A192F] hover:text-white transition-colors"
            >
              Vedi i prezzi
            </button>
          </div>
          <div className="font-mono text-[11px] uppercase tracking-widest text-[#A1A1AA] mt-5">
            Nessuna carta di credito richiesta
          </div>
        </section>

        {/* Features */}
        <section id="funzionalita" className="px-6 py-16 bg-white border-y border-[#E4E4E1]">
          <div className="max-w-5xl mx-auto">
            <div className="text-center mb-12">
              <h2 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight mb-3">
                Tutto quello che serve a un agente di commercio
              </h2>
              <p className="text-[15px] text-[#52525B] max-w-xl mx-auto">
                Pensato specificamente per chi lavora con più mandanti, listini e provvigioni diverse.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
              {FEATURES.map(({ icon: Icon, title, desc }) => (
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

        {/* How it works */}
        <section className="px-6 py-16 max-w-4xl mx-auto">
          <h2 className="font-cabinet font-black text-3xl tracking-tight text-center mb-12">
            Operativo in tre passaggi
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              ["01", "Crea i tuoi mandanti", "Inserisci mandanti, listini e regole di provvigione: bastano due minuti."],
              ["02", "Importa i tuoi clienti", "Aggiungi clienti e lead manualmente o parlando con l'assistente AI."],
              ["03", "Vendi e monitora", "Registra offerte e vendite: provvigioni e bonus si calcolano da soli."],
            ].map(([n, t, d]) => (
              <div key={n}>
                <div className="font-cabinet font-black text-3xl text-[#FF5A00] mb-3">{n}</div>
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
              Pronto a semplificarti il lavoro?
            </h2>
            <p className="text-white/60 text-[15px] mb-8 max-w-xl mx-auto">
              Prova SALESFLY gratis per 14 giorni. Nessuna carta di credito, nessun vincolo.
            </p>
            <button
              onClick={() => navigate("/richiedi-demo")}
              className="px-7 py-3.5 bg-[#FF5A00] text-white rounded-lg text-[15px] font-bold hover:bg-[#e04e00] transition-colors inline-flex items-center gap-2"
            >
              Inizia gratis <ArrowRight className="w-4 h-4" />
            </button>
            <div className="flex items-center justify-center gap-2 mt-6 text-white/40 text-[12px] font-mono uppercase tracking-widest">
              <ShieldCheck className="w-4 h-4" /> Dati protetti · Nessuna carta richiesta
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-[#E4E4E1] py-10 px-6">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 flex items-center justify-center shrink-0">
              <img src="/logo-mark.png" alt="SALESFLY" className="w-full h-full object-contain" />
            </div>
            <span className="font-cabinet font-black text-[14px]">SALESFLY.</span>
          </div>
          <nav className="flex items-center gap-6 text-[12px] text-[#52525B]">
            <Link to="/prezzi" className="hover:text-[#0A192F]">Prezzi</Link>
            <Link to="/login" className="hover:text-[#0A192F]">Accedi</Link>
          </nav>
          <div className="text-[12px] text-[#A1A1AA]">© 2026 SALESFLY. · Gestionale per agenti di commercio</div>
        </div>
      </footer>
    </div>
  );
}

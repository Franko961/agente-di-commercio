import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Users, KanbanSquare, CalendarDays, Map, FileText, Coins,
  Building2, Package, Sparkles, Zap, Check, ArrowRight, ShieldCheck,
  Calendar, PhoneCall, AlertTriangle, Banknote, Navigation, Target,
  LayoutDashboard, Menu, X, Facebook,
} from "lucide-react";

const LANDING_NAV_LINKS = [
  { to: "/prezzi", label: "Prezzi" },
  { to: "/blog", label: "Blog" },
  { to: "/tour", label: "Tour guidato" },
  { to: "/perche-salesfly", label: "Perché SalesFly" },
  { to: "/contatti", label: "Contatti" },
];
import usePlans from "../hooks/usePlans";
import { useCookieConsent } from "../contexts/CookieConsentContext";
import PageMeta from "../components/PageMeta";

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

// Ricostruzione stilizzata della schermata Dashboard (non uno screenshot
// reale): stessi colori/layout dell'app (vedi Dashboard.jsx) con dati di
// esempio, per non dipendere da un file immagine esterno né mostrare dati
// veri/demo che potrebbero cambiare o svuotarsi (vedi il reset periodico
// dell'account demo).
function PhoneMockupScreen() {
  const stats = [
    { icon: Calendar, value: "7", label: "appuntamenti" },
    { icon: PhoneCall, value: "3", label: "da richiamare" },
    { icon: AlertTriangle, value: "2", label: "offerte in scadenza" },
    { icon: Banknote, value: "4", label: "pagamenti" },
    { icon: Navigation, value: "38 km", label: "previsti" },
    { icon: Target, value: "€180", label: "obiettivo giorno" },
  ];
  return (
    <div className="h-full w-full bg-[#F9F9F8] overflow-hidden text-[#0A0A0A] flex flex-col">
      <div className="px-3.5 pt-7 pb-3">
        <div className="font-mono text-[6px] uppercase tracking-[0.2em] text-[#FF5A00] mb-1">
          Cruscotto · Lunedì 27 Luglio
        </div>
        <div className="font-cabinet font-black text-[15px] tracking-tight leading-none">Buongiorno, agente.</div>
      </div>

      <div className="mx-3 bg-white border border-[#E4E4E1] rounded-md overflow-hidden shrink-0">
        <div className="px-2.5 pt-2 font-mono text-[6px] uppercase tracking-[0.15em] text-[#FF5A00]">Oggi</div>
        <div className="grid grid-cols-3 gap-y-1.5 px-2 py-2">
          {stats.map(({ icon: Icon, value, label }) => (
            <div key={label} className="flex items-center gap-1">
              <div className="w-4 h-4 rounded bg-[#F3F3F1] flex items-center justify-center shrink-0">
                <Icon className="w-2 h-2 text-[#0A192F]" strokeWidth={2} />
              </div>
              <div className="min-w-0 leading-none">
                <div className="font-cabinet font-black text-[8px] leading-none">{value}</div>
                <div className="text-[4.5px] text-[#52525B] truncate">{label}</div>
              </div>
            </div>
          ))}
        </div>
        <div className="mx-2 mb-2 flex items-start gap-1 bg-[#FFF7ED] border border-[#FED7AA] rounded px-1.5 py-1.5">
          <Sparkles className="w-2 h-2 text-[#FF5A00] shrink-0 mt-0.5" />
          <div className="text-[5px] text-[#0A0A0A] leading-snug">
            <div className="font-mono text-[4px] uppercase tracking-widest text-[#FF5A00] mb-0.5">Suggerimento AI</div>
            Visita prima Rossi Spa: l'offerta scade venerdì.
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-1.5 px-3 mt-2 shrink-0">
        {[
          { label: "Fatturato vinto", value: "€10.126" },
          { label: "Provvigioni", value: "€3.313" },
        ].map(({ label, value }) => (
          <div key={label} className="bg-white border border-[#E4E4E1] rounded-md px-2 py-1.5">
            <div className="font-mono text-[4px] uppercase tracking-widest text-[#A1A1AA]">{label}</div>
            <div className="font-cabinet font-black text-[9px] mt-0.5">{value}</div>
          </div>
        ))}
      </div>

      <div className="mx-3 mt-2 bg-white border border-[#E4E4E1] rounded-md px-2.5 py-2 shrink-0">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-1">
            <Target className="w-2 h-2 text-[#FF5A00]" />
            <span className="font-mono text-[4.5px] uppercase tracking-widest text-[#52525B]">Fatturato del mese</span>
          </div>
          <span className="font-mono text-[6px] font-semibold">100%</span>
        </div>
        <div className="h-1 bg-[#F3F3F1] rounded-full overflow-hidden">
          <div className="h-full bg-[#FF5A00] rounded-full" style={{ width: "100%" }} />
        </div>
      </div>

      <div className="mx-3 mt-2 bg-white border border-[#E4E4E1] rounded-md px-2.5 py-2 shrink-0">
        <div className="font-mono text-[4.5px] uppercase tracking-widest text-[#52525B] mb-1.5">Andamento mensile</div>
        <div className="flex items-end gap-1 h-8">
          {[35, 55, 40, 70, 50, 90, 65].map((h, i) => (
            <div key={i} className="flex-1 rounded-t-sm bg-[#0A192F]" style={{ height: `${h}%`, opacity: i === 5 ? 1 : 0.35 }} />
          ))}
        </div>
      </div>

      {/* Riempie lo spazio restante, così la barra di navigazione resta
          sempre in fondo allo schermo indipendentemente da quanto contenuto
          c'è sopra. */}
      <div className="flex-1" />

      <div className="shrink-0 border-t border-[#E4E4E1] bg-white flex items-stretch justify-around px-1 py-1.5">
        {[
          { icon: LayoutDashboard, label: "Home", active: true },
          { icon: Users, label: "Clienti" },
          { icon: CalendarDays, label: "Agenda" },
          { icon: Map, label: "Mappa" },
          { icon: FileText, label: "Offerte" },
        ].map(({ icon: Icon, label, active }) => (
          <div key={label} className="flex flex-col items-center gap-0.5 px-1">
            <Icon className="w-2.5 h-2.5" strokeWidth={active ? 2.5 : 1.75} color={active ? "#FF5A00" : "#A1A1AA"} />
            <span className={`text-[3.5px] font-mono uppercase tracking-widest ${active ? "text-[#FF5A00]" : "text-[#A1A1AA]"}`}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function PhoneMockup() {
  return (
    <div className="relative mx-auto md:mx-0 w-[230px] sm:w-[260px] select-none" aria-hidden="true">
      <div className="relative bg-[#0A192F] rounded-[2.2rem] p-2.5 shadow-2xl ring-1 ring-black/10">
        <div className="absolute top-2.5 left-1/2 -translate-x-1/2 w-16 h-4 bg-[#0A192F] rounded-b-lg z-10" />
        <div className="relative bg-white rounded-[1.7rem] overflow-hidden aspect-[9/19.5]">
          <PhoneMockupScreen />
        </div>
      </div>
      {/* Ombra/riflesso decorativo dietro il telefono */}
      <div className="absolute -z-10 -inset-6 bg-gradient-to-br from-[#FF5A00]/10 to-[#0A192F]/10 rounded-[3rem] blur-2xl" />
    </div>
  );
}

export default function Landing() {
  const navigate = useNavigate();
  const { openPreferences } = useCookieConsent();
  const { plansById, trialDays } = usePlans();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div className="min-h-screen bg-[#F9F9F8]">
      <PageMeta path="/">
        <script type="application/ld+json">
          {JSON.stringify({
            "@context": "https://schema.org",
            "@type": "SoftwareApplication",
            name: "SALESFLY",
            applicationCategory: "BusinessApplication",
            operatingSystem: "Web",
            description:
              "CRM per agenti di commercio plurimandatari con un assistente AI che aggiorna clienti, agenda, provvigioni e offerte al posto dell'utente, non solo con consigli.",
            offers: Object.values(plansById).map(p => ({
              "@type": "Offer", name: p.name, price: p.price_eur?.toFixed(2), priceCurrency: "EUR",
            })),
            url: "https://salesfly.it/",
          })}
        </script>
      </PageMeta>

      {/* Header */}
      <header
        className={`sticky top-0 z-30 transition-all duration-200 border-b ${
          scrolled
            ? "bg-[rgba(10,25,47,0.92)] backdrop-blur-md border-transparent shadow-[0_8px_30px_rgba(0,0,0,0.08)]"
            : "bg-white border-[#E4E4E1]"
        }`}
      >
        <div className="px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2" onClick={() => setMobileNavOpen(false)}>
            <div className={`w-11 h-11 flex items-center justify-center shrink-0 ${scrolled ? "animate-logo-pop" : ""}`}>
              <img src="/logo-mark.png" alt="SALESFLY" className="w-full h-full object-contain" />
            </div>
            <span className={`font-cabinet font-black text-xl transition-colors duration-200 ${scrolled ? "text-white" : "text-[#0A0A0A]"}`}>
              SALESFLY.
            </span>
          </Link>
          <nav
            className={`hidden md:flex items-center gap-6 text-[14px] font-medium transition-colors duration-200 ${
              scrolled ? "text-white/80" : "text-[#3F3F46]"
            }`}
          >
            {LANDING_NAV_LINKS.map((l) => (
              <Link key={l.to} to={l.to} className={`transition-colors ${scrolled ? "hover:text-white" : "hover:text-[#0A192F]"}`}>{l.label}</Link>
            ))}
          </nav>
          <div className="flex items-center gap-1.5 sm:gap-3">
            <button
              onClick={() => navigate("/login")}
              className={`hidden sm:inline-block text-[13px] transition-colors duration-200 ${
                scrolled ? "text-white/70 hover:text-white" : "text-[#52525B] hover:text-[#0A192F]"
              }`}
            >
              Accedi
            </button>
            <button
              onClick={() => navigate("/richiedi-demo")}
              className={`px-3 py-1.5 sm:px-4 sm:py-2 rounded-md text-[12px] sm:text-[13px] font-medium whitespace-nowrap transition-colors duration-200 ${
                scrolled ? "bg-white text-[#0A192F] hover:bg-white/90" : "bg-[#0A192F] text-white hover:bg-[#172A45]"
              }`}
            >
              Inizia gratis
            </button>
            <button
              onClick={() => setMobileNavOpen((v) => !v)}
              data-testid="mobile-nav-toggle"
              aria-label="Menu"
              className={`md:hidden p-1.5 shrink-0 transition-colors duration-200 ${scrolled ? "text-white" : "text-[#0A192F]"}`}
            >
              {mobileNavOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
        {mobileNavOpen && (
          <nav className="md:hidden border-t border-[#E4E4E1] px-6 py-2 flex flex-col bg-white">
            {LANDING_NAV_LINKS.map((l) => (
              <Link
                key={l.to}
                to={l.to}
                onClick={() => setMobileNavOpen(false)}
                className="py-3 text-[14px] font-medium text-[#3F3F46] border-b border-[#F3F3F1] last:border-b-0"
              >
                {l.label}
              </Link>
            ))}
            <Link
              to="/login"
              onClick={() => setMobileNavOpen(false)}
              className="py-3 text-[14px] font-medium text-[#3F3F46]"
            >
              Accedi
            </Link>
          </nav>
        )}
      </header>

      {/* Hero */}
      <main>
        <section className="relative overflow-hidden px-6 pt-16 pb-16">
          <img
            src="/hero-skyline.png"
            alt=""
            aria-hidden="true"
            className="pointer-events-none select-none absolute inset-x-0 top-0 w-full h-[480px] object-cover object-top"
            style={{
              maskImage: "linear-gradient(to bottom, black 0%, black 78%, transparent 100%)",
              WebkitMaskImage: "linear-gradient(to bottom, black 0%, black 78%, transparent 100%)",
            }}
          />
          <div className="relative z-10 max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-[340px_1fr] gap-10 md:gap-6 items-center">
            <div className="order-1">
              <PhoneMockup />
            </div>
            <div className="order-2 text-center">
              <div className="inline-block font-mono text-[12px] font-bold uppercase tracking-[0.15em] text-[#FF5A00] bg-[#FF5A00]/10 border border-[#FF5A00]/20 rounded-full px-4 py-1.5 mb-5">
                Il CRM per agenti plurimandatari
              </div>
              <h1 className="font-cabinet font-black text-4xl md:text-5xl tracking-tight mb-6">
                Il CRM che aggiorna clienti, appuntamenti e provvigioni al posto tuo.
              </h1>
              <p className="text-[16px] md:text-[18px] text-[#52525B] mb-6">
                Parla con SALESFLY: l'AI aggiorna clienti, appuntamenti, ordini e provvigioni
                mentre tu sei dai clienti.
              </p>
              <div className="flex flex-wrap items-center justify-center gap-2.5 mb-8">
                {[
                  { icon: Sparkles, label: "Assistente AI" },
                  { icon: Coins, label: "Provvigioni automatiche" },
                  { icon: Navigation, label: "Giro visite intelligente" },
                  { icon: FileText, label: "Ordini e clienti in un unico posto" },
                ].map(({ icon: Icon, label }) => (
                  <div
                    key={label}
                    className="flex items-center gap-1.5 bg-white border border-[#E4E4E1] rounded-full px-3.5 py-1.5 text-[13px] font-medium text-[#3F3F46]"
                  >
                    <Icon className="w-3.5 h-3.5 text-[#FF5A00]" />
                    {label}
                  </div>
                ))}
              </div>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
                <button
                  onClick={() => navigate("/richiedi-demo")}
                  className="w-full sm:w-auto px-6 py-3.5 bg-[#FF5A00] text-white rounded-lg text-[15px] font-bold hover:bg-[#e04e00] transition-colors flex items-center justify-center gap-2"
                >
                  Prova gratis {trialDays} giorni <ArrowRight className="w-4 h-4" />
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
            </div>
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
              Prova SALESFLY gratis per {trialDays} giorni. Nessuna carta di credito, nessun vincolo.
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
            <Link to="/blog" className="hover:text-[#0A192F]">Blog</Link>
            <Link to="/privacy" className="hover:text-[#0A192F]">Privacy</Link>
            <Link to="/termini" className="hover:text-[#0A192F]">Termini</Link>
            <button onClick={openPreferences} className="hover:text-[#0A192F]">Cookie</button>
            <Link to="/login" className="hover:text-[#0A192F]">Accedi</Link>
          </nav>
          <div className="flex items-center gap-3 text-[12px] text-[#A1A1AA]">
            <span>© 2026 SALESFLY. · Gestionale per agenti di commercio</span>
            <a
              href="https://www.facebook.com/salesflycrm"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="SalesFly su Facebook"
              className="w-8 h-8 flex items-center justify-center rounded-full bg-[#0A192F] text-white hover:bg-[#FF5A00] transition-colors shrink-0"
            >
              <Facebook className="w-4 h-4" />
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}

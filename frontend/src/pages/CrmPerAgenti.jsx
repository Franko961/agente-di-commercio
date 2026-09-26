import { Link, useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import PublicHeader from "@/components/PublicHeader";
import PublicFooter from "@/components/PublicFooter";
import PageMeta from "@/components/PageMeta";
import usePlans from "@/hooks/usePlans";
import { trackEvent } from "@/lib/analytics";

// Pagina "pilastro" del cluster CRM: raccoglie in un solo posto le funzioni
// che contano per un agente plurimandatario e rimanda ad ogni articolo di
// approfondimento già pubblicato. Ogni affermazione sul prodotto è ancorata
// a una funzione che esiste davvero (vedi la sezione "Cosa SalesFly non fa"
// per i limiti dichiarati apertamente), coerentemente col resto del blog.
const SECTIONS = [
  {
    title: "Più mandanti nello stesso posto, ognuno con le sue regole",
    text: "Il primo requisito di un CRM per agenti di commercio non è un elenco di funzioni: è ragionare per mandante. Un plurimandatario ha listini, aliquote e clausole diverse per ogni casa mandante, e un CRM generico costringe a simularlo con campi personalizzati e filtri. In SalesFly il mandante è un elemento del CRM: clienti, offerte, ordini e provvigioni si leggono per mandante.",
    links: [
      { to: "/blog/gestire-piu-mandanti-crm", label: "Gestire più mandanti in un solo CRM" },
      { to: "/blog/crm-italiano-agenti-di-commercio", label: "CRM italiano per agenti: cosa significa davvero" },
    ],
  },
  {
    title: "Provvigioni calcolate, non ricostruite a fine trimestre",
    text: "La provvigione dipende dalla percentuale, dalla base di calcolo e dall'eventuale scala premi, e si complica con resi e storni. Ogni mandante ha la propria aliquota e la propria scala premi, le provvigioni si distinguono tra maturate e incassate, e c'è una stima del netto dopo ritenuta d'acconto ed ENASARCO. Per ogni mandante si può generare un riepilogo in PDF con il calcolo.",
    links: [
      { to: "/blog/come-calcolare-provvigioni-agente-di-commercio", label: "Come si calcolano le provvigioni" },
      { to: "/blog/provvigioni-scalari-a-target", label: "Provvigioni scalari a target" },
      { to: "/calcolatori", label: "Calcolatori: FIRR, ENASARCO, forfettario, ATECO" },
    ],
  },
  {
    title: "Agenda, mappa clienti e giro visite ottimizzato",
    text: "Per chi vive in auto, l'agenda è il lavoro. SalesFly mostra i clienti su mappa, organizza gli appuntamenti e calcola l'ordine di visita che riduce i chilometri percorsi tra le tappe, su distanze e tempi reali di strada. Meno chilometri a parità di visite significa meno carburante, che per un agente è un costo diretto.",
    links: [
      { to: "/blog/pianificare-giro-visite-agente-di-commercio", label: "Pianificare il giro visite" },
      { to: "/blog/software-calcolo-percorso-ottimizzato-agenti", label: "Come funziona il percorso ottimizzato" },
      { to: "/blog/costo-carburante-agente-di-commercio", label: "Il costo del carburante per un agente" },
    ],
  },
  {
    title: "Dal telefono, dal cliente",
    text: "Un CRM per agenti si usa in piedi, tra una visita e l'altra. SalesFly funziona dal browser del telefono e si può aggiungere alla schermata home come un'app; le note si possono dettare a voce, con trascrizione automatica, invece di scriverle sulla tastiera.",
    links: [
      { to: "/blog/crm-mobile-agenti-di-commercio", label: "CRM mobile per agenti di commercio" },
      { to: "/blog/usare-crm-da-telefono-dai-clienti", label: "Usare il CRM da telefono davanti al cliente" },
    ],
  },
  {
    title: "Un assistente AI che aggiorna il CRM",
    text: "La differenza tra un CRM con l'AI e un CRM che consiglia è che il secondo ti dice cosa fare, il primo lo fa. L'assistente di SalesFly, scrivendo o parlando, può aggiungere clienti, fissare appuntamenti e registrare note al posto tuo, e ti chiede conferma sulle azioni importanti.",
    links: [
      { to: "/assistente-ai", label: "L'assistente AI di SalesFly" },
      { to: "/blog/crm-intelligenza-artificiale-per-venditori", label: "CRM con intelligenza artificiale per venditori" },
      { to: "/blog/come-ai-e-crm-automatizzano-attivita-vendita", label: "Come AI e CRM automatizzano le attività di vendita" },
    ],
  },
  {
    title: "Offerte, ordini, documenti e catalogo",
    text: "Offerte e preventivi, ordini, archivio documenti e pipeline dei lead in un unico posto, con lo storico di ogni cliente a portata di clic. Il catalogo digitale sostituisce il cartaceo da portare in visita.",
    links: [
      { to: "/blog/catalogo-digitale-agenti-di-commercio", label: "Catalogo digitale al posto del cartaceo" },
      { to: "/blog/whatsapp-crm-agente-di-commercio", label: "WhatsApp e CRM: cosa serve davvero" },
    ],
  },
  {
    title: "Partire da Excel o da un altro CRM",
    text: "Chi ha già i clienti in un foglio Excel può importarli in blocco; chi arriva da un CRM generico porta con sé l'anagrafica ma non lo storico delle attività, e conviene saperlo prima di cambiare.",
    links: [
      { to: "/blog/passare-da-excel-al-crm-agenti", label: "Passare da Excel al CRM" },
      { to: "/blog/migrare-crm-generico-verticale-agenti", label: "Migrare da un CRM generico a uno per agenti" },
      { to: "/blog/implementare-salesfly-in-due-minuti", label: "Iniziare con SalesFly in due minuti" },
    ],
  },
  {
    title: "Come scegliere: confronti e alternative",
    text: "Prima di scegliere conviene confrontare: le opzioni gratuite hanno limiti reali, e i CRM generici funzionano meglio per chi vende in team che per chi lavora su più mandati.",
    links: [
      { to: "/blog/migliori-crm-per-venditori-italiani", label: "I migliori CRM per venditori italiani" },
      { to: "/blog/crm-gratuito-agenti-di-commercio-limiti", label: "CRM gratuito per agenti: esiste davvero?" },
      { to: "/blog/salesfly-vs-hubspot-agenti-di-commercio", label: "SalesFly e HubSpot a confronto" },
    ],
  },
];

export default function CrmPerAgenti() {
  const navigate = useNavigate();
  const { trialDays } = usePlans();

  return (
    <div className="min-h-screen bg-[#F9F9F8] flex flex-col">
      <PageMeta path="/crm-per-agenti-di-commercio" />

      <PublicHeader />

      <main className="flex-1 px-6 py-16 max-w-3xl mx-auto w-full">
        <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#B23E00] mb-4">Guida</div>
        <h1 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight mb-5">
          CRM per agenti di commercio: cosa deve avere e come scegliere
        </h1>
        <p className="text-[16px] text-[#52525B] leading-relaxed mb-4">
          Un agente plurimandatario ha un lavoro diverso da chi vende in un team: più mandanti con regole diverse, provvigioni da verificare, giornate in auto tra un cliente e l'altro. Un CRM adatto a questo lavoro si riconosce da poche cose. Qui sono raccolte, con gli approfondimenti per ciascuna.
        </p>

        <nav aria-label="Indice" className="bg-white border border-[#E4E4E1] rounded-xl p-5 my-8">
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#6B6B72] mb-3">In questa guida</div>
          <ul className="space-y-1.5 text-[14px]">
            {SECTIONS.map((s, i) => (
              <li key={s.title}>
                <a href={`#sezione-${i}`} className="text-[#0A192F] hover:text-[#B23E00] underline-offset-2 hover:underline">
                  {s.title}
                </a>
              </li>
            ))}
            <li>
              <a href="#limiti" className="text-[#0A192F] hover:text-[#B23E00] underline-offset-2 hover:underline">
                Cosa SalesFly non fa
              </a>
            </li>
          </ul>
        </nav>

        {SECTIONS.map((s, i) => (
          <section key={s.title} id={`sezione-${i}`} className="mb-10 scroll-mt-24">
            <h2 className="font-cabinet font-black text-2xl tracking-tight mb-3">{s.title}</h2>
            <p className="text-[15px] leading-relaxed text-[#3F3F46] mb-4">{s.text}</p>
            <ul className="space-y-1.5">
              {s.links.map((l) => (
                <li key={l.to}>
                  <Link to={l.to} className="inline-flex items-center gap-1.5 text-[14px] text-[#B23E00] font-medium hover:underline">
                    <ArrowRight className="w-3.5 h-3.5 shrink-0" /> {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ))}

        <section id="limiti" className="mb-12 scroll-mt-24">
          <h2 className="font-cabinet font-black text-2xl tracking-tight mb-3">Cosa SalesFly non fa</h2>
          <p className="text-[15px] leading-relaxed text-[#3F3F46] mb-3">
            Per scegliere bene serve sapere anche dove uno strumento si ferma. SalesFly è pensato per l'agente che lavora da solo su più mandati, non per un team commerciale:
          </p>
          <ul className="list-disc pl-5 space-y-1.5 text-[15px] leading-relaxed text-[#3F3F46]">
            <li>Non ha una pipeline condivisa tra più venditori.</li>
            <li>Non emette fatture elettroniche: calcola provvigioni e netto stimato, la fatturazione resta al proprio gestionale o al commercialista.</li>
            <li>Non si integra con WhatsApp tramite API: apre la conversazione con un link, i messaggi restano dentro WhatsApp.</li>
          </ul>
        </section>

        <div className="bg-[#0A192F] text-white rounded-2xl p-8 text-center">
          <div className="font-cabinet font-black text-2xl mb-2">Provalo sul tuo lavoro reale</div>
          <p className="text-white/70 text-[14px] mb-6">
            Crea l'account in meno di un minuto e usalo gratis per {trialDays} giorni, senza carta di credito.
          </p>
          <button
            onClick={() => {
              trackEvent("cta_click", { location: "crm_pillar" });
              navigate("/richiedi-demo");
            }}
            className="px-7 py-3.5 bg-[#B23E00] text-white rounded-lg text-[15px] font-bold hover:bg-[#e04e00] transition-colors inline-flex items-center gap-2"
          >
            Inizia la prova gratuita <ArrowRight className="w-4 h-4" />
          </button>
          <div className="mt-4 flex items-center justify-center gap-5 text-[13px] text-white/70 flex-wrap">
            <Link to="/prezzi" className="underline hover:text-white">Vedi i prezzi</Link>
            <Link to="/tour" className="underline hover:text-white">Fai il tour guidato</Link>
            <Link to="/perche-salesfly" className="underline hover:text-white">Perché SalesFly</Link>
          </div>
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}

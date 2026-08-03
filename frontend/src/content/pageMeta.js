// Metadati statici delle pagine pubbliche (non del blog, che ha la propria
// fonte in ./blog/articles) — usati sia dal componente React PageMeta (per
// i client che eseguono JS) sia da scripts/prerender.js (per i crawler che
// non lo fanno, es. Facebook/LinkedIn/Twitter): un'unica fonte, così le due
// versioni non possono disallinearsi nel tempo.
//
// CommonJS apposta (non "export const"): deve essere leggibile sia da
// webpack/Babel (import ... from "...") sia direttamente da Node in
// scripts/prerender.js (require(...)), senza bisogno di transpilazione.
//
// Le descrizioni evitano deliberatamente numeri che vivono altrove (es. i
// prezzi dei piani, che arrivano da un'API) per non doverli tenere
// sincronizzati a mano qui: quei dettagli restano nella pagina reale,
// questi testi servono solo per title/description/anteprime social.
const DEFAULT_OG_IMAGE = "https://salesfly.it/hero-skyline.png";

// changefreq/priority: usati SOLO da scripts/prerender.js per generare
// build/sitemap.xml — tenuti qui, non in un file a parte, per lo stesso
// motivo di title/description sopra: prima sitemap.xml era scritta a mano
// in public/, con il rischio concreto (e già successo) di dimenticare di
// aggiornarla quando si aggiunge o si toglie una pagina.
const PAGES = {
  "/": {
    title: "SALESFLY — Il CRM per Agenti di Commercio Plurimandatari",
    description:
      "SALESFLY è il CRM per agenti di commercio plurimandatari con un assistente AI che aggiorna davvero il CRM al posto tuo: clienti, agenda, provvigioni e offerte, non solo consigli. Prova gratis 14 giorni.",
    ogDescription:
      "L'unico CRM con un assistente che il lavoro non lo spiega: lo fa. Clienti, agenda, provvigioni e offerte per chi vive di visite e mandanti.",
    changefreq: "weekly",
    priority: "1.0",
  },
  "/prezzi": {
    title: "Prezzi — SALESFLY, il CRM per Agenti di Commercio",
    description:
      "Piani Base e Pro per il CRM SALESFLY, con giorni di prova gratuita e nessuna carta di credito richiesta.",
    changefreq: "monthly",
    priority: "0.8",
  },
  "/richiedi-demo": {
    title: "Richiedi la Demo — SALESFLY",
    description:
      "Richiedi l'accesso alla demo di SALESFLY, il CRM per Agenti di Commercio. Riceverai subito il link di accesso via email.",
    changefreq: "monthly",
    priority: "0.8",
  },
  "/perche-salesfly": {
    title: "Perché SalesFly — Il CRM per Agenti di Commercio",
    description:
      "L'unico CRM con un assistente che il lavoro non lo spiega: lo fa. Scopri i vantaggi concreti che SalesFly porta nella giornata di un agente di commercio plurimandatario.",
    changefreq: "monthly",
    priority: "0.8",
  },
  "/tour": {
    title: "Tour guidato — SALESFLY",
    description:
      "Scopri in 3 minuti le funzioni principali di SALESFLY: dashboard, clienti, lead, agenda, automazioni, assistente AI e pianificatore giro visite.",
    changefreq: "monthly",
    priority: "0.7",
  },
  "/contatti": {
    title: "Contatti — SALESFLY",
    description:
      "Hai domande su SALESFLY, il CRM per Agenti di Commercio Plurimandatari? Scrivici, ti risponderemo il prima possibile.",
    changefreq: "monthly",
    priority: "0.5",
  },
  "/blog": {
    title: "Blog per Agenti di Commercio — SALESFLY",
    description:
      "Guide pratiche su provvigioni, ENASARCO, contratti di agenzia e tutto ciò che serve a un agente di commercio plurimandatario.",
    changefreq: "weekly",
    priority: "0.7",
  },
  // Pagina di atterraggio dedicata a campagne pubblicitarie sull'assistente
  // AI (non raggiungibile dal menu principale, vedi LandingAI.jsx) —
  // priorità/changefreq più bassi delle pagine di navigazione principale,
  // coerente con il suo ruolo di pagina secondaria.
  "/assistente-ai": {
    title: "Assistente AI per il CRM — SALESFLY",
    description:
      "L'assistente AI di SALESFLY aggiunge clienti, appuntamenti, lead e note nel CRM al posto tuo: non ti dà consigli, esegue. Prova gratis 14 giorni.",
    ogDescription:
      "Altri assistenti AI nei CRM ti dicono cosa fare. Il nostro lo fa al posto tuo: clienti, appuntamenti, lead e note aggiornati mentre sei dal cliente.",
    changefreq: "monthly",
    priority: "0.5",
  },
};

// Stessi valori per ogni articolo blog (a differenza di slug/title/ecc.,
// non c'è nulla da leggere dal singolo articolo: ogni articolo li vuole
// identici, quindi una costante sola invece di un campo per file).
const BLOG_ARTICLE_SITEMAP_DEFAULTS = { changefreq: "monthly", priority: "0.6" };

module.exports = { PAGES, DEFAULT_OG_IMAGE, BLOG_ARTICLE_SITEMAP_DEFAULTS };

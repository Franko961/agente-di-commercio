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

const PAGES = {
  "/": {
    title: "SALESFLY — Il CRM per Agenti di Commercio Plurimandatari",
    description:
      "SALESFLY è il CRM per agenti di commercio plurimandatari con un assistente AI che aggiorna davvero il CRM al posto tuo: clienti, agenda, provvigioni e offerte, non solo consigli. Prova gratis 14 giorni.",
    ogDescription:
      "L'unico CRM con un assistente che il lavoro non lo spiega: lo fa. Clienti, agenda, provvigioni e offerte per chi vive di visite e mandanti.",
  },
  "/richiedi-demo": {
    title: "Richiedi la Demo — SALESFLY",
    description:
      "Richiedi l'accesso alla demo di SALESFLY, il CRM per Agenti di Commercio. Riceverai subito il link di accesso via email.",
  },
  "/prezzi": {
    title: "Prezzi — SALESFLY, il CRM per Agenti di Commercio",
    description:
      "Piani Base e Pro per il CRM SALESFLY, con giorni di prova gratuita e nessuna carta di credito richiesta.",
  },
  "/perche-salesfly": {
    title: "Perché SalesFly — Il CRM per Agenti di Commercio",
    description:
      "L'unico CRM con un assistente che il lavoro non lo spiega: lo fa. Scopri i vantaggi concreti che SalesFly porta nella giornata di un agente di commercio plurimandatario.",
  },
  "/tour": {
    title: "Tour guidato — SALESFLY",
    description:
      "Scopri in 3 minuti le funzioni principali di SALESFLY: dashboard, clienti, lead, agenda, automazioni, assistente AI e pianificatore giro visite.",
  },
  "/contatti": {
    title: "Contatti — SALESFLY",
    description:
      "Hai domande su SALESFLY, il CRM per Agenti di Commercio Plurimandatari? Scrivici, ti risponderemo il prima possibile.",
  },
  "/blog": {
    title: "Blog per Agenti di Commercio — SALESFLY",
    description:
      "Guide pratiche su provvigioni, ENASARCO, contratti di agenzia e tutto ciò che serve a un agente di commercio plurimandatario.",
  },
};

module.exports = { PAGES, DEFAULT_OG_IMAGE };

import { lazy } from "react";

// Registro centrale dei calcolatori interattivi — un'unica fonte usata sia
// dal blocco "calculator" degli articoli blog (BlogPost.jsx, che cerca per
// chiave: es. { type: "calculator", name: "firr" }) sia dalle pagine
// standalone /calcolatori/:slug e dall'hub /calcolatori. Prima esisteva
// solo una copia locale in BlogPost.jsx — niente slug, niente descrizione,
// inutilizzabile per una pagina propria. Le CHIAVI dell'oggetto (firr,
// ritenutaEnasarco, ...) sono quelle già scritte nei blocchi "calculator"
// degli articoli esistenti: vanno lasciate invariate, cambiarle romperebbe
// silenziosamente quei blocchi (nessun errore, il calcolatore sparirebbe
// dall'articolo pubblicato — stesso rischio già documentato in BlogPost.jsx
// per un nome non registrato).
export const CALCULATORS = {
  firr: {
    slug: "firr",
    title: "Calcolatore FIRR",
    description:
      "Calcola l'accantonamento annuo del Fondo Indennità Risoluzione Rapporto per un singolo mandante, con gli scaglioni 2026 (i primi rivisti dal 1989).",
    component: lazy(() => import("@/components/FirrCalculator")),
    articleSlug: "firr-agenti-commercio-calcolo-indennita",
  },
  ritenutaEnasarco: {
    slug: "ritenuta-acconto-enasarco",
    title: "Calcolatore ritenuta d'acconto e contributo ENASARCO",
    description:
      "Calcola ritenuta d'acconto e contributo ENASARCO da esporre in fattura su una provvigione, in base al proprio regime fiscale.",
    component: lazy(() => import("@/components/RitenutaEnasarcoCalculator")),
    articleSlug: "ritenuta-acconto-contributi-enasarco-fattura",
  },
  regimeForfettario: {
    slug: "regime-forfettario",
    title: "Calcolatore regime forfettario",
    description:
      "Stima l'imposta sostitutiva nel regime forfettario per agenti di commercio, con il coefficiente di redditività del 62%.",
    component: lazy(() => import("@/components/RegimeForfettarioCalculator")),
    articleSlug: null,
  },
  scontoProvvigione: {
    slug: "sconto-provvigione",
    title: "Calcolatore sconto e provvigione",
    description:
      "Calcola quanto perdi di provvigione con uno sconto al cliente, e lo sconto massimo che puoi concedere senza scendere sotto una provvigione minima.",
    component: lazy(() => import("@/components/ScontoProvvigioneCalculator")),
    articleSlug: "provvigioni-scalari-a-target",
  },
};

export function getCalculatorBySlug(slug) {
  return Object.values(CALCULATORS).find((c) => c.slug === slug);
}

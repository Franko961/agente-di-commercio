// Registro centrale degli articoli del blog.
// Per aggiungere un nuovo articolo:
//   1. crea un file in ./articles/nome-slug.js che esporta `article`
//   2. importalo e aggiungilo all'array qui sotto
// Non serve toccare App.js: le rotte /blog e /blog/:slug sono generiche.
import { article as calcoloProvvigioni } from "./articles/calcolo-provvigioni-agente-di-commercio";
import { article as aiCrmAutomazione } from "./articles/ai-crm-automatizzano-vendite";
import { article as enasarco } from "./articles/enasarco-cos-e-come-funziona";
import { article as giroVisite } from "./articles/pianificare-giro-visite-agente-di-commercio";
import { article as speseDeducibili } from "./articles/spese-deducibili-agente-di-commercio";
import { article as multiMandante } from "./articles/gestire-piu-mandanti-crm";
import { article as crmMobile } from "./articles/crm-mobile-agenti-di-commercio";
import { article as crmDaTelefono } from "./articles/usare-crm-da-telefono-dai-clienti";
import { article as salesflyVsHubspot } from "./articles/salesfly-vs-hubspot-agenti-di-commercio";
import { article as migliorCrmVenditori } from "./articles/migliori-crm-per-venditori-italiani";
import { article as crmAiVenditori } from "./articles/crm-intelligenza-artificiale-per-venditori";
import { article as aumentareProvvigioni } from "./articles/aumentare-provvigioni-agente-di-commercio";
import { article as daExcelAlCrm } from "./articles/passare-da-excel-al-crm-agenti";
import { article as implementareInDueMinuti } from "./articles/implementare-salesfly-in-due-minuti";
import { article as contrattoDiAgenzia } from "./articles/contratto-di-agenzia-clausole-da-controllare";
import { article as rimborsoTasseStudio } from "./articles/enasarco-rimborso-tasse-studio-universita-2026";
import { article as bonusScolasticoFigli } from "./articles/enasarco-bonus-scolastico-figli-2026";
import { article as minimaliMassimali } from "./articles/enasarco-minimali-massimali-2026";
import { article as inquadramentoAgente } from "./articles/diventare-agente-di-commercio-requisiti-iscrizioni";
import { article as catalogoDigitale } from "./articles/catalogo-digitale-agenti-di-commercio";
import { article as ritenutaAcconto } from "./articles/ritenuta-acconto-contributi-enasarco-fattura";
import { article as firr } from "./articles/firr-agenti-commercio-calcolo-indennita";
import { article as agenteSportivo } from "./articles/differenza-agente-commercio-agente-sportivo";
import { article as deducibilitaAuto } from "./articles/deducibilita-fiscale-auto-agenti-commercio";
import { article as crmItaliano } from "./articles/crm-italiano-agenti-di-commercio";
import { article as percorsoOttimizzato } from "./articles/software-calcolo-percorso-ottimizzato-agenti";

const allArticles = [calcoloProvvigioni, aiCrmAutomazione, enasarco, giroVisite, speseDeducibili, multiMandante, crmMobile, crmDaTelefono, salesflyVsHubspot, migliorCrmVenditori, crmAiVenditori, aumentareProvvigioni, daExcelAlCrm, implementareInDueMinuti, contrattoDiAgenzia, rimborsoTasseStudio, bonusScolasticoFigli, minimaliMassimali, inquadramentoAgente, catalogoDigitale, ritenutaAcconto, firr, agenteSportivo, deducibilitaAuto, crmItaliano, percorsoOttimizzato];

export const articles = [...allArticles].sort(
  (a, b) => new Date(b.publishedAt) - new Date(a.publishedAt)
);

export function getArticleBySlug(slug) {
  return articles.find((a) => a.slug === slug);
}

export function getPublishedArticles() {
  return articles.filter((a) => !a.draft);
}

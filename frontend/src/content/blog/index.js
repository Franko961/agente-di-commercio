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

const allArticles = [calcoloProvvigioni, aiCrmAutomazione, enasarco, giroVisite, speseDeducibili, multiMandante, crmMobile, crmDaTelefono, salesflyVsHubspot, migliorCrmVenditori, crmAiVenditori, aumentareProvvigioni];

export const articles = [...allArticles].sort(
  (a, b) => new Date(b.publishedAt) - new Date(a.publishedAt)
);

export function getArticleBySlug(slug) {
  return articles.find((a) => a.slug === slug);
}

export function getPublishedArticles() {
  return articles.filter((a) => !a.draft);
}

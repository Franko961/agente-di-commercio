// Registro centrale degli articoli del blog.
// Per aggiungere un nuovo articolo:
//   1. crea un file in ./articles/nome-slug.js che esporta `article`
//   2. importalo e aggiungilo all'array qui sotto
// Non serve toccare App.js: le rotte /blog e /blog/:slug sono generiche.
import { article as calcoloProvvigioni } from "./articles/calcolo-provvigioni-agente-di-commercio";
import { article as aiCrmAutomazione } from "./articles/ai-crm-automatizzano-vendite";

const allArticles = [calcoloProvvigioni, aiCrmAutomazione];

export const articles = [...allArticles].sort(
  (a, b) => new Date(b.publishedAt) - new Date(a.publishedAt)
);

export function getArticleBySlug(slug) {
  return articles.find((a) => a.slug === slug);
}

export function getPublishedArticles() {
  return articles.filter((a) => !a.draft);
}

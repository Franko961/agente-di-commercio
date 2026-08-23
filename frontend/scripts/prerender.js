#!/usr/bin/env node
/**
 * Prerendering "leggero" delle pagine pubbliche, eseguito dopo `craco build`.
 *
 * Il problema che risolve: essendo una SPA React, title/description/OG/
 * canonical vengono impostati da React 19 SOLO dopo che il JavaScript viene
 * eseguito nel browser. I crawler social (Facebook, LinkedIn, Twitter/X,
 * WhatsApp) NON eseguono JavaScript quando "srotolano" un link condiviso:
 * leggono solo l'HTML statico restituito dal server — che prima di questo
 * script era sempre lo stesso index.html generico, con i tag OG della
 * homepage, indipendentemente dalla pagina o dall'articolo condiviso.
 *
 * Cosa fa: per ogni pagina pubblica nota (elencate sotto) e ogni articolo
 * del blog non in bozza, genera una copia di build/index.html con i tag
 * <title>/<meta description>/<link canonical>/OG/Twitter già corretti nel
 * markup statico, scritta in build/<percorso>.html (es. build/prezzi.html,
 * build/blog/<slug>.html — non build/<percorso>/index.html: Netlify
 * risolve i file .html senza estensione nell'URL SENZA redirect grazie a
 * "pretty URLs", mentre un file indice in una sottocartella richiederebbe
 * un redirect 301 per aggiungere la barra finale, un giro di rete in più
 * su ogni pagina pubblica e ogni visita di un crawler). Netlify serve un
 * file statico che esiste fisicamente PRIMA di applicare la regola di
 * fallback SPA (/* -> /index.html in public/_redirects), quindi queste
 * pagine vengono servite già pronte, senza bisogno di alcuna modifica alla
 * configurazione di hosting.
 *
 * Non è un prerendering completo del CONTENUTO della pagina (quello
 * richiederebbe eseguire davvero React, es. con Puppeteer, o una vera
 * migrazione a un framework SSR/SSG) — copre solo i tag nell'<head>, che
 * sono esattamente ciò che i crawler social leggono, e ciò che risolve il
 * problema concreto delle anteprime social sbagliate. Il contenuto pieno
 * della pagina resta disponibile ai motori di ricerca che eseguono
 * JavaScript (Google lo fa già), solo con un piccolo ritardo.
 *
 * Genera anche sitemap.xml (build/sitemap.xml, sovrascrivendo l'eventuale
 * copia statica in public/) dagli stessi dati, invece di tenerla scritta a
 * mano: ogni URL nella sitemap corrisponde 1:1 a una pagina qui sopra o a un
 * articolo blog reale, quindi non può più capitare di dimenticare di
 * aggiungerne uno (era già successo).
 */
const fs = require("fs");
const path = require("path");
const { PAGES, DEFAULT_OG_IMAGE, BLOG_ARTICLE_SITEMAP_DEFAULTS } = require("../src/content/pageMeta");

const SITE_URL = "https://salesfly.it";
const BUILD_DIR = path.join(__dirname, "..", "build");
const ARTICLES_DIR = path.join(__dirname, "..", "src", "content", "blog", "articles");

// require() reale (non regex sul testo del file): ogni file articolo ora
// esporta in CommonJS (vedi il commento in un file articolo qualunque, es.
// calcolo-provvigioni-agente-di-commercio.js), quindi Node può caricarlo
// come modulo vero — qualunque forma JS valida funziona (template literal,
// stringhe multilinea, apostrofi, valori importati o costruiti a runtime),
// non solo lo schema testuale che una regex sapeva riconoscere. Prima
// versione: leggeva il file come testo e ne estraeva slug/title/ecc. con
// espressioni regolari — fragile per costruzione, si era già rotta una
// volta (un articolo scomparso dal prerendering per una riga di commento
// che citava "draft: true" come esempio).
function loadBlogArticles() {
  if (!fs.existsSync(ARTICLES_DIR)) return [];
  return fs
    .readdirSync(ARTICLES_DIR)
    .filter((f) => f.endsWith(".js"))
    .map((f) => require(path.join(ARTICLES_DIR, f)).article)
    .filter((a) => a && a.slug && a.title && !a.draft);
}

function buildRoutes() {
  const routes = Object.entries(PAGES).map(([routePath, meta]) => ({
    path: routePath,
    title: meta.title,
    description: meta.description,
    ogDescription: meta.ogDescription || meta.description,
    image: meta.ogImage || DEFAULT_OG_IMAGE,
    type: "website",
    changefreq: meta.changefreq,
    priority: meta.priority,
  }));

  for (const article of loadBlogArticles()) {
    routes.push({
      path: `/blog/${article.slug}`,
      title: `${article.title} — SALESFLY`,
      description: article.description,
      ogDescription: article.description,
      image: article.coverImage ? `${SITE_URL}${article.coverImage}` : DEFAULT_OG_IMAGE,
      type: "article",
      changefreq: BLOG_ARTICLE_SITEMAP_DEFAULTS.changefreq,
      priority: BLOG_ARTICLE_SITEMAP_DEFAULTS.priority,
      publishedAt: article.publishedAt,
      slug: article.slug,
      articleTitle: article.title,
    });
  }

  return routes;
}

function escapeHtmlAttr(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

// Stessa struttura del JSON-LD Article renderizzato lato client in
// BlogPost.jsx — duplicata qui apposta (non importata da lì, che è JSX
// pensato per React) così i crawler che non eseguono JavaScript vedono lo
// stesso markup strutturato dei client che lo fanno.
function buildArticleJsonLd(route) {
  const json = JSON.stringify({
    "@context": "https://schema.org",
    "@type": "Article",
    headline: route.articleTitle,
    description: route.description,
    datePublished: route.publishedAt,
    author: { "@type": "Organization", name: "SALESFLY" },
    publisher: { "@type": "Organization", name: "SALESFLY" },
    mainEntityOfPage: `${SITE_URL}/blog/${route.slug}`,
  });
  // "<\/script" non "</script": il parser HTML cerca la sequenza di
  // chiusura anche dentro il contenuto testuale di <script>, prima che
  // qualsiasi JS venga eseguito — senza questo escape, una description con
  // "</script" al suo interno troncherebbe il tag a metà.
  return `<script type="application/ld+json">${json.replace(/<\//g, "<\\/")}</script>`;
}

function renderPage(template, route) {
  const url = `${SITE_URL}${route.path}`;
  const title = escapeHtmlAttr(route.title);
  const description = escapeHtmlAttr(route.description);
  const ogDescription = escapeHtmlAttr(route.ogDescription);
  const image = escapeHtmlAttr(route.image);

  let html = template;
  html = html.replace(/<title>.*?<\/title>/s, `<title>${title}</title>`);

  // Nessuno di questi esiste già nel template base (vedi public/index.html
  // e il commento lì sopra sul perché): inseriti tutti qui, subito dopo
  // twitter:card, invece di fare un find-and-replace su tag che non ci
  // sono — evita anche il duplicato che si creerebbe se un domani
  // qualcuno li aggiungesse di nuovo lì per errore.
  const insertion = [
    `<meta name="description" content="${description}" />`,
    `<link rel="canonical" href="${url}" />`,
    `<meta property="og:type" content="${route.type}" />`,
    `<meta property="og:title" content="${title}" />`,
    `<meta property="og:description" content="${ogDescription}" />`,
    `<meta property="og:url" content="${url}" />`,
    `<meta property="og:image" content="${image}" />`,
    `<meta property="og:locale" content="it_IT" />`,
    // twitter:card resta SOLO statico nel template (identico ovunque),
    // vedi il commento analogo in PageMeta.jsx.
    `<meta name="twitter:title" content="${title}" />`,
    `<meta name="twitter:description" content="${ogDescription}" />`,
    // Preload dell'immagine di sfondo dell'hero SOLO sulla home (l'unica
    // pagina che la usa): senza questo, il browser non la scopre finché
    // React non la renderizza (esiste solo dopo il JS, non nell'HTML
    // iniziale), partendo a caricarla 1,5s+ dopo il resto della pagina —
    // verificato con Lighthouse come causa principale di un LCP di ~7s.
    // hero-skyline-bg.webp, non hero-skyline.png: versione ridotta e
    // compressa pensata solo per questo sfondo (vedi il commento in
    // Landing.jsx sul perché il .png originale resta invariato altrove).
    ...(route.path === "/" ? [
      `<link rel="preload" as="image" href="${SITE_URL}/hero-skyline-bg.webp" fetchpriority="high" />`,
    ] : []),
    ...(route.type === "article" ? [buildArticleJsonLd(route)] : []),
  ].join("\n        ");
  // \s*\/?> (non " />" letterale): la build di produzione minifica
  // public/index.html, che arriva qui senza lo spazio prima di "/>" — un
  // ancoraggio con lo spazio esatto non troverebbe più nulla da sostituire
  // e l'inserimento sparirebbe silenziosamente in produzione (esattamente
  // quello che è successo alla prima prova di questo script).
  html = html.replace(
    /(<meta name="twitter:card" content="summary_large_image"\s*\/?>)/,
    `$1${insertion}`,
  );

  return html;
}

// Genera sitemap.xml dagli stessi route usati per il prerendering, invece
// di tenerla scritta a mano in public/ — era il problema concreto segnalato
// (un articolo nuovo richiedeva una modifica manuale facile da dimenticare).
// lastmod solo per gli articoli (hanno un publishedAt reale); le pagine
// statiche non lo avevano nemmeno nella sitemap scritta a mano che questa
// sostituisce, quindi lo stesso comportamento è mantenuto qui.
function generateSitemapXml(routes) {
  const urls = routes
    .map((route) => {
      const lastmod = route.publishedAt ? `\n    <lastmod>${route.publishedAt}</lastmod>` : "";
      return `  <url>
    <loc>${SITE_URL}${route.path}</loc>${lastmod}
    <changefreq>${route.changefreq}</changefreq>
    <priority>${route.priority}</priority>
  </url>`;
    })
    .join("\n");

  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>
`;
}

function main() {
  if (!fs.existsSync(BUILD_DIR)) {
    console.error("[prerender] build/ non trovata: esegui prima `craco build`.");
    process.exit(1);
  }
  const templatePath = path.join(BUILD_DIR, "index.html");
  const template = fs.readFileSync(templatePath, "utf8");

  // Copia GENERICA del template, presa PRIMA di riscrivere build/index.html
  // con i tag specifici della home qui sotto: serve da fallback SPA per le
  // rotte non elencate in PAGES (login, reset-password, /app/*, ecc. — vedi
  // public/_redirects, aggiornato per puntare qui invece che a index.html).
  // Senza questa copia separata, quelle pagine erediterebbero il canonical
  // e i tag OG della HOME (sbagliati per loro) invece di restare generici
  // come erano prima di questo script.
  fs.writeFileSync(path.join(BUILD_DIR, "app-shell.html"), template);

  const routes = buildRoutes();
  for (const route of routes) {
    const html = renderPage(template, route);
    // "/" resta build/index.html (il file richiesto per servire la root);
    // ogni altra rotta diventa un file .html pari, non una sottocartella
    // con index.html — vedi il commento in testa al file sul perché.
    const outPath = route.path === "/"
      ? path.join(BUILD_DIR, "index.html")
      : path.join(BUILD_DIR, `${route.path}.html`);
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    fs.writeFileSync(outPath, html);
  }

  fs.writeFileSync(path.join(BUILD_DIR, "sitemap.xml"), generateSitemapXml(routes));

  console.log(`[prerender] Generate ${routes.length} pagine: ${routes.map((r) => r.path).join(", ")}`);
  console.log(`[prerender] sitemap.xml rigenerata (${routes.length} URL).`);
}

main();

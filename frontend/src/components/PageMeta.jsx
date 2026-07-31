import { PAGES, DEFAULT_OG_IMAGE } from "../content/pageMeta";

const SITE_URL = "https://salesfly.it";

// Un solo componente per title/description/canonical/OG/Twitter, riusato da
// tutte le pagine pubbliche: prima ogni pagina impostava i propri tag a
// mano, e la maggior parte (tutte tranne Landing e BlogPost) non impostava
// affatto og:title/og:description/og:image/twitter:* — quindi, anche a
// JavaScript eseguito, condividerle su Facebook/LinkedIn mostrava ancora i
// tag generici rimasti in public/index.html. path/title/description/image
// espliciti (usati da BlogPost per i dati per-articolo) hanno sempre la
// precedenza sui valori di default in content/pageMeta.js.
export default function PageMeta({
  path, title, description, ogDescription, image, type = "website", noindex = false, children,
}) {
  const page = PAGES[path] || {};
  const finalTitle = title || page.title;
  const finalDescription = description || page.description;
  // Distinto da finalDescription: la pagina Landing usa una descrizione SEO
  // più lunga per <meta name="description"> e un testo più breve e
  // "da social" per og:description/twitter:description — se non specificato
  // separatamente, resta comunque lo stesso testo.
  const finalOgDescription = ogDescription || page.ogDescription || finalDescription;
  const finalImage = image || page.ogImage || DEFAULT_OG_IMAGE;
  const url = `${SITE_URL}${path}`;

  return (
    <>
      <title>{finalTitle}</title>
      <meta name="description" content={finalDescription} />
      <link rel="canonical" href={url} />
      {noindex && <meta name="robots" content="noindex" />}
      <meta property="og:type" content={type} />
      <meta property="og:title" content={finalTitle} />
      <meta property="og:description" content={finalOgDescription} />
      <meta property="og:url" content={url} />
      <meta property="og:image" content={finalImage} />
      <meta property="og:locale" content="it_IT" />
      {/* twitter:card resta SOLO statico in public/index.html: è
      identico su ogni pagina ("summary_large_image"), renderizzarlo
      anche qui duplicherebbe il tag invece di sostituirlo (vedi il
      commento in index.html sul perché React non rimuove i tag statici
      che non ha creato lui). */}
      <meta name="twitter:title" content={finalTitle} />
      <meta name="twitter:description" content={finalOgDescription} />
      {children}
    </>
  );
}

import { Suspense } from "react";
import { useParams, Navigate, Link } from "react-router-dom";
import { ArrowLeft, ArrowRight, Calendar } from "lucide-react";
import { getArticleBySlug, getPublishedArticles } from "@/content/blog";
import { PILLAR, PILLAR_CLUSTER_SLUGS } from "@/content/blog/pillar";
import { themeForSlug } from "@/content/blog/theme";
import { CALCULATORS } from "@/content/calculators";
import PublicHeader from "@/components/PublicHeader";
import PublicFooter from "@/components/PublicFooter";
import PageMeta from "@/components/PageMeta";
import { trackEvent } from "@/lib/analytics";

// Link interni dentro paragrafi e liste con la sintassi [testo](/percorso):
// solo percorsi interni (devono iniziare con "/"), così un refuso non può
// trasformarsi in un link esterno. Un testo senza questa sintassi torna
// identico, quindi gli articoli esistenti non cambiano.
const INLINE_LINK = /\[([^\]]+)\]\((\/[^)\s]*)\)/g;

function renderInline(text, articleSlug) {
  const parts = [];
  let last = 0;
  for (const m of text.matchAll(INLINE_LINK)) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    parts.push(
      <Link
        key={m.index}
        to={m[2]}
        onClick={() => trackEvent("blog_inline_link_click", { from: articleSlug, to: m[2] })}
        className="text-[#B23E00] underline underline-offset-2 hover:text-[#0A192F]"
      >
        {m[1]}
      </Link>,
    );
    last = m.index + m[0].length;
  }
  if (last === 0) return text;
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

function renderBlock(block, i, articleSlug) {
  switch (block.type) {
    case "calculator": {
      // Registro condiviso con le pagine standalone /calcolatori/:slug
      // (content/calculators.js) — solo il nome nel blocco dell'articolo,
      // così un nuovo calcolatore si aggiunge in un solo posto senza
      // toccare renderBlock. Caricati con lazy() dentro il registro: solo
      // i pochi articoli che hanno davvero un blocco "calculator" pagano
      // il costo di questo JS, non ogni pagina del blog.
      const Calc = CALCULATORS[block.name]?.component;
      if (!Calc) {
        // Un nome che non corrisponde a nessun calcolatore registrato
        // andrebbe altrimenti perso in silenzio (nessun errore, nessun
        // avviso da nessuna parte) — un refuso nel campo "name" di un
        // futuro articolo sparirebbe dalla pagina pubblicata senza che
        // nessuno se ne accorga finché non la legge manualmente.
        console.warn(`Blocco "calculator" con name non registrato: "${block.name}"`);
        return null;
      }
      return (
        <Suspense key={i} fallback={null}>
          <Calc />
        </Suspense>
      );
    }
    case "h2":
      return (
        <h2 key={i} className="font-cabinet font-black text-2xl mt-10 mb-4">
          {block.text}
        </h2>
      );
    case "ul":
      return (
        <ul key={i} className="list-disc pl-5 space-y-2 my-4 text-[15px] text-[#3F3F46]">
          {block.items.map((item, j) => (
            <li key={j}>{renderInline(item, articleSlug)}</li>
          ))}
        </ul>
      );
    case "cta":
      return (
        <div
          key={i}
          className="my-8 bg-[#0A192F] text-white rounded-xl p-6 md:p-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-4"
        >
          <div>
            <div className="font-cabinet font-black text-lg mb-1">{block.title}</div>
            <p className="text-[14px] text-white/70">{block.text}</p>
          </div>
          <div className="shrink-0 flex flex-col items-start md:items-end gap-2">
            <Link
              to={block.href || "/richiedi-demo"}
              onClick={() => trackEvent("cta_click", { location: "blog_article", article_slug: articleSlug })}
              className="inline-flex items-center gap-2 bg-[#B23E00] text-white rounded-lg px-5 py-3 text-[14px] font-bold hover:bg-[#e04e00] transition-colors whitespace-nowrap"
            >
              {block.cta || "Inizia prova gratuita"}
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/prezzi"
              onClick={() => trackEvent("cta_click", { location: "blog_article_prezzi", article_slug: articleSlug })}
              className="text-[13px] text-white/60 hover:text-white underline underline-offset-2 transition-colors"
            >
              Vedi i prezzi
            </Link>
          </div>
        </div>
      );
    case "p":
    default:
      return (
        <p key={i} className="text-[15px] leading-relaxed text-[#3F3F46] mb-4">
          {renderInline(block.text, articleSlug)}
        </p>
      );
  }
}

export default function BlogPost() {
  const { slug } = useParams();
  const article = getArticleBySlug(slug);

  if (!article) return <Navigate to="/blog" replace />;

  // Fino a 2 altri articoli pubblicati: prima quelli dello stesso cluster
  // tematico (stessa "macro" di content/blog/theme.js — Vendita/Fisco/
  // Tecnologia/Guide, la stessa usata dal filtro in /blog), poi — solo se
  // il cluster non basta a riempire i 2 slot — i più recenti in assoluto.
  // Prima di questo, "Leggi anche" mostrava sempre e solo i 2 articoli più
  // recenti del blog, indipendentemente dall'argomento: un lettore
  // dell'articolo sul FIRR poteva ritrovarsi rimandato a un confronto tra
  // CRM. getPublishedArticles() è già ordinato per data decrescente, quindi
  // sia il cluster sia il fallback restano "più recente prima".
  const otherArticles = getPublishedArticles().filter((a) => a.slug !== article.slug);
  const currentMacro = themeForSlug(article.slug).macro;
  const sameCluster = otherArticles.filter((a) => themeForSlug(a.slug).macro === currentMacro);
  const restArticles = otherArticles.filter((a) => themeForSlug(a.slug).macro !== currentMacro);
  const relatedArticles = [...sameCluster, ...restArticles].slice(0, 2);

  return (
    <div className="min-h-screen bg-[#F9F9F8] flex flex-col">
      <PageMeta
        path={`/blog/${article.slug}`}
        title={`${article.title} — SALESFLY`}
        description={article.description}
        image={article.coverImage ? `https://salesfly.it${article.coverImage}` : undefined}
        type="article"
        noindex={article.draft}
      >
        <script type="application/ld+json">
          {JSON.stringify({
            "@context": "https://schema.org",
            "@type": "Article",
            headline: article.title,
            description: article.description,
            datePublished: article.publishedAt,
            author: { "@type": "Organization", name: "SALESFLY" },
            publisher: { "@type": "Organization", name: "SALESFLY" },
            mainEntityOfPage: `https://salesfly.it/blog/${article.slug}`,
          })}
        </script>
      </PageMeta>

      <PublicHeader />

      <main className="flex-1 px-6 py-16 max-w-2xl mx-auto w-full">
        <Link
          to="/blog"
          className="inline-flex items-center gap-1.5 text-[13px] text-[#52525B] hover:text-[#0A192F] mb-8"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Tutte le guide
        </Link>

        <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#B23E00] mb-3 flex items-center gap-1.5">
          <Calendar className="w-3 h-3" />
          {new Date(article.publishedAt).toLocaleDateString("it-IT", {
            day: "numeric",
            month: "long",
            year: "numeric",
          })}
        </div>
        <h1 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight mb-8">
          {article.title}
        </h1>

        {article.coverImage && (
          <img
            src={article.coverImage}
            alt={article.imageAlt || article.title}
            className="w-full aspect-video object-cover rounded-xl border border-[#E4E4E1] mb-10"
          />
        )}

        <article>{article.blocks.map((block, i) => renderBlock(block, i, article.slug))}</article>

        {PILLAR_CLUSTER_SLUGS.includes(article.slug) && (
          <Link
            to={PILLAR.path}
            onClick={() => trackEvent("pillar_link_click", { from: article.slug })}
            className="block mt-10 bg-white border border-[#E4E4E1] rounded-xl p-6 hover:border-[#0A192F] transition-colors"
          >
            <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#B23E00] mb-2">Guida completa</div>
            <div className="font-cabinet font-bold text-lg mb-2">{PILLAR.title}</div>
            <p className="text-[14px] text-[#52525B] mb-3">{PILLAR.text}</p>
            <span className="inline-flex items-center gap-1 text-[13px] text-[#B23E00] font-medium">
              Leggi la guida <ArrowRight className="w-3.5 h-3.5" />
            </span>
          </Link>
        )}

        {relatedArticles.length > 0 && (
          <div className="mt-16 pt-10 border-t border-[#E4E4E1]">
            <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#6B6B72] mb-4">
              Leggi anche
            </div>
            <div className="space-y-4">
              {relatedArticles.map((a) => (
                <Link
                  key={a.slug}
                  to={`/blog/${a.slug}`}
                  className="block bg-white border border-[#E4E4E1] rounded-xl p-6 hover:border-[#0A192F] transition-colors"
                >
                  <div className="font-cabinet font-bold text-lg mb-2">{a.title}</div>
                  <p className="text-[14px] text-[#52525B] mb-3">{a.description}</p>
                  <span className="inline-flex items-center gap-1 text-[13px] text-[#B23E00] font-medium">
                    Leggi <ArrowRight className="w-3.5 h-3.5" />
                  </span>
                </Link>
              ))}
            </div>
          </div>
        )}
      </main>

      <PublicFooter />
    </div>
  );
}

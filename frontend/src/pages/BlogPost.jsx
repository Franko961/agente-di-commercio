import { lazy, Suspense } from "react";
import { useParams, Navigate, Link } from "react-router-dom";
import { ArrowLeft, ArrowRight, Calendar } from "lucide-react";
import { getArticleBySlug, getPublishedArticles } from "@/content/blog";
import PublicHeader from "@/components/PublicHeader";
import PublicFooter from "@/components/PublicFooter";
import PageMeta from "@/components/PageMeta";

// Registro dei componenti interattivi richiamabili da un blocco di tipo
// "calculator" — solo il nome nel file dell'articolo, così un nuovo
// calcolatore si aggiunge qui senza toccare renderBlock. Caricati con
// lazy(): solo i 2 articoli su ~30 che hanno davvero un blocco
// "calculator" pagano il costo di questo JS, non ogni pagina del blog.
const CALCULATORS = {
  ritenutaEnasarco: lazy(() => import("@/components/RitenutaEnasarcoCalculator")),
  firr: lazy(() => import("@/components/FirrCalculator")),
};

function renderBlock(block, i) {
  switch (block.type) {
    case "calculator": {
      const Calc = CALCULATORS[block.name];
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
            <li key={j}>{item}</li>
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
          <Link
            to={block.href || "/richiedi-demo"}
            className="shrink-0 inline-flex items-center gap-2 bg-[#B23E00] text-white rounded-lg px-5 py-3 text-[14px] font-bold hover:bg-[#e04e00] transition-colors whitespace-nowrap"
          >
            {block.cta || "Inizia prova gratuita"}
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      );
    case "p":
    default:
      return (
        <p key={i} className="text-[15px] leading-relaxed text-[#3F3F46] mb-4">
          {block.text}
        </p>
      );
  }
}

export default function BlogPost() {
  const { slug } = useParams();
  const article = getArticleBySlug(slug);

  if (!article) return <Navigate to="/blog" replace />;

  // Fino a 2 altri articoli pubblicati, i più recenti dopo quello corrente:
  // collega ogni articolo agli altri invece di lasciarlo isolato (nessun
  // link interno tra i pezzi del blog finora), aiutando sia il crawling
  // di Google sia la permanenza del lettore sul sito.
  const relatedArticles = getPublishedArticles()
    .filter((a) => a.slug !== article.slug)
    .slice(0, 2);

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

        <article>{article.blocks.map(renderBlock)}</article>

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

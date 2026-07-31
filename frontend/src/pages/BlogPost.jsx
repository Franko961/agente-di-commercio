import { useParams, Navigate, Link } from "react-router-dom";
import { ArrowLeft, Calendar } from "lucide-react";
import { getArticleBySlug } from "@/content/blog";
import PublicHeader from "@/components/PublicHeader";
import PublicFooter from "@/components/PublicFooter";
import PageMeta from "@/components/PageMeta";

function renderBlock(block, i) {
  switch (block.type) {
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

        <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00] mb-3 flex items-center gap-1.5">
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
      </main>

      <PublicFooter />
    </div>
  );
}

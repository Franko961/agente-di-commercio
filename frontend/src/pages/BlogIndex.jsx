import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { getPublishedArticles } from "@/content/blog";
import PublicHeader from "@/components/PublicHeader";
import PublicFooter from "@/components/PublicFooter";
import PageMeta from "@/components/PageMeta";

export default function BlogIndex() {
  const articles = getPublishedArticles();

  return (
    <div className="min-h-screen bg-[#F9F9F8] flex flex-col">
      <PageMeta path="/blog" />

      <PublicHeader />

      <main className="flex-1 px-6 py-16 max-w-3xl mx-auto w-full">
        <div className="text-center mb-12">
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00] mb-3">Blog</div>
          <h1 className="font-cabinet font-black text-4xl tracking-tight mb-4">
            Blog per agenti di commercio
          </h1>
          <p className="text-[16px] text-[#52525B] max-w-xl mx-auto">
            Provvigioni, ENASARCO, contratti di agenzia: le risposte alle domande che contano davvero.
          </p>
        </div>

        {articles.length === 0 ? (
          <p className="text-center text-[14px] text-[#A1A1AA]">Presto nuovi contenuti.</p>
        ) : (
          <div className="space-y-4">
            {articles.map((a) => (
              <Link
                key={a.slug}
                to={`/blog/${a.slug}`}
                className="block bg-white border border-[#E4E4E1] rounded-xl p-6 hover:border-[#0A192F] transition-colors"
              >
                <div className="font-cabinet font-bold text-lg mb-2">{a.title}</div>
                <p className="text-[14px] text-[#52525B] mb-3">{a.description}</p>
                <span className="inline-flex items-center gap-1 text-[13px] text-[#FF5A00] font-medium">
                  Leggi <ArrowRight className="w-3.5 h-3.5" />
                </span>
              </Link>
            ))}
          </div>
        )}
      </main>

      <PublicFooter />
    </div>
  );
}

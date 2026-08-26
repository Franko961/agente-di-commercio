import { useState } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { getPublishedArticles } from "@/content/blog";
import PublicHeader from "@/components/PublicHeader";
import PublicFooter from "@/components/PublicFooter";
import PageMeta from "@/components/PageMeta";

const PER_PAGE = 9;

// Copertine in stile testata di rivista: foto reale (Unsplash, dominio già
// autorizzato dalla CSP del sito in img-src, licenza Unsplash che ne permette
// l'uso commerciale libero) con overlay sfumato scuro sotto per leggibilità
// del testo sovrapposto — non un'icona/illustrazione generata.
//
// Categoria a tema per slug, in ordine dal più specifico al più generico — i
// sotto-temi ENASARCO (rimborso tasse, bonus scolastico) vanno controllati
// prima del fallback generico "enasarco".
const THEME_RULES = [
  [(s) => s.includes("rimborso-tasse") || s.includes("universita"), "STUDIO", "1541339907198-e08756dedf3f"],
  [(s) => s.includes("bonus-scolastico"), "FAMIGLIA", "1603367563698-67012943fd67"],
  [(s) => s.includes("enasarco"), "ENASARCO", "1637763723578-79a4ca9225f7"],
  [(s) => s.includes("contratto"), "CONTRATTI", "1450101499163-c8848c66ca85"],
  [(s) => s.includes("aumentare-provvigioni") || s.includes("calcolo-provvigioni"), "PROVVIGIONI", "1560221328-12fe60f83ab8"],
  [(s) => s.includes("excel"), "MIGRAZIONE", "1487017159836-4e23ece2e4cf"],
  [(s) => s.includes("due-minuti"), "SETUP", "1449247709967-d4461a6a6103"],
  [(s) => s.includes("hubspot") || s.includes("migliori-crm"), "CONFRONTO", "1539992190939-08f22d7ebaad"],
  [(s) => s.includes("intelligenza-artificiale") || s.includes("ai-crm"), "AI", "1674027444485-cec3da58eef4"],
  [(s) => s.includes("mobile") || s.includes("telefono"), "MOBILE", "1592890288564-76628a30a657"],
  [(s) => s.includes("giro-visite"), "TERRITORIO", "1684836571999-f3dc511935e7"],
  [(s) => s.includes("mandanti"), "MANDANTI", "1672380135241-c024f7fbfa13"],
  [(s) => s.includes("spese"), "SPESE", "1649209979970-f01d950cc5ed"],
];
const DEFAULT_THEME = { category: "GUIDA", photoId: "1612367980327-7454a7276aa7" };

function themeForSlug(slug) {
  const match = THEME_RULES.find(([test]) => test(slug));
  return match ? { category: match[1], photoId: match[2] } : DEFAULT_THEME;
}

function ArticleCover({ slug, issueNumber, priority }) {
  const { category, photoId } = themeForSlug(slug);
  return (
    <div className="aspect-[3/4] rounded-2xl relative overflow-hidden shadow-sm group-hover:shadow-xl transition-shadow duration-300">
      <img
        src={`https://images.unsplash.com/photo-${photoId}?w=600&q=75&auto=format&fit=crop`}
        alt=""
        loading={priority ? "eager" : "lazy"}
        fetchpriority={priority ? "high" : undefined}
        className="absolute inset-0 w-full h-full object-cover transition-transform duration-300 ease-out group-hover:scale-110"
      />
      <div
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(to top, rgba(10,25,47,0.9) 0%, rgba(10,25,47,0.15) 45%, rgba(10,25,47,0.35) 100%)",
        }}
      />
      <div className="absolute inset-0 flex flex-col justify-between p-5">
        <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-white/90 self-start px-2.5 py-1 rounded-full bg-black/25 backdrop-blur-sm">
          N. {issueNumber}
        </span>
        <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-white self-start px-2.5 py-1 rounded-full border border-white/40">
          {category}
        </span>
      </div>
    </div>
  );
}

export default function BlogIndex() {
  const articles = getPublishedArticles();
  const total = articles.length;
  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE));
  const [page, setPage] = useState(1);

  const start = (page - 1) * PER_PAGE;
  const pageArticles = articles.slice(start, start + PER_PAGE);

  function goToPage(p) {
    const clamped = Math.min(Math.max(1, p), totalPages);
    setPage(clamped);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <div className="min-h-screen bg-[#F9F9F8] flex flex-col">
      <PageMeta path="/blog" />

      <PublicHeader />

      <main className="flex-1 px-6 py-16 max-w-6xl mx-auto w-full">
        <div className="text-center mb-12">
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#B23E00] mb-3">Blog</div>
          <h1 className="font-cabinet font-black text-4xl tracking-tight mb-4">
            Blog per agenti di commercio
          </h1>
          <p className="text-[16px] text-[#52525B] max-w-xl mx-auto">
            Provvigioni, ENASARCO, contratti di agenzia: le risposte alle domande che contano davvero.
          </p>
        </div>

        {total === 0 ? (
          <p className="text-center text-[14px] text-[#6B6B72]">Presto nuovi contenuti.</p>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-12">
              {pageArticles.map((a, i) => (
                <Link key={a.slug} to={`/blog/${a.slug}`} className="group block">
                  <ArticleCover slug={a.slug} issueNumber={total - (start + i)} priority={i === 0} />
                  <div className="mt-4">
                    <div className="font-mono text-[11px] uppercase tracking-widest text-[#6B6B72] mb-2">
                      Issue {total - (start + i)}
                    </div>
                    <h2 className="font-cabinet font-bold text-lg mb-2 group-hover:text-[#B23E00] transition-colors">
                      {a.title}
                    </h2>
                    <p className="text-[14px] text-[#52525B] line-clamp-3">{a.description}</p>
                  </div>
                </Link>
              ))}
            </div>

            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 mt-16">
                <button
                  onClick={() => goToPage(page - 1)}
                  disabled={page === 1}
                  className="w-9 h-9 flex items-center justify-center rounded-md border border-[#E4E4E1] text-[#0A192F] disabled:opacity-30 disabled:cursor-not-allowed hover:border-[#0A192F] transition-colors"
                  aria-label="Pagina precedente"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                  <button
                    key={p}
                    onClick={() => goToPage(p)}
                    className={`w-9 h-9 flex items-center justify-center rounded-md font-mono text-[13px] transition-colors ${
                      p === page
                        ? "bg-[#0A192F] text-white"
                        : "border border-[#E4E4E1] text-[#52525B] hover:border-[#0A192F]"
                    }`}
                  >
                    {p}
                  </button>
                ))}
                <button
                  onClick={() => goToPage(page + 1)}
                  disabled={page === totalPages}
                  className="w-9 h-9 flex items-center justify-center rounded-md border border-[#E4E4E1] text-[#0A192F] disabled:opacity-30 disabled:cursor-not-allowed hover:border-[#0A192F] transition-colors"
                  aria-label="Pagina successiva"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </>
        )}
      </main>

      <PublicFooter />
    </div>
  );
}

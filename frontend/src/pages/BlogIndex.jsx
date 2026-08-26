import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ChevronLeft,
  ChevronRight,
  Calculator,
  TrendingUp,
  GraduationCap,
  BookOpen,
  ShieldCheck,
  FileSignature,
  FileSpreadsheet,
  Rocket,
  Scale,
  Sparkles,
  Smartphone,
  Route,
  Building2,
  Receipt,
  Newspaper,
} from "lucide-react";
import { getPublishedArticles } from "@/content/blog";
import PublicHeader from "@/components/PublicHeader";
import PublicFooter from "@/components/PublicFooter";
import PageMeta from "@/components/PageMeta";

const PER_PAGE = 9;

// Sfondi pastello in rotazione per le copertine — nessuna immagine reale per
// articolo (niente fototeca esterna, la CSP del sito limita i domini immagine
// consentiti), quindi il "visual" è un'icona a tema grande su sfondo colorato,
// come una copertina editoriale illustrata invece che una foto.
const COVER_PALETTE = [
  { bg: "#D9E4D3", text: "#0A192F" }, // salvia
  { bg: "#F0E4D3", text: "#0A192F" }, // sabbia
  { bg: "#DCE3E8", text: "#0A192F" }, // grigio-blu
  { bg: "#E8C9B8", text: "#0A192F" }, // terracotta chiaro
  { bg: "#E4E0E8", text: "#0A192F" }, // lavanda
];

// Icona a tema per slug, in ordine dal più specifico al più generico — i
// sotto-temi ENASARCO (rimborso tasse, bonus scolastico) vanno controllati
// prima del fallback generico "enasarco".
const ICON_RULES = [
  [(s) => s.includes("rimborso-tasse") || s.includes("universita"), GraduationCap],
  [(s) => s.includes("bonus-scolastico"), BookOpen],
  [(s) => s.includes("enasarco"), ShieldCheck],
  [(s) => s.includes("contratto"), FileSignature],
  [(s) => s.includes("aumentare-provvigioni"), TrendingUp],
  [(s) => s.includes("calcolo-provvigioni"), Calculator],
  [(s) => s.includes("excel"), FileSpreadsheet],
  [(s) => s.includes("due-minuti"), Rocket],
  [(s) => s.includes("hubspot") || s.includes("migliori-crm"), Scale],
  [(s) => s.includes("intelligenza-artificiale") || s.includes("ai-crm"), Sparkles],
  [(s) => s.includes("mobile") || s.includes("telefono"), Smartphone],
  [(s) => s.includes("giro-visite"), Route],
  [(s) => s.includes("mandanti"), Building2],
  [(s) => s.includes("spese"), Receipt],
];

function iconForSlug(slug) {
  const match = ICON_RULES.find(([test]) => test(slug));
  return match ? match[1] : Newspaper;
}

function ArticleCover({ slug, issueNumber, index }) {
  const palette = COVER_PALETTE[index % COVER_PALETTE.length];
  const Icon = iconForSlug(slug);
  return (
    <div
      className="aspect-[3/4] rounded-2xl relative overflow-hidden flex flex-col p-5"
      style={{ background: palette.bg }}
    >
      <div
        className="absolute -right-10 -bottom-10 w-40 h-40 rounded-full border-2 opacity-20"
        style={{ borderColor: palette.text }}
      />
      <span
        className="font-mono text-[11px] uppercase tracking-[0.2em] relative z-10"
        style={{ color: palette.text, opacity: 0.7 }}
      >
        N. {issueNumber}
      </span>
      <div className="flex-1 flex items-center justify-center relative z-10">
        <Icon className="w-20 h-20" strokeWidth={1.25} style={{ color: palette.text, opacity: 0.85 }} />
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
                  <ArticleCover slug={a.slug} issueNumber={total - (start + i)} index={start + i} />
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

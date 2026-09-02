import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, ChevronLeft, ChevronRight } from "lucide-react";
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
// Ogni regola ha anche una "macro" (una delle 4 in MACROS più sotto): serve
// solo al filtro in testa alla pagina, un livello più grossolano della
// categoria puntuale mostrata sulla card — senza questo, il filtro
// avrebbe una ventina di voci (una per ogni categoria specifica), troppe
// per restare leggibile.
//
// Categoria a tema per slug, in ordine dal più specifico al più generico — i
// sotto-temi ENASARCO (rimborso tasse, bonus scolastico) vanno controllati
// prima del fallback generico "enasarco". IMPORTANTE: ogni nuovo articolo
// aggiunto al blog va accoppiato a una regola qui — senza, ricade sul tema
// generico DEFAULT_THEME, e più articoli scoperti in questo modo finiscono
// per avere la stessa identica copertina (è esattamente il problema che ha
// motivato questa lista).
const THEME_RULES = [
  [(s) => s.includes("rimborso-tasse") || s.includes("universita"), "STUDIO", "1541339907198-e08756dedf3f", "Fisco"],
  [(s) => s.includes("bonus-scolastico"), "FAMIGLIA", "1603367563698-67012943fd67", "Fisco"],
  [(s) => s.includes("ritenuta-acconto"), "RITENUTA", "1554224154-26032ffc0d07", "Fisco"],
  [(s) => s.includes("firr"), "INDENNITÀ", "1707157284454-553ef0a4ed0d", "Fisco"],
  [(s) => s.includes("deducibilita-fiscale-auto"), "AUTO", "1616805111996-e39d9a19e35c", "Fisco"],
  [(s) => s.includes("verifica-partita-iva-vies"), "FISCO UE", "1608817576136-0f3a56922823", "Fisco"],
  // Va prima della regola generica "enasarco" qui sotto, altrimenti le due
  // finiscono con la stessa foto (è successo, vedi il commento sopra).
  [(s) => s.includes("minimali-massimali"), "MASSIMALI", "1633158829585-23ba8f7c8caf", "Fisco"],
  [(s) => s.includes("enasarco"), "ENASARCO", "1637763723578-79a4ca9225f7", "Fisco"],
  [(s) => s.includes("spese"), "SPESE", "1649209979970-f01d950cc5ed", "Fisco"],
  [(s) => s.includes("diventare-agente-di-commercio-requisiti"), "REQUISITI", "1562564055-71e051d33c19", "Guide"],
  [(s) => s.includes("differenza-agente-commercio-agente-sportivo"), "PROFESSIONI", "1533073526757-2c8ca1df9f1c", "Guide"],
  [(s) => s.includes("contratto"), "CONTRATTI", "1450101499163-c8848c66ca85", "Guide"],
  [(s) => s.includes("excel"), "MIGRAZIONE", "1487017159836-4e23ece2e4cf", "Guide"],
  [(s) => s.includes("due-minuti"), "SETUP", "1449247709967-d4461a6a6103", "Guide"],
  [(s) => s.includes("storno-provvigioni"), "PROVVIGIONI", "1638262052640-82e94d64664a", "Vendita"],
  [(s) => s.includes("catalogo-digitale"), "CATALOGO", "1700165644892-3dd6b67b25bc", "Vendita"],
  [(s) => s.includes("percorso-ottimizzato"), "PERCORSO", "1461183479101-6c14cd5299c4", "Vendita"],
  // "come-calcolare-provvigioni" va prima: senza questa regola dedicata
  // non veniva intercettato da nessun'altra ("calcolo-provvigioni" ≠
  // "calcolare-provvigioni") e ricadeva sul tema generico.
  [(s) => s.includes("come-calcolare-provvigioni"), "PROVVIGIONI", "1580048915913-4f8f5cb481c4", "Vendita"],
  [(s) => s.includes("aumentare-provvigioni") || s.includes("calcolo-provvigioni"), "PROVVIGIONI", "1560221328-12fe60f83ab8", "Vendita"],
  [(s) => s.includes("giro-visite"), "TERRITORIO", "1684836571999-f3dc511935e7", "Vendita"],
  [(s) => s.includes("mandanti"), "MANDANTI", "1672380135241-c024f7fbfa13", "Vendita"],
  [(s) => s.includes("crm-italiano"), "CRM ITALIANO", "1536140012599-830a641c27e6", "Tecnologia"],
  [(s) => s.includes("hubspot"), "CONFRONTO", "1616279468745-de6fdbad0262", "Tecnologia"],
  [(s) => s.includes("migliori-crm"), "CONFRONTO", "1539992190939-08f22d7ebaad", "Tecnologia"],
  // "come-ai-e-crm" va prima della regola generica "ai-crm" qui sotto:
  // "ai-e-crm" non contiene "ai-crm" come sottostringa esatta.
  [(s) => s.includes("come-ai-e-crm"), "AI", "1600087626120-062700394a01", "Tecnologia"],
  [(s) => s.includes("intelligenza-artificiale") || s.includes("ai-crm"), "AI", "1674027444485-cec3da58eef4", "Tecnologia"],
  [(s) => s.includes("telefono"), "MOBILE", "1511707171634-5f897ff02aa9", "Tecnologia"],
  [(s) => s.includes("mobile"), "MOBILE", "1592890288564-76628a30a657", "Tecnologia"],
];
const DEFAULT_THEME = { category: "GUIDA", photoId: "1612367980327-7454a7276aa7", macro: "Guide" };

// Filtro in testa alla pagina: 4 macro-categorie editoriali più "Tutti",
// deliberatamente poche (non una per ogni THEME_RULES) — l'obiettivo è
// restare leggibile, non essere esaustivi.
const MACROS = ["Tutti", "Vendita", "Fisco", "Tecnologia", "Guide"];

function themeForSlug(slug) {
  const match = THEME_RULES.find(([test]) => test(slug));
  return match ? { category: match[1], photoId: match[2], macro: match[3] } : DEFAULT_THEME;
}

function formatDate(dateStr) {
  return new Date(dateStr)
    .toLocaleDateString("it-IT", { day: "2-digit", month: "short", year: "numeric" })
    .toUpperCase()
    .replace(".", "");
}

// aspect-video = 16:9 (utility nativa di Tailwind): sostituisce il
// precedente aspect-[3/4], quasi verticale, che da solo occupava circa il
// 65% dell'altezza della card.
function CoverImage({ slug, priority, className = "" }) {
  const { category, photoId } = themeForSlug(slug);
  return (
    <div className={`relative overflow-hidden ${className}`}>
      <img
        src={`https://images.unsplash.com/photo-${photoId}?w=800&q=68&auto=format&fit=crop`}
        alt=""
        loading={priority ? "eager" : "lazy"}
        fetchPriority={priority ? "high" : undefined}
        className="absolute inset-0 w-full h-full object-cover transition-transform duration-500 ease-out group-hover:scale-105"
      />
      <div
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(to top, rgba(10,25,47,0.85) 0%, rgba(10,25,47,0.05) 55%, rgba(10,25,47,0.25) 100%)",
        }}
      />
      {/* Una sola pill sulla foto — la numerazione "Issue" è stata rimossa
      dalla copertina, resta solo come dettaglio editoriale minore, la data,
      sotto l'immagine. */}
      <span className="absolute top-4 left-4 font-mono text-[10px] uppercase tracking-[0.15em] text-white self-start px-2.5 py-1 rounded-full border border-white/40">
        {category}
      </span>
    </div>
  );
}

function ArticleCard({ article, priority }) {
  const { category } = themeForSlug(article.slug);
  return (
    <Link
      to={`/blog/${article.slug}`}
      className="group block rounded-2xl transition-transform duration-300 hover:-translate-y-1"
    >
      <CoverImage slug={article.slug} priority={priority} className="aspect-video rounded-2xl shadow-sm group-hover:shadow-xl transition-shadow duration-300" />
      <div className="mt-4">
        <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-widest mb-2">
          <span className="text-[#B23E00] font-semibold">{category}</span>
          <span className="text-[#6B6B72]">·</span>
          <span className="text-[#6B6B72]">{formatDate(article.publishedAt)}</span>
        </div>
        <h2 className="font-cabinet font-bold text-[21px] leading-[1.25] mb-2 group-hover:text-[#B23E00] transition-colors">
          {article.title}
        </h2>
        <p className="text-[14px] text-[#52525B] line-clamp-2 mb-3">{article.description}</p>
        <span className="inline-flex items-center gap-1.5 text-[13px] font-semibold text-[#B23E00]">
          Leggi l'articolo
          <ArrowRight className="w-3.5 h-3.5 transition-transform duration-300 group-hover:translate-x-1" />
        </span>
      </div>
    </Link>
  );
}

function FeaturedArticle({ article }) {
  const { category } = themeForSlug(article.slug);
  return (
    <Link
      to={`/blog/${article.slug}`}
      className="group grid md:grid-cols-2 gap-0 mb-16 items-stretch border border-[#E4E4E1] rounded-2xl overflow-hidden bg-white hover:shadow-xl transition-shadow duration-300"
    >
      <CoverImage slug={article.slug} priority className="aspect-video md:aspect-auto" />
      <div className="p-8 md:p-10 flex flex-col justify-center">
        <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-widest mb-3">
          <span className="px-2.5 py-1 rounded-full bg-[#B23E00]/10 text-[#B23E00] font-semibold">In evidenza</span>
          <span className="text-[#6B6B72]">{category} · {formatDate(article.publishedAt)}</span>
        </div>
        <h2 className="font-cabinet font-black text-[26px] md:text-[30px] leading-tight mb-4 group-hover:text-[#B23E00] transition-colors">
          {article.title}
        </h2>
        <p className="text-[15px] text-[#52525B] mb-6 line-clamp-3">{article.description}</p>
        <span className="inline-flex items-center gap-1.5 text-[14px] font-semibold text-[#B23E00]">
          Leggi l'articolo
          <ArrowRight className="w-4 h-4 transition-transform duration-300 group-hover:translate-x-1" />
        </span>
      </div>
    </Link>
  );
}

export default function BlogIndex() {
  const allArticles = getPublishedArticles();
  const [activeMacro, setActiveMacro] = useState("Tutti");
  const [page, setPage] = useState(1);

  // Filtrati per macro-categoria (o tutti), sempre in ordine dal più
  // recente — il primo della lista filtrata diventa l'articolo in
  // evidenza, quindi cambia in modo prevedibile insieme al filtro
  // (l'articolo più recente di QUELLA categoria, non un editoriale
  // scelto a mano che andrebbe tenuto aggiornato manualmente).
  const filtered = useMemo(() => {
    if (activeMacro === "Tutti") return allArticles;
    return allArticles.filter((a) => themeForSlug(a.slug).macro === activeMacro);
  }, [allArticles, activeMacro]);

  const featured = filtered[0];
  const rest = filtered.slice(1);
  const totalPages = Math.max(1, Math.ceil(rest.length / PER_PAGE));
  const clampedPage = Math.min(page, totalPages);
  const start = (clampedPage - 1) * PER_PAGE;
  const pageArticles = rest.slice(start, start + PER_PAGE);

  function selectMacro(m) {
    setActiveMacro(m);
    setPage(1);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function goToPage(p) {
    const clamped = Math.min(Math.max(1, p), totalPages);
    setPage(clamped);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <div className="min-h-screen bg-[#F9F9F8] flex flex-col">
      <PageMeta path="/blog" />

      <PublicHeader />

      <main className="flex-1 px-6 py-16 max-w-[1320px] mx-auto w-full">
        <div className="text-center mb-10">
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#B23E00] mb-3">Blog</div>
          <h1 className="font-cabinet font-black text-4xl tracking-tight mb-4">
            Il blog di SalesFly
          </h1>
          <p className="text-[16px] text-[#52525B] max-w-xl mx-auto mb-8">
            Provvigioni, ENASARCO, contratti di agenzia: le risposte alle domande che contano davvero.
          </p>
          <div className="flex items-center justify-center gap-2 flex-wrap">
            {MACROS.map((m) => (
              <button
                key={m}
                onClick={() => selectMacro(m)}
                className={`px-4 py-2 rounded-full text-[12px] font-medium transition-colors ${
                  activeMacro === m
                    ? "bg-[#0A192F] text-white"
                    : "border border-[#E4E4E1] text-[#52525B] hover:border-[#0A192F]"
                }`}
              >
                {m}
              </button>
            ))}
          </div>
        </div>

        {allArticles.length === 0 ? (
          <p className="text-center text-[14px] text-[#6B6B72]">Presto nuovi contenuti.</p>
        ) : (
          <>
            {featured && <FeaturedArticle article={featured} />}

            {pageArticles.length > 0 ? (
              <>
                <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#6B6B72] mb-6">
                  Ultimi articoli
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-14">
                  {pageArticles.map((a, i) => (
                    <ArticleCard key={a.slug} article={a} priority={!featured && i === 0} />
                  ))}
                </div>
              </>
            ) : (
              !featured && (
                <p className="text-center text-[14px] text-[#6B6B72]">Nessun articolo in questa categoria.</p>
              )
            )}

            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 mt-16">
                <button
                  onClick={() => goToPage(clampedPage - 1)}
                  disabled={clampedPage === 1}
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
                      p === clampedPage
                        ? "bg-[#0A192F] text-white"
                        : "border border-[#E4E4E1] text-[#52525B] hover:border-[#0A192F]"
                    }`}
                  >
                    {p}
                  </button>
                ))}
                <button
                  onClick={() => goToPage(clampedPage + 1)}
                  disabled={clampedPage === totalPages}
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

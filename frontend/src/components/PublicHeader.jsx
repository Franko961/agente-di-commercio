import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { PUBLIC_NAV_LINKS } from "@/content/publicNavLinks";

export default function PublicHeader() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  // Stesso effetto scroll-driven della home (Landing.jsx): header bianco
  // in cima alla pagina, che passa a blu scuro semi-trasparente con
  // sfocatura appena si inizia a scorrere — prima presente solo nella
  // home (che ha un proprio header separato per via del contenuto
  // dell'hero), ora anche qui per coerenza visiva sul resto del sito.
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`sticky top-0 z-30 transition-all duration-200 border-b ${
        scrolled
          ? "bg-[rgba(10,25,47,0.92)] backdrop-blur-md border-transparent shadow-[0_8px_30px_rgba(0,0,0,0.08)]"
          : "bg-white border-[#E4E4E1]"
      }`}
    >
      <div className="px-6 py-4 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2" onClick={() => setOpen(false)}>
          <div className={`w-11 h-11 flex items-center justify-center shrink-0 ${scrolled ? "animate-logo-pop" : ""}`}>
            <img src="/logo-mark.webp" alt="SALESFLY" className="w-full h-full object-contain" />
          </div>
          <span className={`font-cabinet font-black text-xl transition-colors duration-200 ${scrolled ? "text-white" : "text-[#0A0A0A]"}`}>
            SALESFLY.
          </span>
        </Link>
        <nav
          className={`hidden md:flex items-center gap-6 text-[14px] font-medium transition-colors duration-200 ${
            scrolled ? "text-white/80" : "text-[#3F3F46]"
          }`}
        >
          {PUBLIC_NAV_LINKS.map((l) => (
            <Link key={l.to} to={l.to} className={`transition-colors ${scrolled ? "hover:text-white" : "hover:text-[#0A192F]"}`}>{l.label}</Link>
          ))}
        </nav>
        <div className="flex items-center gap-1.5 sm:gap-3">
          <button
            onClick={() => navigate("/login")}
            className={`hidden sm:inline-block text-[13px] transition-colors duration-200 ${
              scrolled ? "text-white/70 hover:text-white" : "text-[#52525B] hover:text-[#0A192F]"
            }`}
          >
            Accedi
          </button>
          <button
            onClick={() => navigate("/richiedi-demo")}
            className={`px-3 py-1.5 sm:px-4 sm:py-2 rounded-md text-[12px] sm:text-[13px] font-medium whitespace-nowrap transition-colors duration-200 ${
              scrolled ? "bg-white text-[#0A192F] hover:bg-white/90" : "bg-[#0A192F] text-white hover:bg-[#172A45]"
            }`}
          >
            Inizia gratis
          </button>
          <button
            onClick={() => setOpen((v) => !v)}
            data-testid="mobile-nav-toggle"
            aria-label="Menu"
            className={`md:hidden p-1.5 shrink-0 transition-colors duration-200 ${scrolled ? "text-white" : "text-[#0A192F]"}`}
          >
            {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>
      {open && (
        <nav className="md:hidden border-t border-[#E4E4E1] px-6 py-2 flex flex-col bg-white">
          {PUBLIC_NAV_LINKS.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              onClick={() => setOpen(false)}
              className="py-3 text-[14px] font-medium text-[#3F3F46] border-b border-[#F3F3F1] last:border-b-0"
            >
              {l.label}
            </Link>
          ))}
          <Link
            to="/login"
            onClick={() => setOpen(false)}
            className="py-3 text-[14px] font-medium text-[#3F3F46]"
          >
            Accedi
          </Link>
        </nav>
      )}
    </header>
  );
}

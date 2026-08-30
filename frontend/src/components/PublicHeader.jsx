import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { PUBLIC_NAV_LINKS } from "@/content/publicNavLinks";

export default function PublicHeader() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  return (
    <header className="border-b border-[#E4E4E1] bg-white">
      <div className="px-6 py-4 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2" onClick={() => setOpen(false)}>
          <div className="w-11 h-11 flex items-center justify-center shrink-0">
            <img src="/logo-mark.webp" alt="SALESFLY" className="w-full h-full object-contain" />
          </div>
          <span className="font-cabinet font-black text-xl">SALESFLY.</span>
        </Link>
        <nav className="hidden md:flex items-center gap-6 text-[14px] font-medium text-[#3F3F46]">
          {PUBLIC_NAV_LINKS.map((l) => (
            <Link key={l.to} to={l.to} className="hover:text-[#0A192F] transition-colors">{l.label}</Link>
          ))}
        </nav>
        <div className="flex items-center gap-1.5 sm:gap-3">
          <button onClick={() => navigate("/login")} className="hidden sm:inline-block text-[13px] text-[#52525B] hover:text-[#0A192F]">
            Accedi
          </button>
          <button
            onClick={() => navigate("/richiedi-demo")}
            className="px-3 py-1.5 sm:px-4 sm:py-2 bg-[#0A192F] text-white rounded-md text-[12px] sm:text-[13px] font-medium hover:bg-[#172A45] transition-colors whitespace-nowrap"
          >
            Inizia gratis
          </button>
          <button
            onClick={() => setOpen((v) => !v)}
            data-testid="mobile-nav-toggle"
            aria-label="Menu"
            className="md:hidden p-1.5 text-[#0A192F] shrink-0"
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

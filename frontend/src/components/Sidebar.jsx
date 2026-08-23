import { NavLink, Link, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, Users, KanbanSquare, CalendarDays, Map, FileText, ShoppingCart,
  Coins, Building2, Package, Folder, Sparkles, Zap, LogOut, ArrowLeftRight, ShieldCheck, CreditCard, Settings as SettingsIcon, Receipt,
  HelpCircle, IdCard, Truck, Clock,
} from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { useMandante } from "../contexts/MandanteContext";
import NotificationBell from "./NotificationBell";

// "module" collega la voce a core.security.MODULE_KEYS lato backend: se
// presente nell'array disabled_modules dell'utente (impostato dall'admin,
// vedi Admin.jsx), la voce sparisce dal menu. Dashboard e Impostazioni
// non hanno un module — restano sempre visibili, altrimenti un utente
// con tutto disattivato non avrebbe più modo di navigare l'app.
const navItems = [
  { to: "/app", label: "Dashboard", icon: LayoutDashboard },
  { to: "/app/clienti", label: "Clienti", icon: Users, module: "clienti" },
  { to: "/app/lead", label: "Lead & Pipeline", icon: KanbanSquare, module: "lead" },
  { to: "/app/agenda", label: "Agenda", icon: CalendarDays, module: "agenda" },
  { to: "/app/mappa", label: "Mappa", icon: Map, module: "mappa" },
  { to: "/app/offerte", label: "Offerte", icon: FileText, module: "offerte" },
  { to: "/app/ordini", label: "Ordini", icon: ShoppingCart, module: "ordini" },
  { to: "/app/provvigioni", label: "Provvigioni", icon: Coins, module: "provvigioni" },
  { to: "/app/spese", label: "Spese", icon: Receipt, module: "spese" },
  { to: "/app/mandanti", label: "Mandanti", icon: Building2, module: "mandanti" },
  { to: "/app/prodotti", label: "Prodotti & Listini", icon: Package, module: "prodotti" },
  { to: "/app/documenti", label: "Documenti", icon: Folder, module: "documenti" },
  { to: "/app/automazioni", label: "Automazioni", icon: Zap, module: "automazioni" },
  { to: "/app/ai", label: "Assistente AI", icon: Sparkles, module: "ai" },
  // extra: true = modulo verticale spento di default (vedi ModuleGuard.jsx
  // e core.security.EXTRA_MODULE_KEYS), non i normali moduli CRM sopra.
  { to: "/app/personale", label: "Personale", icon: IdCard, module: "personale", extra: true },
  { to: "/app/presenze", label: "Presenze", icon: Clock, module: "personale", extra: true },
  { to: "/app/flotta", label: "Flotta", icon: Truck, module: "flotta", extra: true },
  { to: "/app/impostazioni", label: "Impostazioni", icon: SettingsIcon },
];

export default function Sidebar({ collapsed, onToggle }) {
  const { user, logout } = useAuth();
  const isAdmin = user?.role === "admin";
  const disabledModules = user?.disabled_modules || [];
  const enabledExtraModules = user?.enabled_extra_modules || [];
  const { mandanti, activeMandante, setActiveMandante } = useMandante();
  const navigate = useNavigate();

  const handleLogout = async () => { await logout(); navigate("/login"); };
  const active = mandanti.find(m => m.id === activeMandante);

  return (
    <aside
      data-testid="desktop-sidebar"
      className="hidden md:flex flex-col h-screen sticky top-0 bg-white border-r border-[#E4E4E1] w-[260px] shrink-0"
    >
      {/* Brand */}
      <div className="px-6 py-5 border-b border-[#E4E4E1] flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-9 h-9 flex items-center justify-center shrink-0">
            <img src="/logo-mark.png" alt="SALESFLY" className="w-full h-full object-contain" />
          </div>
          <div className="min-w-0">
            <div className="font-cabinet font-black text-[15px] leading-none">SALESFLY.</div>
            <div className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72] mt-0.5">gestionale</div>
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <Link
            to="/app/aiuto"
            data-testid="help-center-link"
            title="Centro assistenza"
            aria-label="Centro assistenza"
            className="w-8 h-8 flex items-center justify-center rounded-md text-[#6B6B72] hover:text-[#0A192F] hover:bg-[#F3F3F1] transition-colors"
          >
            <HelpCircle className="w-4 h-4" strokeWidth={1.75} />
          </Link>
          <NotificationBell />
        </div>
      </div>

      {/* Mandante switcher */}
      <div className="px-4 py-4 border-b border-[#E4E4E1]">
        <div className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72] mb-2">Mandante attivo</div>
        <button
          data-testid="mandante-switcher"
          onClick={() => {
            const ids = ["all", ...mandanti.map(m => m.id)];
            const next = ids[(ids.indexOf(activeMandante) + 1) % ids.length];
            setActiveMandante(next);
          }}
          className="w-full flex items-center justify-between px-3 py-2 border border-[#E4E4E1] hover:border-[#0A192F] rounded-md transition-all duration-200"
        >
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-2 h-2 rounded-full shrink-0" style={{ background: active?.brand_color || "#B23E00" }} />
            <span className="font-medium text-[13px] truncate">{active?.name || "Tutti i mandanti"}</span>
          </div>
          <ArrowLeftRight className="w-3.5 h-3.5 text-[#6B6B72]" />
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-3">
        {navItems.filter(({ module, extra }) => {
          if (!module) return true;
          return extra ? enabledExtraModules.includes(module) : !disabledModules.includes(module);
        }).map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/app"}
            data-testid={`nav-${to.replace("/", "") || "dashboard"}`}
            className={({ isActive }) =>
              `flex items-center gap-3 px-6 py-2.5 text-[13px] transition-all duration-150 border-l-2 ${
                isActive
                  ? "border-[#B23E00] bg-[#F3F3F1] text-[#0A0A0A] font-semibold"
                  : "border-transparent text-[#52525B] hover:bg-[#F9F9F8] hover:text-[#0A0A0A]"
              }`
            }
          >
            <Icon className="w-4 h-4" strokeWidth={1.75} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      {/* User */}
      <div className="p-4 border-t border-[#E4E4E1]">
        <div className="flex items-center gap-3 mb-3">
          {/* FF5A00 originale, non B23E00: qui è testo arancione su sfondo
          blu scuro, non su chiaro — la versione scurita ridurrebbe il
          contrasto invece di migliorarlo (verificato: 5.63:1 con
          l'originale contro 3.0:1 con la versione scurita). */}
          <div className="w-9 h-9 rounded-full bg-[#0A192F] text-[#FF5A00] flex items-center justify-center font-cabinet font-bold text-sm">
            {user?.name?.[0] || "A"}
          </div>
          <div className="min-w-0 flex-1">
            <div className="font-medium text-[13px] truncate">{user?.name}</div>
            <div className="font-mono text-[10px] text-[#6B6B72] truncate">{user?.email}</div>
          </div>
        </div>
        {isAdmin && (
          <NavLink to="/app/admin"
            className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-[#B23E00] text-white rounded-md text-[12px] font-medium mb-2"
          >
            <ShieldCheck className="w-3.5 h-3.5" /> Admin
          </NavLink>
        )}
        <Link to="/app/abbonamento" className="mx-1 mb-2 flex items-center justify-between px-3 py-2 bg-[#F3F3F1] hover:bg-[#E4E4E1] rounded-md transition-colors">
          <span className="font-mono text-[10px] uppercase tracking-widest text-[#52525B]">Abbonamento</span>
          <span className="font-mono text-[9px] uppercase tracking-widest px-1.5 py-0.5 rounded"
            style={{ background: user?.plan === "pro" ? "#B23E0020" : "#0A192F15", color: user?.plan === "pro" ? "#B23E00" : "#0A192F" }}>
            {user?.plan || "base"}
          </span>
        </Link>
        <button
          data-testid="logout-button"
          onClick={handleLogout}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 border border-[#E4E4E1] hover:border-[#DC2626] hover:text-[#DC2626] rounded-md text-[12px] font-medium transition-all duration-200"
        >
          <LogOut className="w-3.5 h-3.5" />
          Esci
        </button>
      </div>
    </aside>
  );
}

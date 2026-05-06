import { NavLink, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, Users, KanbanSquare, CalendarDays, Map, FileText,
  Coins, Building2, Package, Folder, Sparkles, Zap, LogOut, ArrowLeftRight
} from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { useMandante } from "../contexts/MandanteContext";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/clienti", label: "Clienti", icon: Users },
  { to: "/lead", label: "Lead & Pipeline", icon: KanbanSquare },
  { to: "/agenda", label: "Agenda", icon: CalendarDays },
  { to: "/mappa", label: "Mappa", icon: Map },
  { to: "/offerte", label: "Offerte", icon: FileText },
  { to: "/provvigioni", label: "Provvigioni", icon: Coins },
  { to: "/mandanti", label: "Mandanti", icon: Building2 },
  { to: "/prodotti", label: "Prodotti & Listini", icon: Package },
  { to: "/documenti", label: "Documenti", icon: Folder },
  { to: "/automazioni", label: "Automazioni", icon: Zap },
  { to: "/ai", label: "Assistente AI", icon: Sparkles },
];

export default function Sidebar({ collapsed, onToggle }) {
  const { user, logout } = useAuth();
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
      <div className="px-6 py-5 border-b border-[#E4E4E1]">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-[#0A192F] flex items-center justify-center rounded-sm">
            <span className="text-[#FF5A00] font-cabinet font-black text-sm">A</span>
          </div>
          <div>
            <div className="font-cabinet font-black text-[15px] leading-none">AGENTE.</div>
            <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] mt-0.5">gestionale</div>
          </div>
        </div>
      </div>

      {/* Mandante switcher */}
      <div className="px-4 py-4 border-b border-[#E4E4E1]">
        <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] mb-2">Mandante attivo</div>
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
            <div className="w-2 h-2 rounded-full shrink-0" style={{ background: active?.brand_color || "#FF5A00" }} />
            <span className="font-medium text-[13px] truncate">{active?.name || "Tutti i mandanti"}</span>
          </div>
          <ArrowLeftRight className="w-3.5 h-3.5 text-[#A1A1AA]" />
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-3">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            data-testid={`nav-${to.replace("/", "") || "dashboard"}`}
            className={({ isActive }) =>
              `flex items-center gap-3 px-6 py-2.5 text-[13px] transition-all duration-150 border-l-2 ${
                isActive
                  ? "border-[#FF5A00] bg-[#F3F3F1] text-[#0A0A0A] font-semibold"
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
          <div className="w-9 h-9 rounded-full bg-[#0A192F] text-[#FF5A00] flex items-center justify-center font-cabinet font-bold text-sm">
            {user?.name?.[0] || "A"}
          </div>
          <div className="min-w-0 flex-1">
            <div className="font-medium text-[13px] truncate">{user?.name}</div>
            <div className="font-mono text-[10px] text-[#A1A1AA] truncate">{user?.email}</div>
          </div>
        </div>
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

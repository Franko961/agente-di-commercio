import { useState } from "react";
import { Outlet, useLocation, NavLink, useNavigate, Link } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import Sidebar from "./Sidebar";
import MobileNav from "./MobileNav";
import VoiceAssistant from "./VoiceAssistant";
import NotificationBell from "./NotificationBell";
import { Sheet, SheetContent } from "./ui/sheet";
import { useAuth } from "../contexts/AuthContext";
import { useMandante } from "../contexts/MandanteContext";
import {
  LayoutDashboard, Users, KanbanSquare, CalendarDays, Map, FileText, ShoppingCart,
  Coins, Building2, Package, Folder, Sparkles, Zap, LogOut, CreditCard, ShieldCheck, Receipt,
  HelpCircle,
} from "lucide-react";

const fullNav = [
  { to: "/app", label: "Dashboard", icon: LayoutDashboard },
  { to: "/app/clienti", label: "Clienti", icon: Users },
  { to: "/app/lead", label: "Lead & Pipeline", icon: KanbanSquare },
  { to: "/app/agenda", label: "Agenda", icon: CalendarDays },
  { to: "/app/mappa", label: "Mappa", icon: Map },
  { to: "/app/offerte", label: "Offerte", icon: FileText },
  { to: "/app/ordini", label: "Ordini", icon: ShoppingCart },
  { to: "/app/provvigioni", label: "Provvigioni", icon: Coins },
  { to: "/app/spese", label: "Spese", icon: Receipt },
  { to: "/app/mandanti", label: "Mandanti", icon: Building2 },
  { to: "/app/prodotti", label: "Prodotti & Listini", icon: Package },
  { to: "/app/documenti", label: "Documenti", icon: Folder },
  { to: "/app/automazioni", label: "Automazioni", icon: Zap },
  { to: "/app/ai", label: "Assistente AI", icon: Sparkles },
  { to: "/app/abbonamento", label: "Abbonamento", icon: CreditCard },
];

export default function Layout() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { user, logout } = useAuth();
  const isAdmin = user?.role === "admin";
  const { mandanti, activeMandante, setActiveMandante } = useMandante();
  const location = useLocation();
  const navigate = useNavigate();
  const active = mandanti.find(m => m.id === activeMandante);

  const titles = {
    "/app": "Dashboard", "/app/clienti": "Clienti", "/app/lead": "Pipeline Lead",
    "/app/agenda": "Agenda", "/app/mappa": "Mappa Clienti", "/app/offerte": "Offerte",
    "/app/ordini": "Ordini",
    "/app/provvigioni": "Provvigioni", "/app/mandanti": "Mandanti",
    "/app/spese": "Spese",
    "/app/prodotti": "Prodotti & Listini", "/app/documenti": "Documenti",
    "/app/automazioni": "Automazioni", "/app/ai": "Assistente AI",
    "/app/aiuto": "Centro assistenza",
  };
  const baseTitle = Object.entries(titles).find(([k]) => location.pathname === k || (k !== "/app" && location.pathname.startsWith(k)))?.[1] || "";

  return (
    <div className="flex min-h-screen bg-[#F9F9F8]">
      <Helmet>
        {/* Le pagine dell'app sono private: non devono essere indicizzate da Google */}
        <meta name="robots" content="noindex, nofollow" />
      </Helmet>
      <Sidebar />
      <main className="flex-1 min-w-0 pb-20 md:pb-0">
        {/* Mobile top header */}
        <header className="md:hidden sticky top-0 z-30 bg-white border-b border-[#E4E4E1] px-4 py-3 flex items-center justify-between">
          <div>
            <div className="font-cabinet font-black text-[15px] leading-none">{baseTitle}</div>
            <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] mt-1 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: active?.brand_color || "#FF5A00" }} />
              {active?.name || "Tutti i mandanti"}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              data-testid="mobile-mandante-switcher"
              onClick={() => {
                const ids = ["all", ...mandanti.map(m => m.id)];
                const next = ids[(ids.indexOf(activeMandante) + 1) % ids.length];
                setActiveMandante(next);
              }}
              className="font-mono text-[10px] uppercase tracking-widest text-[#FF5A00] border border-[#E4E4E1] px-2 py-1.5 rounded-md"
            >
              cambia
            </button>
            <Link
              to="/app/aiuto"
              data-testid="mobile-help-center-link"
              className="w-8 h-8 flex items-center justify-center rounded-md text-[#A1A1AA] hover:text-[#0A192F] hover:bg-[#F3F3F1] transition-colors"
            >
              <HelpCircle className="w-4 h-4" strokeWidth={1.75} />
            </Link>
            <NotificationBell />
          </div>
        </header>

        <Outlet />

        <VoiceAssistant />
        <MobileNav onMenu={() => setDrawerOpen(true)} />

        <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
          <SheetContent side="right" className="w-[280px] p-0 bg-white">
            <div className="flex flex-col h-full">
              <div className="px-5 py-4 border-b border-[#E4E4E1]">
                <div className="font-cabinet font-black text-[15px]">Menu completo</div>
                <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] mt-1">{user?.name}</div>
              </div>
              <nav className="flex-1 overflow-y-auto py-2">
                {fullNav.map(({ to, label, icon: Icon }) => (
                  <NavLink
                    key={to}
                    to={to}
                    end={to === "/app"}
                    onClick={() => setDrawerOpen(false)}
                    data-testid={`drawer-nav-${to.replace("/", "") || "dashboard"}`}
                    className={({ isActive }) =>
                      `flex items-center gap-3 px-5 py-3 text-sm border-l-2 ${
                        isActive
                          ? "border-[#FF5A00] bg-[#F3F3F1] text-[#0A0A0A] font-semibold"
                          : "border-transparent text-[#52525B]"
                      }`
                    }
                  >
                    <Icon className="w-4 h-4" strokeWidth={1.75} />
                    {label}
                  </NavLink>
                ))}
              </nav>
              {isAdmin && (
                <NavLink to="/app/admin" onClick={() => setDrawerOpen(false)} className="mx-4 mb-1 flex items-center gap-2 px-3 py-2.5 bg-[#FF5A00] text-white rounded-md text-sm font-medium">
                  <ShieldCheck className="w-4 h-4" /> Admin
                </NavLink>
              )}
              <button
                data-testid="drawer-logout"
                onClick={async () => { await logout(); navigate("/login"); }}
                className="m-4 flex items-center justify-center gap-2 px-3 py-2.5 border border-[#E4E4E1] rounded-md text-sm font-medium"
              >
                <LogOut className="w-4 h-4" /> Esci
              </button>
            </div>
          </SheetContent>
        </Sheet>
      </main>
    </div>
  );
}

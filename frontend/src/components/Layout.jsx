import { useState } from "react";
import { Outlet, useLocation, NavLink, useNavigate, Link } from "react-router-dom";
import Sidebar from "./Sidebar";
import MobileNav from "./MobileNav";
import VoiceAssistant from "./VoiceAssistant";
import NotificationBell from "./NotificationBell";
import OnboardingTour from "./OnboardingTour";
import { Sheet, SheetContent } from "./ui/sheet";
import { useAuth } from "../contexts/AuthContext";
import { useMandante } from "../contexts/MandanteContext";
import {
  LayoutDashboard, Users, KanbanSquare, CalendarDays, Map, FileText, ShoppingCart,
  Coins, Building2, Package, Folder, Sparkles, Zap, LogOut, CreditCard, ShieldCheck, Receipt,
  HelpCircle, Eye, Pencil, IdCard, Truck, Clock,
} from "lucide-react";

// Banner sempre visibile mentre un admin sta usando l'account di un altro
// utente (vedi Admin.jsx "Visualizza come utente"/"Accedi e modifica" e
// AuthContext.exitImpersonation): senza un avviso inequivocabile, sarebbe
// facile dimenticare in quale account ci si trova mentre si naviga il
// gestionale altrui, con il rischio di scambiare per propri dati che non lo
// sono. Il testo/icona distinguono le due modalità (vedi
// core.security.forbid_demo_write per come "view" blocca le scritture lato
// backend, non solo qui a livello di avviso).
function ImpersonationBanner({ email, mode, onExit }) {
  const isEdit = mode === "edit";
  const Icon = isEdit ? Pencil : Eye;
  return (
    <div className="bg-[#DC2626] text-white text-[13px] font-medium py-2 px-4 flex items-center justify-center gap-3 text-center flex-wrap">
      <Icon className="w-3.5 h-3.5 shrink-0" />
      <span>
        {isEdit
          ? <>Stai <strong>modificando</strong> l'account di <strong>{email}</strong> come amministratore.</>
          : <>Stai visualizzando l'account di <strong>{email}</strong> in <strong>sola lettura</strong>.</>}
      </span>
      <button onClick={onExit} data-testid="exit-impersonation-button" className="underline font-bold shrink-0">
        Esci dall'account
      </button>
    </div>
  );
}

// "module" collega la voce a core.security.MODULE_KEYS lato backend, come
// in Sidebar.jsx — stesso motivo, stesso elenco (qui duplicato perché il
// menu a comparsa mobile mostra anche "Abbonamento", assente dalla sidebar
// desktop dove ha già una sua scorciatoia dedicata in fondo).
const fullNav = [
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
  { to: "/app/personale", label: "Personale", icon: IdCard, module: "personale", extra: true },
  { to: "/app/presenze", label: "Presenze", icon: Clock, module: "personale", extra: true },
  { to: "/app/flotta", label: "Flotta", icon: Truck, module: "flotta", extra: true },
  { to: "/app/abbonamento", label: "Abbonamento", icon: CreditCard },
];

export default function Layout() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { user, logout, exitImpersonation } = useAuth();
  const isAdmin = user?.role === "admin";
  const disabledModules = user?.disabled_modules || [];
  const enabledExtraModules = user?.enabled_extra_modules || [];
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
    "/app/automazioni": "Automazioni", "/app/ai": "Assistente AI", "/app/personale": "Personale",
    "/app/presenze": "Presenze",
    "/app/flotta": "Flotta",
    "/app/aiuto": "Centro assistenza",
  };
  const baseTitle = Object.entries(titles).find(([k]) => location.pathname === k || (k !== "/app" && location.pathname.startsWith(k)))?.[1] || "";

  return (
    <>
      {user?.impersonated_by && <ImpersonationBanner email={user.email} mode={user.impersonation_mode} onExit={exitImpersonation} />}
      <div className="flex min-h-screen bg-[#F9F9F8]">
      {/* Le pagine dell'app sono private: non devono essere indicizzate da Google */}
      <meta name="robots" content="noindex, nofollow" />
      {user && !user.onboarding_seen && <OnboardingTour />}
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

        {!disabledModules.includes("ai") && <VoiceAssistant />}
        <MobileNav onMenu={() => setDrawerOpen(true)} />

        <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
          <SheetContent side="right" className="w-[280px] p-0 bg-white">
            <div className="flex flex-col h-full">
              <div className="px-5 py-4 border-b border-[#E4E4E1]">
                <div className="font-cabinet font-black text-[15px]">Menu completo</div>
                <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] mt-1">{user?.name}</div>
              </div>
              <nav className="flex-1 overflow-y-auto py-2">
                {fullNav.filter(({ module, extra }) => {
                  if (!module) return true;
                  return extra ? enabledExtraModules.includes(module) : !disabledModules.includes(module);
                }).map(({ to, label, icon: Icon }) => (
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
    </>
  );
}

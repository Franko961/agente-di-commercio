import { NavLink } from "react-router-dom";
import { LayoutDashboard, Users, CalendarDays, FileText, Menu } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";

const items = [
  { to: "/app", label: "Home", icon: LayoutDashboard },
  { to: "/app/clienti", label: "Clienti", icon: Users, module: "clienti" },
  { to: "/app/agenda", label: "Agenda", icon: CalendarDays, module: "agenda" },
  { to: "/app/offerte", label: "Offerte", icon: FileText, module: "offerte" },
];

export default function MobileNav({ onMenu }) {
  const { user } = useAuth();
  const disabledModules = user?.disabled_modules || [];
  // flex invece di una grid a colonne fisse: il numero di voci varia in
  // base ai moduli disattivati, una grid-cols-N statica non si adatterebbe.
  const visible = items.filter(({ module }) => !module || !disabledModules.includes(module));

  return (
    <nav
      data-testid="mobile-bottom-nav"
      className="md:hidden fixed bottom-0 inset-x-0 bg-white border-t border-[#E4E4E1] z-40 flex"
    >
      {visible.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === "/app"}
          data-testid={`mobile-nav-${to.replace("/", "") || "home"}`}
          className={({ isActive }) =>
            `flex-1 flex flex-col items-center justify-center gap-1 py-2.5 transition-colors duration-150 ${
              isActive ? "text-[#0A192F]" : "text-[#6B6B72]"
            }`
          }
        >
          {({ isActive }) => (
            <>
              <Icon className="w-5 h-5" strokeWidth={1.75} />
              <span className="text-[10px] font-medium tracking-wide">{label}</span>
              {isActive && <span className="absolute bottom-0 w-8 h-0.5 bg-[#B23E00]" />}
            </>
          )}
        </NavLink>
      ))}
      <button
        onClick={onMenu}
        data-testid="mobile-menu-button"
        className="flex-1 flex flex-col items-center justify-center gap-1 py-2.5 text-[#6B6B72]"
      >
        <Menu className="w-5 h-5" strokeWidth={1.75} />
        <span className="text-[10px] font-medium tracking-wide">Menu</span>
      </button>
    </nav>
  );
}

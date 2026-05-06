import { NavLink } from "react-router-dom";
import { LayoutDashboard, Users, CalendarDays, FileText, Menu } from "lucide-react";

const items = [
  { to: "/", label: "Home", icon: LayoutDashboard },
  { to: "/clienti", label: "Clienti", icon: Users },
  { to: "/agenda", label: "Agenda", icon: CalendarDays },
  { to: "/offerte", label: "Offerte", icon: FileText },
];

export default function MobileNav({ onMenu }) {
  return (
    <nav
      data-testid="mobile-bottom-nav"
      className="md:hidden fixed bottom-0 inset-x-0 bg-white border-t border-[#E4E4E1] z-40 grid grid-cols-5"
    >
      {items.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === "/"}
          data-testid={`mobile-nav-${to.replace("/", "") || "home"}`}
          className={({ isActive }) =>
            `flex flex-col items-center justify-center gap-1 py-2.5 transition-colors duration-150 ${
              isActive ? "text-[#0A192F]" : "text-[#A1A1AA]"
            }`
          }
        >
          {({ isActive }) => (
            <>
              <Icon className="w-5 h-5" strokeWidth={1.75} />
              <span className="text-[10px] font-medium tracking-wide">{label}</span>
              {isActive && <span className="absolute bottom-0 w-8 h-0.5 bg-[#FF5A00]" />}
            </>
          )}
        </NavLink>
      ))}
      <button
        onClick={onMenu}
        data-testid="mobile-menu-button"
        className="flex flex-col items-center justify-center gap-1 py-2.5 text-[#A1A1AA]"
      >
        <Menu className="w-5 h-5" strokeWidth={1.75} />
        <span className="text-[10px] font-medium tracking-wide">Menu</span>
      </button>
    </nav>
  );
}

import { Navigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

// Riporta a /app se l'utente raggiunge direttamente (URL diretto, link
// salvato) la pagina di un modulo non disponibile per il suo account — la
// voce di menu è già nascosta (vedi Sidebar.jsx/Layout.jsx), questo copre
// il caso in cui l'URL viene comunque raggiunto. Il vero blocco è lato
// backend (core.security.require_module): questo è solo per non mostrare
// una pagina che poi fallirebbe ogni chiamata API.
//
// extra=true per i moduli verticali (Personale, Flotta — vedi
// EXTRA_MODULE_KEYS lato backend): spenti finché non esplicitamente
// attivati (enabled_extra_modules), logica opposta ai moduli "core"
// (Clienti, Provvigioni, ecc.), attivi finché non disattivati
// (disabled_modules).
export default function ModuleGuard({ module, extra = false, children }) {
  const { user } = useAuth();
  const blocked = extra
    ? !(user?.enabled_extra_modules || []).includes(module)
    : (user?.disabled_modules || []).includes(module);
  if (blocked) {
    return <Navigate to="/app" replace />;
  }
  return children;
}

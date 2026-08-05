import { Navigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

// Riporta a /app se l'utente raggiunge direttamente (URL diretto, link
// salvato) la pagina di un modulo che l'admin ha disattivato per il suo
// account — la voce di menu è già nascosta (vedi Sidebar.jsx/Layout.jsx),
// questo copre il caso in cui l'URL viene comunque raggiunto. Il vero
// blocco è lato backend (core.security.require_module): questo è solo
// per non mostrare una pagina che poi fallirebbe ogni chiamata API.
export default function ModuleGuard({ module, children }) {
  const { user } = useAuth();
  if ((user?.disabled_modules || []).includes(module)) {
    return <Navigate to="/app" replace />;
  }
  return children;
}

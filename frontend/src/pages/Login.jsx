import { useState, useEffect } from "react";
import { useNavigate, Navigate, useSearchParams, Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";
import { Eye, EyeOff } from "lucide-react";

export default function Login() {
  const { user, login, register } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [mode, setMode] = useState(searchParams.get("register") !== null ? "register" : "login");
  const [plan, setPlan] = useState(searchParams.get("plan") || "base");
  const [email, setEmail] = useState(mode === "login" ? "agente@demo.it" : "");
  const [password, setPassword] = useState(mode === "login" ? "demo1234" : "");
  const [name, setName] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  // Se arriva da /register?plan=pro apri direttamente registrazione
  useEffect(() => {
    if (searchParams.get("plan") || searchParams.get("register") !== null) {
      setMode("register");
      setEmail("");
      setPassword("");
    }
  }, []);

  if (user) return <Navigate to="/" replace />;

  const switchMode = (next) => {
    setMode(next);
    setError("");
    if (next === "register") { setEmail(""); setPassword(""); }
    else { setEmail("agente@demo.it"); setPassword("demo1234"); setName(""); }
  };

  const formatError = (err) => {
    const detail = err?.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((e) => {
      const field = e?.loc?.[e.loc.length - 1];
      const msg = e?.msg || "valore non valido";
      if (field === "email") return "Email non valida";
      if (field === "password") return "Password non valida";
      return `${field}: ${msg}`;
    }).join(" · ");
    if (!err?.response) return "Connessione al server fallita. Verifica internet e riprova.";
    return `Errore ${err.response.status || ""}: riprova tra poco`;
  };

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (mode === "register") {
      if (!name.trim()) { setError("Inserisci nome e cognome"); return; }
      if (password.length < 6) { setError("La password deve avere almeno 6 caratteri"); return; }
    }
    setBusy(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(name.trim(), email.trim().toLowerCase(), password, plan);
      toast.success(mode === "login" ? "Accesso effettuato" : "Account creato — benvenuto!");
      navigate("/");
    } catch (err) {
      const msg = formatError(err);
      setError(msg);
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-[1fr_1.2fr] bg-[#F9F9F8]">
      {/* Left: form */}
      <div className="flex flex-col justify-between p-6 sm:p-10 lg:p-14">
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-[#0A192F] flex items-center justify-center rounded-sm">
              <span className="text-[#FF5A00] font-cabinet font-black text-base">A</span>
            </div>
            <div>
              <div className="font-cabinet font-black text-[16px] leading-none">AGENTE.</div>
              <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] mt-0.5">gestionale per agenti di commercio</div>
            </div>
          </div>
          <Link to="/prezzi" className="text-[12px] font-mono uppercase tracking-widest text-[#FF5A00] hover:underline hidden sm:block">
            Piani & Prezzi →
          </Link>
        </header>

        <div className="flex-1 flex items-center">
          <div className="w-full max-w-md fade-up">
            <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-[#FF5A00] mb-3">
              {mode === "login" ? "01 — Accesso" : "01 — Registrazione"}
            </div>
            <h1 className="font-cabinet font-black text-4xl sm:text-5xl tracking-tight text-[#0A0A0A] mb-3">
              {mode === "login" ? "Bentornato in zona." : "Nuovo agente."}
            </h1>
            <p className="text-[14px] text-[#52525B] leading-relaxed mb-8 max-w-sm">
              {mode === "login"
                ? "Accedi al tuo cruscotto. Gestisci clienti, provvigioni e visite in un unico posto."
                : "14 giorni di prova gratuita. Nessuna carta richiesta."}
            </p>

            {/* Selezione piano in registrazione */}
            {mode === "register" && (
              <div className="mb-5">
                <div className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] mb-2">Piano scelto</div>
                <div className="grid grid-cols-2 gap-2">
                  {["base", "pro"].map(p => (
                    <button key={p} type="button" onClick={() => setPlan(p)}
                      className={`py-2.5 px-3 rounded-md border-2 text-[13px] font-medium transition-colors ${plan === p ? "border-[#FF5A00] bg-[#FF5A00] text-white" : "border-[#E4E4E1] text-[#52525B]"}`}>
                      {p === "base" ? "Base — €6/mese" : "Pro — €11/mese"}
                    </button>
                  ))}
                </div>
                <Link to="/prezzi" className="text-[11px] text-[#A1A1AA] mt-1.5 block hover:text-[#FF5A00]">
                  Confronta i piani →
                </Link>
              </div>
            )}

            <form onSubmit={submit} className="space-y-4">
              {mode === "register" && (
                <div>
                  <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Nome completo</label>
                  <input data-testid="register-name-input" type="text" required value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2.5 text-[14px] focus:outline-none focus:border-[#0A192F]" />
                </div>
              )}
              <div>
                <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Email</label>
                <input data-testid="login-email-input" type="email" required value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2.5 text-[14px] focus:outline-none focus:border-[#0A192F]" />
              </div>
              <div>
                <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Password</label>
                <div className="relative">
                  <input data-testid="login-password-input" type={show ? "text" : "password"} required value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2.5 text-[14px] pr-10 focus:outline-none focus:border-[#0A192F]" />
                  <button type="button" onClick={() => setShow(!show)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[#A1A1AA]">
                    {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <button data-testid="login-submit-button" type="submit" disabled={busy}
                className="w-full bg-[#0A192F] hover:bg-[#172A45] text-white font-medium py-3 rounded-md transition-all flex items-center justify-center gap-2 disabled:opacity-50">
                {busy ? "Attendere…" : mode === "login" ? "Accedi al gestionale" : "Inizia prova gratuita"}
                <span className="text-[#FF5A00]">→</span>
              </button>

              {error && (
                <div data-testid="auth-error" className="bg-[#DC2626]/5 border border-[#DC2626]/30 rounded-md p-3 text-[12px] text-[#DC2626] font-medium">
                  {error}
                </div>
              )}
            </form>

            <div className="mt-6 text-[13px] text-[#52525B]">
              {mode === "login" ? "Non hai un account? " : "Hai già un account? "}
              <button data-testid="toggle-auth-mode" onClick={() => switchMode(mode === "login" ? "register" : "login")}
                className="text-[#0A192F] font-semibold underline underline-offset-4 decoration-[#FF5A00]">
                {mode === "login" ? "Inizia gratis" : "Accedi"}
              </button>
            </div>

            {mode === "login" && (
              <div className="mt-8 pt-6 border-t border-[#E4E4E1]">
                <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] mb-2">Demo</div>
                <div className="font-mono text-[12px] text-[#52525B]">agente@demo.it / demo1234</div>
              </div>
            )}
          </div>
        </div>

        <footer className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA]">
          © 2026 AGENTE — Made in Italia
        </footer>
      </div>

      {/* Right: visual */}
      <div className="hidden lg:block relative">
        <div className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: 'url(https://images.unsplash.com/photo-1649585067848-50efdd21835b?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzd8MHwxfHNlYXJjaHwxfHxpdGFsaWFuJTIwYnVzaW5lc3MlMjBtaWxhbiUyMHN0cmVldCUyMGx1eHVyeSUyMGFyY2hpdGVjdHVyZXxlbnwwfHx8fDE3NzgwNzE2MDB8MA&ixlib=rb-4.1.0&q=85)' }} />
        <div className="absolute inset-0 bg-gradient-to-tr from-[#F9F9F8]/90 via-[#F9F9F8]/40 to-transparent" />
        <div className="relative h-full flex flex-col justify-end p-10">
          <div className="bg-white border border-[#E4E4E1] rounded-md p-6 max-w-md">
            <div className="font-mono text-[10px] uppercase tracking-widest text-[#FF5A00] mb-3">In evidenza · oggi</div>
            <div className="font-cabinet font-black text-2xl mb-3">"7 clienti da visitare in zona Lombardia."</div>
            <div className="text-[13px] text-[#52525B] mb-4">
              L'assistente AI individua le opportunità più calde in base a storico ordini, ultimo contatto e potenziale.
            </div>
            <div className="grid grid-cols-3 gap-2 text-center font-mono text-[11px]">
              <div className="border border-[#E4E4E1] rounded-md py-2">
                <div className="text-[#FF5A00] text-base font-bold">€42K</div>
                <div className="text-[#A1A1AA] uppercase tracking-widest text-[9px]">pipeline</div>
              </div>
              <div className="border border-[#E4E4E1] rounded-md py-2">
                <div className="text-[#0A192F] text-base font-bold">3</div>
                <div className="text-[#A1A1AA] uppercase tracking-widest text-[9px]">mandanti</div>
              </div>
              <div className="border border-[#E4E4E1] rounded-md py-2">
                <div className="text-[#059669] text-base font-bold">+18%</div>
                <div className="text-[#A1A1AA] uppercase tracking-widest text-[9px]">vs mese prec.</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

import { useState, useEffect } from "react";
import { useNavigate, Navigate, useSearchParams, Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";
import { Eye, EyeOff, CreditCard } from "lucide-react";
import api from "../api";
import usePlans from "../hooks/usePlans";

export default function Login() {
  const { plansById, trialDays } = usePlans();
  const { user, loading, login } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  // Trial scaduto: mostriamo una schermata di pagamento al posto del login,
  // usando le credenziali appena digitate per avviare il checkout senza
  // richiedere una sessione autenticata (che non può più esistere).
  const [paywall, setPaywall] = useState(false);
  const [checkingOut, setCheckingOut] = useState(false);

  // Se arriva da un redirect per trial scaduto a metà sessione, avvisiamo
  // che deve reinserire le credenziali per procedere al pagamento.
  useEffect(() => {
    if (searchParams.get("scaduto") === "1") {
      setError("Il tuo periodo di prova gratuita è scaduto. Accedi di nuovo per scegliere un piano.");
    }
  }, []);

  const startCheckout = async (checkoutPlan) => {
    setCheckingOut(true);
    try {
      const { data } = await api.post("/subscription/checkout-expired", {
        email: email.trim().toLowerCase(),
        password,
        plan: checkoutPlan,
        return_url: window.location.origin,
      });
      window.location.href = data.url;
    } catch (err) {
      toast.error("Errore nell'avvio del pagamento. Riprova tra poco.");
      setCheckingOut(false);
    }
  };

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-[#F9F9F8]">
      <div className="font-mono text-sm text-[#52525B]">caricamento...</div>
    </div>
  );
  if (user) return <Navigate to="/app" replace />;

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
    setPaywall(false);
    const cleanEmail = email.trim().toLowerCase();
    setBusy(true);
    try {
      await login(cleanEmail, password);
      toast.success("Accesso effettuato");
      navigate("/app");
    } catch (err) {
      if (err?.response?.status === 402) {
        setPaywall(true);
      } else {
        const msg = formatError(err);
        setError(msg);
        toast.error(msg);
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-[1fr_1.2fr] bg-[#F9F9F8]">
      <title>Accedi — SALESFLY</title>
      <meta name="robots" content="noindex, nofollow" />
      {/* Left: form */}
      <div className="flex flex-col justify-between p-6 sm:p-10 lg:p-14">
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 flex items-center justify-center shrink-0">
              <img src="/logo-mark.png" alt="SALESFLY" className="w-full h-full object-contain" />
            </div>
            <div>
              <div className="font-cabinet font-black text-[16px] leading-none">SALESFLY.</div>
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
              01 — Accesso
            </div>
            <h1 className="font-cabinet font-black text-4xl sm:text-5xl tracking-tight text-[#0A0A0A] mb-3">
              Bentornato in zona.
            </h1>
            <p className="text-[14px] text-[#52525B] leading-relaxed mb-8 max-w-sm">
              Accedi al tuo cruscotto. Gestisci clienti, provvigioni e visite in un unico posto.
            </p>

            {paywall && (
              <div data-testid="trial-expired-paywall" className="bg-white border-2 border-[#FF5A00] rounded-lg p-6 mb-6">
                <h2 className="font-cabinet font-black text-xl mb-2">Il tuo periodo di prova è scaduto</h2>
                <p className="text-[13px] text-[#52525B] mb-5">
                  I {trialDays} giorni di prova gratuita per <strong>{email}</strong> sono terminati.
                  Scegli un piano per riattivare subito il tuo account.
                </p>
                <div className="grid grid-cols-2 gap-3 mb-4">
                  {Object.entries(plansById).map(([id, p]) => (
                    <div key={id} className={`border-2 rounded-md p-4 ${id === "pro" ? "border-[#FF5A00]" : "border-[#E4E4E1]"}`}>
                      <div className="font-cabinet font-black text-lg">{p.name}</div>
                      <div className="font-cabinet font-black text-2xl mb-3">€{p.price_eur}<span className="text-[12px] font-normal text-[#52525B]">/mese</span></div>
                      <button type="button" onClick={() => startCheckout(id)} disabled={checkingOut}
                        className="w-full flex items-center justify-center gap-2 py-2 bg-[#0A192F] text-white rounded-md text-[12px] font-medium disabled:opacity-50">
                        <CreditCard className="w-3.5 h-3.5" /> {checkingOut ? "Attendere…" : "Attiva"}
                      </button>
                    </div>
                  ))}
                </div>
                <button type="button" onClick={() => setPaywall(false)} className="text-[12px] text-[#52525B] underline">
                  ← Torna al login
                </button>
              </div>
            )}

            {!paywall && (
            <form onSubmit={submit} className="space-y-4">
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
                <div className="text-right mt-1.5">
                  <Link to="/password-dimenticata" className="text-[12px] text-[#52525B] hover:text-[#0A192F] underline underline-offset-4">
                    Password dimenticata?
                  </Link>
                </div>
              </div>

              <button data-testid="login-submit-button" type="submit" disabled={busy}
                className="w-full bg-[#0A192F] hover:bg-[#172A45] text-white font-medium py-3 rounded-md transition-all flex items-center justify-center gap-2 disabled:opacity-50">
                {busy ? "Attendere…" : "Accedi al gestionale"}
                <span className="text-[#FF5A00]">→</span>
              </button>

              {error && (
                <div data-testid="auth-error" className="bg-[#DC2626]/5 border border-[#DC2626]/30 rounded-md p-3 text-[12px] text-[#DC2626] font-medium">
                  {error}
                </div>
              )}
            </form>
            )}

            {!paywall && (
            <div className="mt-6 text-[13px] text-[#52525B]">
              Non hai un account?{" "}
              <Link data-testid="signup-link" to="/richiedi-demo"
                className="text-[#0A192F] font-semibold underline underline-offset-4 decoration-[#FF5A00]">
                Inizia gratis
              </Link>
            </div>
            )}
          </div>
        </div>

        <footer className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA]">
          © 2026 SALESFLY — Made in Italia
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

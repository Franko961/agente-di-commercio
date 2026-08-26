import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Eye, EyeOff, CheckCircle2 } from "lucide-react";
import api from "../api";
import { toast } from "sonner";

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (password.length < 10) {
      setError("La password deve avere almeno 10 caratteri");
      return;
    }
    if (password !== confirm) {
      setError("Le due password non coincidono");
      return;
    }
    setBusy(true);
    try {
      await api.post("/auth/reset-password", { token, new_password: password });
      setDone(true);
      toast.success("Password aggiornata con successo");
      setTimeout(() => navigate("/login"), 2000);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const msg = typeof detail === "string" ? detail : "Si è verificato un errore, riprova tra poco.";
      setError(msg);
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F9F9F8] flex flex-col">
      <title>Reimposta password — SALESFLY</title>
      <meta name="robots" content="noindex, nofollow" />

      <header className="border-b border-[#E4E4E1] bg-white px-6 py-4 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-9 h-9 flex items-center justify-center shrink-0">
            <img src="/logo-mark.webp" alt="SALESFLY" className="w-full h-full object-contain" />
          </div>
          <span className="font-cabinet font-black text-lg">SALESFLY.</span>
        </Link>
        <Link to="/login" className="text-[13px] text-[#52525B] hover:text-[#0A192F]">Accedi</Link>
      </header>

      <main className="flex-1 px-6 py-16 max-w-md mx-auto w-full">
        {!token ? (
          <div className="bg-white border border-[#E4E4E1] rounded-xl p-8 text-center">
            <h1 className="font-cabinet font-black text-2xl mb-2">Link non valido</h1>
            <p className="text-[#52525B] text-sm mb-6">
              Questo link non contiene un token di reset valido. Richiedine uno nuovo dalla pagina di login.
            </p>
            <Link to="/password-dimenticata" className="text-[13px] font-semibold text-[#0A192F] underline underline-offset-4 decoration-[#B23E00]">
              Richiedi un nuovo link →
            </Link>
          </div>
        ) : done ? (
          <div className="bg-white border border-[#E4E4E1] rounded-xl p-8 text-center">
            <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-4" />
            <h1 className="font-cabinet font-black text-2xl mb-2">Password aggiornata</h1>
            <p className="text-[#52525B] text-sm">Ti stiamo reindirizzando al login…</p>
          </div>
        ) : (
          <>
            <div className="text-center mb-8">
              <h1 className="font-cabinet font-black text-3xl mb-2">Scegli una nuova password</h1>
              <p className="text-[#52525B] text-sm">Il link è valido per 1 ora dalla richiesta.</p>
            </div>

            <form onSubmit={submit} className="bg-white border border-[#E4E4E1] rounded-xl p-6 space-y-4">
              <div>
                <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Nuova password</label>
                <div className="relative">
                  <input
                    type={show ? "text" : "password"}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2.5 text-[14px] pr-10 focus:outline-none focus:border-[#0A192F]"
                  />
                  <button type="button" onClick={() => setShow(!show)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[#6B6B72]">
                    {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Conferma password</label>
                <input
                  type={show ? "text" : "password"}
                  required
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2.5 text-[14px] focus:outline-none focus:border-[#0A192F]"
                />
              </div>

              <button type="submit" disabled={busy}
                className="w-full bg-[#0A192F] hover:bg-[#172A45] text-white font-medium py-3 rounded-md transition-all flex items-center justify-center gap-2 disabled:opacity-50">
                {busy ? "Attendere…" : "Reimposta password"}
                <span className="text-[#B23E00]">→</span>
              </button>

              {error && (
                <div className="bg-[#DC2626]/5 border border-[#DC2626]/30 rounded-md p-3 text-[12px] text-[#DC2626] font-medium">
                  {error}
                </div>
              )}
            </form>
          </>
        )}
      </main>
    </div>
  );
}

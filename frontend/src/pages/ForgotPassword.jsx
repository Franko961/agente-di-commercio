import { useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";
import api from "../api";
import { toast } from "sonner";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api.post("/auth/forgot-password", { email: email.trim().toLowerCase() });
      // Il backend risponde sempre con lo stesso messaggio generico, esista o
      // meno l'email, per non rivelare quali indirizzi sono registrati.
      setSent(true);
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
      <title>Password dimenticata — SALESFLY</title>
      <meta name="robots" content="noindex, nofollow" />

      <header className="border-b border-[#E4E4E1] bg-white px-6 py-4 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-9 h-9 flex items-center justify-center shrink-0">
            <img src="/logo-mark.png" alt="SALESFLY" className="w-full h-full object-contain" />
          </div>
          <span className="font-cabinet font-black text-lg">SALESFLY.</span>
        </Link>
        <Link to="/login" className="text-[13px] text-[#52525B] hover:text-[#0A192F]">Accedi</Link>
      </header>

      <main className="flex-1 px-6 py-16 max-w-md mx-auto w-full">
        {sent ? (
          <div className="bg-white border border-[#E4E4E1] rounded-xl p-8 text-center">
            <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-4" />
            <h1 className="font-cabinet font-black text-2xl mb-2">Controlla la tua email</h1>
            <p className="text-[#52525B] text-sm">
              Se l'indirizzo <strong>{email}</strong> è registrato su SALESFLY, riceverai a breve un'email
              con le istruzioni per reimpostare la password. Il link è valido per 1 ora. Se non la trovi,
              controlla anche nello spam.
            </p>
            <Link to="/login" className="inline-block mt-6 text-[13px] font-semibold text-[#0A192F] underline underline-offset-4 decoration-[#FF5A00]">
              ← Torna al login
            </Link>
          </div>
        ) : (
          <>
            <div className="text-center mb-8">
              <h1 className="font-cabinet font-black text-3xl mb-2">Password dimenticata?</h1>
              <p className="text-[#52525B] text-sm">
                Inserisci l'email del tuo account: ti manderemo un link per scegliere una nuova password.
              </p>
            </div>

            <form onSubmit={submit} className="bg-white border border-[#E4E4E1] rounded-xl p-6 space-y-4">
              <div>
                <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Email</label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2.5 text-[14px] focus:outline-none focus:border-[#0A192F]"
                />
              </div>

              <button type="submit" disabled={busy}
                className="w-full bg-[#0A192F] hover:bg-[#172A45] text-white font-medium py-3 rounded-md transition-all flex items-center justify-center gap-2 disabled:opacity-50">
                {busy ? "Invio in corso…" : "Invia link di reset"}
                <span className="text-[#FF5A00]">→</span>
              </button>

              {error && (
                <div className="bg-[#DC2626]/5 border border-[#DC2626]/30 rounded-md p-3 text-[12px] text-[#DC2626] font-medium">
                  {error}
                </div>
              )}
            </form>

            <div className="mt-6 text-center text-[13px] text-[#52525B]">
              <Link to="/login" className="text-[#0A192F] font-semibold underline underline-offset-4 decoration-[#FF5A00]">
                ← Torna al login
              </Link>
            </div>
          </>
        )}
      </main>
    </div>
  );
}

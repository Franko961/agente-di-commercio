import { useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";
import api from "../api";
import { toast } from "sonner";
import usePlans from "../hooks/usePlans";

export default function RichiediDemo() {
  const { trialDays } = usePlans();
  const [form, setForm] = useState({
    nome: "", cognome: "", email: "", azienda: "", telefono: "",
    privacy_consent: false, marketing_consent: false,
  });
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [emailFailed, setEmailFailed] = useState(false);
  const [error, setError] = useState("");

  const update = (field, value) => setForm((f) => ({ ...f, [field]: value }));

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (!form.nome.trim() || !form.cognome.trim() || !form.email.trim()) {
      setError("Compila nome, cognome ed email.");
      return;
    }
    if (!form.privacy_consent) {
      setError("Devi accettare l'informativa privacy per procedere.");
      return;
    }
    setBusy(true);
    try {
      const { data } = await api.post("/demo-requests", form);
      setEmailFailed(data?.credentials_email_sent === false);
      setSent(true);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Si è verificato un errore, riprova tra poco.");
      toast.error("Invio non riuscito");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F9F9F8] flex flex-col">
      <title>Richiedi la Demo — SALESFLY</title>
      <meta name="description" content="Richiedi l'accesso alla demo di SALESFLY, il CRM per Agenti di Commercio. Riceverai subito il link di accesso via email." />
      <link rel="canonical" href="https://salesfly.it/richiedi-demo" />

      <header className="border-b border-[#E4E4E1] bg-white px-6 py-4 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-9 h-9 flex items-center justify-center shrink-0">
            <img src="/logo-mark.png" alt="SALESFLY" className="w-full h-full object-contain" />
          </div>
          <span className="font-cabinet font-black text-lg">SALESFLY.</span>
        </Link>
        <Link to="/login" className="text-[13px] text-[#52525B] hover:text-[#0A192F]">Accedi</Link>
      </header>

      <main className="flex-1 px-6 py-16 max-w-lg mx-auto w-full">
        {sent ? (
          emailFailed ? (
            <div className="bg-white border border-[#E4E4E1] rounded-xl p-8 text-center">
              <CheckCircle2 className="w-12 h-12 text-amber-500 mx-auto mb-4" />
              <h1 className="font-cabinet font-black text-2xl mb-2">Account creato</h1>
              <p className="text-[#52525B] text-sm mb-4">
                Il tuo account con {trialDays} giorni di prova gratuita è pronto, ma non siamo
                riusciti a inviarti l'email con la password. Usa "Password dimenticata" nella
                pagina di accesso per impostarne una nuova.
              </p>
              <Link to="/login" className="text-sm font-medium text-[#0A192F] underline">
                Vai alla pagina di accesso
              </Link>
            </div>
          ) : (
            <div className="bg-white border border-[#E4E4E1] rounded-xl p-8 text-center">
              <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-4" />
              <h1 className="font-cabinet font-black text-2xl mb-2">Controlla la tua email</h1>
              <p className="text-[#52525B] text-sm">
                Abbiamo creato il tuo account e ti abbiamo inviato email e password per accedere
                subito a SALESFLY, con {trialDays} giorni di prova gratuita. Se non la trovi, controlla anche nello spam.
              </p>
            </div>
          )
        ) : (
          <>
            <div className="text-center mb-8">
              <h1 className="font-cabinet font-black text-3xl mb-2">Richiedi la Demo</h1>
              <p className="text-[#52525B] text-sm">
                Compila il form: riceverai subito via email le tue credenziali di accesso e potrai
                usare SALESFLY gratis per {trialDays} giorni.
              </p>
            </div>

            <form onSubmit={submit} className="bg-white border border-[#E4E4E1] rounded-xl p-6 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[12px] font-medium text-[#52525B] mb-1">Nome *</label>
                  <input
                    value={form.nome}
                    onChange={(e) => update("nome", e.target.value)}
                    className="w-full border border-[#E4E4E1] rounded-md px-3 py-2 text-sm"
                    required
                  />
                </div>
                <div>
                  <label className="block text-[12px] font-medium text-[#52525B] mb-1">Cognome *</label>
                  <input
                    value={form.cognome}
                    onChange={(e) => update("cognome", e.target.value)}
                    className="w-full border border-[#E4E4E1] rounded-md px-3 py-2 text-sm"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-[12px] font-medium text-[#52525B] mb-1">Email *</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => update("email", e.target.value)}
                  className="w-full border border-[#E4E4E1] rounded-md px-3 py-2 text-sm"
                  required
                />
              </div>

              <div>
                <label className="block text-[12px] font-medium text-[#52525B] mb-1">Azienda</label>
                <input
                  value={form.azienda}
                  onChange={(e) => update("azienda", e.target.value)}
                  className="w-full border border-[#E4E4E1] rounded-md px-3 py-2 text-sm"
                />
              </div>

              <div>
                <label className="block text-[12px] font-medium text-[#52525B] mb-1">Telefono</label>
                <input
                  value={form.telefono}
                  onChange={(e) => update("telefono", e.target.value)}
                  className="w-full border border-[#E4E4E1] rounded-md px-3 py-2 text-sm"
                />
              </div>

              <label className="flex items-start gap-2 text-[12px] text-[#52525B] pt-2">
                <input
                  type="checkbox"
                  checked={form.privacy_consent}
                  onChange={(e) => update("privacy_consent", e.target.checked)}
                  className="mt-0.5"
                  required
                />
                <span>
                  Ho letto e accetto l'
                  <Link to="/privacy" target="_blank" className="underline text-[#0A192F]">
                    informativa sulla privacy
                  </Link>{" "}
                  e acconsento al trattamento dei miei dati per ricevere l'accesso alla demo. *
                </span>
              </label>

              <label className="flex items-start gap-2 text-[12px] text-[#52525B]">
                <input
                  type="checkbox"
                  checked={form.marketing_consent}
                  onChange={(e) => update("marketing_consent", e.target.checked)}
                  className="mt-0.5"
                />
                <span>
                  Acconsento (facoltativo) a essere ricontattato per comunicazioni commerciali su SALESFLY.
                </span>
              </label>

              {error && <p className="text-[12px] text-red-600">{error}</p>}

              <button
                type="submit"
                disabled={busy}
                className="w-full bg-[#0A192F] text-white rounded-md py-2.5 text-sm font-medium disabled:opacity-60"
              >
                {busy ? "Invio in corso…" : "Richiedi accesso alla demo"}
              </button>

              <p className="text-[11px] text-[#999] text-center">* Campi obbligatori</p>
            </form>
          </>
        )}
      </main>
    </div>
  );
}

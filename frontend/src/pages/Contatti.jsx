import { useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, Mail } from "lucide-react";
import { createContactRequest } from "../api/contactRequests";
import { toast } from "sonner";
import PublicHeader from "@/components/PublicHeader";
import PublicFooter from "@/components/PublicFooter";
import PageMeta from "@/components/PageMeta";

export default function Contatti() {
  const [form, setForm] = useState({ nome: "", email: "", telefono: "", messaggio: "", privacy_consent: false });
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  const update = (field, value) => setForm((f) => ({ ...f, [field]: value }));

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (!form.nome.trim() || !form.email.trim() || !form.messaggio.trim()) {
      setError("Compila nome, email e messaggio.");
      return;
    }
    if (!form.privacy_consent) {
      setError("Devi accettare l'informativa privacy per procedere.");
      return;
    }
    setBusy(true);
    try {
      await createContactRequest(form);
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
      <PageMeta path="/contatti" />

      <PublicHeader />

      <main className="flex-1 px-6 py-16 max-w-lg mx-auto w-full">
        {sent ? (
          <div className="bg-white border border-[#E4E4E1] rounded-xl p-8 text-center">
            <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-4" />
            <h1 className="font-cabinet font-black text-2xl mb-2">Messaggio inviato</h1>
            <p className="text-[#52525B] text-sm">
              Grazie, abbiamo ricevuto il tuo messaggio. Ti risponderemo il prima possibile all'indirizzo email che ci hai lasciato.
            </p>
          </div>
        ) : (
          <>
            <div className="text-center mb-8">
              <div className="w-11 h-11 rounded-full bg-[#0A192F0D] flex items-center justify-center mx-auto mb-4">
                <Mail className="w-5 h-5 text-[#0A192F]" />
              </div>
              <h1 className="font-cabinet font-black text-3xl mb-2">Contattaci</h1>
              <p className="text-[#52525B] text-sm">
                Domande sul prodotto, sui prezzi o sull'attivazione? Scrivici, ti risponderemo il prima possibile.
              </p>
            </div>

            <form onSubmit={submit} className="bg-white border border-[#E4E4E1] rounded-xl p-6 space-y-4">
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
                <label className="block text-[12px] font-medium text-[#52525B] mb-1">Telefono</label>
                <input
                  value={form.telefono}
                  onChange={(e) => update("telefono", e.target.value)}
                  className="w-full border border-[#E4E4E1] rounded-md px-3 py-2 text-sm"
                />
              </div>

              <div>
                <label className="block text-[12px] font-medium text-[#52525B] mb-1">Messaggio *</label>
                <textarea
                  value={form.messaggio}
                  onChange={(e) => update("messaggio", e.target.value)}
                  rows={5}
                  className="w-full border border-[#E4E4E1] rounded-md px-3 py-2 text-sm resize-none"
                  required
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
                  e acconsento al trattamento dei miei dati per essere ricontattato. *
                </span>
              </label>

              {error && <p className="text-[12px] text-red-600">{error}</p>}

              <button
                type="submit"
                disabled={busy}
                className="w-full bg-[#0A192F] text-white rounded-md py-2.5 text-sm font-medium disabled:opacity-60"
              >
                {busy ? "Invio in corso…" : "Invia messaggio"}
              </button>

              <p className="text-[11px] text-[#999] text-center">* Campi obbligatori</p>
            </form>
          </>
        )}
      </main>

      <PublicFooter />
    </div>
  );
}

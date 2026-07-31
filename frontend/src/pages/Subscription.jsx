import { useEffect, useState } from "react";
import api from "../api";
import usePlans from "../hooks/usePlans";
import { CheckCircle, XCircle, CreditCard, AlertTriangle, ExternalLink } from "lucide-react";
import { toast } from "sonner";

export default function Subscription() {
  const { plansById, loading: plansLoading } = usePlans();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [paying, setPaying] = useState(false);
  const [confirmingPaypal, setConfirmingPaypal] = useState(false);

  const load = async () => {
    const { data } = await api.get("/subscription/status");
    setStatus(data);
    setLoading(false);
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);

    // Ritorno da PayPal: dobbiamo prima chiedere conferma al backend (che a sua
    // volta verifica con PayPal) prima di sapere se l'abbonamento è davvero attivo.
    const subscriptionId = params.get("subscription_id");
    if (params.get("paypal_return") && subscriptionId) {
      setConfirmingPaypal(true);
      api.post("/subscription/paypal-capture", { subscription_id: subscriptionId })
        .then(({ data }) => {
          if (data.status === "active") {
            toast.success("Abbonamento attivato! Grazie.");
          } else {
            toast.info("Pagamento in verifica: l'abbonamento si attiverà a breve.");
          }
        })
        .catch(() => toast.error("Non siamo riusciti a confermare il pagamento PayPal. Contattaci se il problema persiste."))
        .finally(() => {
          setConfirmingPaypal(false);
          window.history.replaceState({}, "", window.location.pathname);
          load();
        });
      return;
    }

    load();
    // Gestisci redirect da Stripe
    if (params.get("success")) { toast.success("Abbonamento attivato! Grazie."); load(); }
    if (params.get("cancelled")) toast.info("Pagamento annullato.");
  }, []);

  const startStripe = async (plan) => {
    setPaying(true);
    try {
      const { data } = await api.post("/subscription/create-stripe-session", {
        plan,
        return_url: window.location.origin,
      });
      window.location.href = data.url;
    } catch {
      toast.error("Errore avvio pagamento Stripe");
      setPaying(false);
    }
  };

  const startPaypal = async (plan) => {
    setPaying(true);
    try {
      const { data } = await api.post("/subscription/paypal-create", {
        plan,
        return_url: window.location.origin,
      });
      window.location.href = data.approve_url;
    } catch {
      toast.error("Errore avvio pagamento PayPal");
      setPaying(false);
    }
  };

  const cancelSub = async () => {
    if (!window.confirm("Sei sicuro di voler cancellare l'abbonamento?")) return;
    await api.post("/subscription/cancel");
    toast.success("Abbonamento cancellato");
    load();
  };

  if (confirmingPaypal) {
    return (
      <div className="p-8 text-center text-[#52525B]">
        <div className="animate-pulse font-cabinet font-bold text-lg mb-2">Verifica pagamento PayPal in corso…</div>
        <div className="text-[13px]">Un attimo, stiamo confermando l'abbonamento con PayPal.</div>
      </div>
    );
  }

  if (loading || plansLoading) return <div className="p-8 text-center text-[#A1A1AA]">Caricamento…</div>;

  const plan = plansById[status?.plan] || plansById.base || { name: "", price_eur: 0, color: "#0A192F" };
  const isActive = status?.active;
  const isTrial = status?.status === "trial";
  const isCancelled = status?.status === "cancelled";
  // Disdetta già richiesta ma periodo pagato non ancora terminato: lo stato
  // resta "active" fino a quella data (vedi is_subscription_active nel
  // backend), quindi va distinto dall'abbonamento attivo "normale".
  const cancelAt = status?.cancel_at;
  const cancelAtLabel = cancelAt
    ? new Date(cancelAt).toLocaleDateString("it-IT", { day: "numeric", month: "long", year: "numeric" })
    : null;

  const trialDaysLeft = status?.trial_ends_at
    ? Math.max(0, Math.ceil((new Date(status.trial_ends_at) - new Date()) / 86400000))
    : 0;

  return (
    <div className="p-4 md:p-8 max-w-3xl">
      <div className="border-b border-[#E4E4E1] pb-6 mb-6">
        <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00] mb-2">Account</div>
        <h1 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight">Il tuo abbonamento</h1>
      </div>

      {/* Stato attuale */}
      <div className="bg-white border border-[#E4E4E1] rounded-md p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] mb-1">Piano attivo</div>
            <div className="font-cabinet font-black text-2xl" style={{ color: plan.color }}>{plan.name}</div>
            <div className="text-[14px] text-[#52525B] mt-1">€{plan.price_eur}/mese</div>
          </div>
          <div className="flex items-center gap-2">
            {isActive && !isTrial && !cancelAt && <CheckCircle className="w-5 h-5 text-[#059669]" />}
            {isTrial && <AlertTriangle className="w-5 h-5 text-[#FF5A00]" />}
            {(isCancelled || cancelAt) && <XCircle className="w-5 h-5 text-red-500" />}
            <span className="font-mono text-[11px] uppercase tracking-widest"
              style={{ color: isTrial ? "#FF5A00" : (isCancelled || cancelAt) ? "#DC2626" : "#059669" }}>
              {isTrial ? `Prova (${trialDaysLeft}gg rimasti)` : cancelAt ? "In scadenza" : isCancelled ? "Cancellato" : "Attivo"}
            </span>
          </div>
        </div>

        {isTrial && (
          <div className="bg-[#FF5A0010] border border-[#FF5A0030] rounded-md p-4 text-[13px] text-[#FF5A00]">
            La tua prova gratuita scade tra <strong>{trialDaysLeft} giorni</strong>. Attiva un abbonamento per continuare ad usare SALESFLY.
          </div>
        )}

        {isActive && !isTrial && cancelAt && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4 text-[13px] text-red-600">
            Hai disdetto l'abbonamento: resterà attivo fino al <strong>{cancelAtLabel}</strong>, poi non verrà rinnovato.
          </div>
        )}

        {isCancelled && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4 text-[13px] text-red-600">
            Il tuo abbonamento è stato cancellato. Riattivalo per continuare.
          </div>
        )}
      </div>

      {/* Scegli piano */}
      {(!isActive || isTrial || isCancelled) && (
        <div className="mb-6">
          <h2 className="font-cabinet font-bold text-lg mb-4">Attiva abbonamento</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(plansById).map(([id, p]) => (
              <div key={id} className={`bg-white border-2 rounded-md p-5 ${id === "pro" ? "border-[#FF5A00]" : "border-[#E4E4E1]"}`}>
                <div className="font-cabinet font-black text-xl mb-1" style={{ color: p.color }}>{p.name}</div>
                <div className="font-cabinet font-black text-3xl mb-4">€{p.price_eur}<span className="text-[14px] font-normal text-[#52525B]">/mese</span></div>

                {/* Stripe */}
                <button onClick={() => startStripe(id)} disabled={paying}
                  className="w-full flex items-center justify-center gap-2 py-2.5 bg-[#0A192F] text-white rounded-md text-[13px] font-medium mb-2 disabled:opacity-50">
                  <CreditCard className="w-4 h-4" /> Paga con carta (Stripe)
                </button>

                {/* PayPal */}
                <div className="text-center text-[11px] text-[#A1A1AA] mb-2">oppure</div>
                <button onClick={() => startPaypal(id)} disabled={paying}
                  className="w-full flex items-center justify-center gap-2 py-2.5 bg-[#FFC439] text-[#003087] rounded-md text-[13px] font-bold disabled:opacity-50">
                  <ExternalLink className="w-4 h-4" /> Paga con PayPal
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Cancella abbonamento */}
      {isActive && !isTrial && cancelAt && (
        <div className="bg-white border border-[#E4E4E1] rounded-md p-5">
          <div className="font-cabinet font-bold mb-2">Abbonamento in scadenza</div>
          <div className="text-[13px] text-[#52525B]">
            Hai già disdetto il rinnovo: potrai continuare a usare SALESFLY fino al <strong>{cancelAtLabel}</strong>.
          </div>
        </div>
      )}
      {isActive && !isTrial && !cancelAt && (
        <div className="bg-white border border-[#E4E4E1] rounded-md p-5">
          <div className="font-cabinet font-bold mb-2">Cancella abbonamento</div>
          <div className="text-[13px] text-[#52525B] mb-4">Puoi cancellare in qualsiasi momento. L'accesso rimane attivo fino alla fine del periodo pagato.</div>
          <button onClick={cancelSub} className="px-4 py-2 border border-red-300 text-red-500 rounded-md text-[13px] hover:bg-red-50 transition-colors">
            Cancella abbonamento
          </button>
        </div>
      )}
    </div>
  );
}

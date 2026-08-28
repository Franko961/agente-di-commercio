import { useEffect, useState } from "react";
import { listFeedbackAdmin, setFeedbackApproved, deleteFeedback } from "../../api/feedback";
import { Star, Check, X, Trash2 } from "lucide-react";
import { toast } from "sonner";

// ---------------------------------------------------------------------
// Feedback lasciati dagli utenti — moderazione prima della pubblicazione
// pubblica in home page (vedi GET /api/feedback/public: mostra solo ciò
// che è sia approvato QUI sia stato dato con consenso dall'utente stesso).
// ---------------------------------------------------------------------
export default function FeedbackTab() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      setItems(await listFeedbackAdmin());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const setApproved = async (id, approved) => {
    await setFeedbackApproved(id, approved);
    setItems((prev) => prev.map((i) => (i.id === id ? { ...i, approved } : i)));
    toast.success(approved ? "Feedback approvato" : "Approvazione revocata");
  };

  const remove = async (id) => {
    if (!window.confirm("Eliminare definitivamente questo feedback?")) return;
    await deleteFeedback(id);
    setItems((prev) => prev.filter((i) => i.id !== id));
    toast.success("Feedback eliminato");
  };

  return (
    <div className="bg-white border border-[#E4E4E1] rounded-md overflow-hidden">
      <div className="px-4 py-3 border-b border-[#E4E4E1] font-mono text-[11px] uppercase tracking-widest text-[#52525B]">
        Feedback ricevuti ({items.length})
      </div>
      {loading ? (
        <div className="p-8 text-center text-[#6B6B72]">Caricamento…</div>
      ) : items.length === 0 ? (
        <div className="p-8 text-center text-[13px] text-[#6B6B72]">Nessun feedback ricevuto</div>
      ) : (
        <div className="divide-y divide-[#E4E4E1]">
          {items.map((f) => (
            <div key={f.id} className="p-4 flex items-start justify-between gap-4">
              <div className="min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <div className="flex items-center">
                    {[1, 2, 3, 4, 5].map((n) => (
                      <Star key={n} className={`w-3.5 h-3.5 ${n <= f.rating ? "fill-[#B23E00] text-[#B23E00]" : "text-[#E4E4E1]"}`} />
                    ))}
                  </div>
                  <span className="text-[12px] font-medium">{f.user_name || "—"}</span>
                  <span className="text-[11px] text-[#6B6B72] font-mono">
                    {f.created_at ? new Date(f.created_at).toLocaleDateString("it-IT") : "—"}
                  </span>
                  {f.publish_consent ? (
                    <span className="text-[10px] font-mono uppercase tracking-widest text-[#059669]">consenso pubblicazione</span>
                  ) : (
                    <span className="text-[10px] font-mono uppercase tracking-widest text-[#6B6B72]">privato</span>
                  )}
                  {f.approved && (
                    <span className="text-[10px] font-mono uppercase tracking-widest text-[#B23E00]">approvato</span>
                  )}
                </div>
                {f.text && <p className="text-[13px] text-[#52525B]">{f.text}</p>}
              </div>
              <div className="flex items-center gap-1 shrink-0">
                {f.approved ? (
                  <button onClick={() => setApproved(f.id, false)} title="Revoca approvazione" aria-label="Revoca approvazione"
                    className="p-1.5 text-[#6B6B72] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded transition-colors">
                    <X className="w-4 h-4" />
                  </button>
                ) : (
                  <button onClick={() => setApproved(f.id, true)} disabled={!f.publish_consent} title={f.publish_consent ? "Approva per la pubblicazione" : "L'utente non ha dato il consenso alla pubblicazione"} aria-label="Approva per la pubblicazione"
                    className="p-1.5 text-[#6B6B72] hover:text-[#059669] hover:bg-green-50 rounded transition-colors disabled:opacity-30 disabled:hover:text-[#6B6B72] disabled:hover:bg-transparent">
                    <Check className="w-4 h-4" />
                  </button>
                )}
                <button onClick={() => remove(f.id)} title="Elimina" aria-label="Elimina feedback"
                  className="p-1.5 text-[#6B6B72] hover:text-[#DC2626] hover:bg-red-50 rounded transition-colors">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

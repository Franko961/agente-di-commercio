import { useEffect, useState } from "react";
import api from "../api";
import { Plus, Trash2, Pencil, Target } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../components/ui/dialog";
import { useMandante } from "../contexts/MandanteContext";
import { toast } from "sonner";

const fmt = (n) => new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(n || 0);
const EMPTY = { name: "", brand_color: "#0A192F", commission_rate: 5, notes: "", target_monthly: "", target_yearly: "", target_clients: "", target_notes: "" };

export default function Mandanti() {
  const { mandanti, refreshMandanti } = useMandante();
  const [open, setOpen] = useState(false);
  const [editTarget, setEditTarget] = useState(null);

  const remove = async (id) => {
    if (!window.confirm("Eliminare il mandante?")) return;
    await api.delete(`/mandanti/${id}`);
    refreshMandanti();
    toast.success("Mandante eliminato");
  };

  const save = async (f) => {
    await api.post("/mandanti", f);
    refreshMandanti();
    toast.success("Mandante creato");
    setOpen(false);
  };

  const update = async (id, f) => {
    await api.put(`/mandanti/${id}`, f);
    refreshMandanti();
    toast.success("Mandante aggiornato");
    setEditTarget(null);
  };

  return (
    <div className="p-4 md:p-8">
      <div className="flex items-end justify-between border-b border-[#E4E4E1] pb-6 mb-6">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00] mb-2">Multi-mandato</div>
          <h1 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight">Mandanti</h1>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <button data-testid="new-mandante-button" className="flex items-center gap-2 px-4 py-2.5 bg-[#0A192F] text-white rounded-md text-[13px] font-medium">
              <Plus className="w-4 h-4" /> Nuovo mandante
            </button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Nuovo mandante</DialogTitle></DialogHeader>
            <MandanteForm initial={EMPTY} onSave={save} />
          </DialogContent>
        </Dialog>
      </div>

      <Dialog open={!!editTarget} onOpenChange={(v) => !v && setEditTarget(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Modifica mandante</DialogTitle></DialogHeader>
          {editTarget && <MandanteForm initial={editTarget} onSave={(f) => update(editTarget.id, f)} submitLabel="Aggiorna" />}
        </DialogContent>
      </Dialog>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {mandanti.map(m => {
          const hasTargets = m.target_monthly || m.target_yearly || m.target_clients;
          return (
            <div key={m.id} data-testid={`mandante-${m.id}`} className="bg-white border border-[#E4E4E1] rounded-md p-5">
              <div className="flex items-start justify-between mb-3">
                <div className="w-10 h-10 rounded-md flex items-center justify-center" style={{ background: m.brand_color }}>
                  <span className="text-white font-cabinet font-black text-lg">{m.name[0]}</span>
                </div>
                <div className="flex gap-1">
                  <button onClick={() => setEditTarget(m)} className="p-1.5 text-[#A1A1AA] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded transition-colors" title="Modifica">
                    <Pencil className="w-4 h-4" />
                  </button>
                  <button onClick={() => remove(m.id)} className="p-1.5 text-[#A1A1AA] hover:text-[#DC2626] hover:bg-red-50 rounded transition-colors" title="Elimina">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              <div className="font-cabinet font-bold text-lg leading-tight">{m.name}</div>
              <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] mt-2">Provvigione standard</div>
              <div className="font-cabinet font-black text-2xl text-[#FF5A00]">{m.commission_rate}%</div>

              {hasTargets && (
                <div className="mt-3 pt-3 border-t border-[#E4E4E1]">
                  <div className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-widest text-[#52525B] mb-2">
                    <Target className="w-3 h-3" /> Obiettivi
                  </div>
                  <div className="space-y-1">
                    {m.target_monthly && (
                      <div className="flex justify-between text-[12px]">
                        <span className="text-[#A1A1AA]">Mensile</span>
                        <span className="font-cabinet font-bold">{fmt(m.target_monthly)}</span>
                      </div>
                    )}
                    {m.target_yearly && (
                      <div className="flex justify-between text-[12px]">
                        <span className="text-[#A1A1AA]">Annuale</span>
                        <span className="font-cabinet font-bold">{fmt(m.target_yearly)}</span>
                      </div>
                    )}
                    {m.target_clients && (
                      <div className="flex justify-between text-[12px]">
                        <span className="text-[#A1A1AA]">Clienti target</span>
                        <span className="font-cabinet font-bold">{m.target_clients}</span>
                      </div>
                    )}
                  </div>
                  {m.target_notes && <div className="text-[11px] text-[#52525B] mt-2 italic">{m.target_notes}</div>}
                </div>
              )}

              {m.notes && <div className="text-[12px] text-[#52525B] mt-3 pt-3 border-t border-[#E4E4E1]">{m.notes}</div>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function MandanteForm({ initial, onSave, submitLabel = "Salva" }) {
  const [f, setF] = useState(initial);
  const [tab, setTab] = useState("info");

  useEffect(() => { setF(initial); setTab("info"); }, [initial]);

  return (
    <form onSubmit={async (e) => { e.preventDefault(); await onSave(f); }} className="space-y-3">
      <div className="flex border border-[#E4E4E1] rounded-md overflow-hidden mb-1">
        {["info", "obiettivi"].map(t => (
          <button key={t} type="button" onClick={() => setTab(t)}
            className={`flex-1 py-2 text-[12px] font-medium font-mono uppercase tracking-widest transition-colors ${tab === t ? "bg-[#0A192F] text-white" : "bg-white text-[#52525B]"}`}>
            {t === "info" ? "Dati azienda" : "Obiettivi"}
          </button>
        ))}
      </div>

      {tab === "info" && (
        <>
          <Field label="Nome mandante *" v={f.name} on={(v) => setF({ ...f, name: v })} required />
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Colore brand</label>
              <input type="color" value={f.brand_color} onChange={(e) => setF({ ...f, brand_color: e.target.value })}
                className="w-full h-10 bg-white border border-[#E4E4E1] rounded-md cursor-pointer" />
            </div>
            <Field label="Aliquota %" v={f.commission_rate} on={(v) => setF({ ...f, commission_rate: parseFloat(v) || 0 })} type="number" />
          </div>
          <div>
            <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Note</label>
            <textarea value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} rows={2}
              className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
          </div>
        </>
      )}

      {tab === "obiettivi" && (
        <>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Obiettivo mensile (€)" v={f.target_monthly} on={(v) => setF({ ...f, target_monthly: parseFloat(v) || "" })} type="number" />
            <Field label="Obiettivo annuale (€)" v={f.target_yearly} on={(v) => setF({ ...f, target_yearly: parseFloat(v) || "" })} type="number" />
          </div>
          <Field label="Clienti target (#)" v={f.target_clients} on={(v) => setF({ ...f, target_clients: parseInt(v) || "" })} type="number" />
          <div>
            <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Note obiettivi</label>
            <textarea value={f.target_notes} onChange={(e) => setF({ ...f, target_notes: e.target.value })} rows={2}
              placeholder="Es. raggiungere 10 nuovi clienti entro Q3..."
              className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
          </div>
        </>
      )}

      <button data-testid="save-mandante-button" type="submit"
        className="w-full bg-[#0A192F] text-white py-2.5 rounded-md text-[13px] font-medium">
        {submitLabel}
      </button>
    </form>
  );
}

function Field({ label, v, on, type = "text", required }) {
  return (
    <div>
      <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">{label}</label>
      <input type={type} required={required} value={v ?? ""} onChange={(e) => on(e.target.value)}
        className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
    </div>
  );
}

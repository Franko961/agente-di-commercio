import { useEffect, useState } from "react";
import api from "../api";
import { Plus, Trash2 } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../components/ui/dialog";
import { useMandante } from "../contexts/MandanteContext";
import { toast } from "sonner";

export default function Mandanti() {
  const { mandanti, refreshMandanti } = useMandante();
  const [open, setOpen] = useState(false);

  const remove = async (id) => {
    if (!window.confirm("Eliminare il mandante?")) return;
    await api.delete(`/mandanti/${id}`);
    refreshMandanti();
    toast.success("Mandante eliminato");
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
            <MandanteForm onSave={async (f) => { await api.post("/mandanti", f); refreshMandanti(); toast.success("Mandante creato"); setOpen(false); }} />
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {mandanti.map(m => (
          <div key={m.id} data-testid={`mandante-${m.id}`} className="bg-white border border-[#E4E4E1] rounded-md p-5">
            <div className="flex items-start justify-between mb-3">
              <div className="w-10 h-10 rounded-md flex items-center justify-center" style={{ background: m.brand_color }}>
                <span className="text-white font-cabinet font-black text-lg">{m.name[0]}</span>
              </div>
              <button onClick={() => remove(m.id)} className="text-[#A1A1AA] hover:text-[#DC2626]"><Trash2 className="w-4 h-4" /></button>
            </div>
            <div className="font-cabinet font-bold text-lg leading-tight">{m.name}</div>
            <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] mt-2">Provvigione standard</div>
            <div className="font-cabinet font-black text-2xl text-[#FF5A00]">{m.commission_rate}%</div>
            {m.notes && <div className="text-[12px] text-[#52525B] mt-3 pt-3 border-t border-[#E4E4E1]">{m.notes}</div>}
          </div>
        ))}
      </div>
    </div>
  );
}

function MandanteForm({ onSave }) {
  const [f, setF] = useState({ name: "", brand_color: "#0A192F", commission_rate: 5, notes: "" });
  return (
    <form onSubmit={async (e) => { e.preventDefault(); await onSave(f); }} className="space-y-3">
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
      <button data-testid="save-mandante-button" type="submit" className="w-full bg-[#0A192F] text-white py-2.5 rounded-md text-[13px] font-medium">Salva</button>
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

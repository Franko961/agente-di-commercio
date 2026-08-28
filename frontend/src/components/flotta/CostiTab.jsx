import { useState } from "react";
import { Plus, Trash2, Pencil } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../ui/dialog";
import { COST_CATEGORY_LABELS, fmtEuro } from "./constants";

export default function CostiTab({
  costs, activeVehicles, totalCosts,
  costOpen, setCostOpen, costEditTarget, setCostEditTarget,
  saveCost, deleteCost, emptyCost,
}) {
  return (
    <div>
      <div className="text-[12px] text-[#6B6B72] mb-3">Ogni costo genera automaticamente una voce nel modulo Spese, così dashboard, AI e report restano coerenti.</div>
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <div className="text-[13px] text-[#52525B]">Totale: <span className="font-cabinet font-bold text-[15px] text-[#0A192F]">{fmtEuro(totalCosts)}</span></div>
        <Dialog open={costOpen} onOpenChange={setCostOpen}>
          <DialogTrigger asChild>
            <button className="flex items-center gap-2 px-4 py-2.5 bg-[#0A192F] text-white rounded-md text-[13px] font-medium">
              <Plus className="w-4 h-4" /> Nuovo costo
            </button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Nuovo costo</DialogTitle></DialogHeader>
            <CostForm initial={emptyCost} vehicles={activeVehicles} onSave={saveCost} />
          </DialogContent>
        </Dialog>
      </div>
      <Dialog open={!!costEditTarget} onOpenChange={(v) => !v && setCostEditTarget(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Modifica costo</DialogTitle></DialogHeader>
          {costEditTarget && <CostForm initial={{ ...costEditTarget, amount: String(costEditTarget.amount) }} vehicles={activeVehicles} onSave={saveCost} submitLabel="Aggiorna" />}
        </DialogContent>
      </Dialog>

      <div className="space-y-2">
        {costs.map((c) => (
          <div key={c.id} className="bg-white border border-[#E4E4E1] rounded-md p-4 flex items-center justify-between gap-3 flex-wrap">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-cabinet font-bold text-[14px]">{c.vehicle_plate}</span>
                <span className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72]">{COST_CATEGORY_LABELS[c.category]}</span>
              </div>
              <div className="text-[12px] text-[#52525B] mt-1">{c.date}{c.description ? ` · ${c.description}` : ""}</div>
            </div>
            <div className="flex items-center gap-3">
              <span className="font-cabinet font-bold text-[15px]">{fmtEuro(c.amount)}</span>
              <div className="flex gap-1">
                <button onClick={() => setCostEditTarget(c)} title="Modifica" aria-label="Modifica costo"
                  className="p-1.5 text-[#6B6B72] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded"><Pencil className="w-4 h-4" /></button>
                <button onClick={() => deleteCost(c.id)} title="Elimina" aria-label="Elimina costo"
                  className="p-1.5 text-[#6B6B72] hover:text-red-500 hover:bg-red-50 rounded"><Trash2 className="w-4 h-4" /></button>
              </div>
            </div>
          </div>
        ))}
        {costs.length === 0 && (
          <div className="bg-white border border-[#E4E4E1] rounded-md p-8 text-center text-[#6B6B72] text-[13px]">Nessun costo ancora registrato.</div>
        )}
      </div>
    </div>
  );
}

function CostForm({ initial, vehicles, onSave, submitLabel = "Salva" }) {
  const [f, setF] = useState({
    vehicle_id: initial.vehicle_id || (vehicles[0]?.id || ""), category: initial.category || "carburante",
    amount: initial.amount || "", date: initial.date || "", description: initial.description || "",
  });
  return (
    <form onSubmit={async (e) => { e.preventDefault(); await onSave(f); }} className="space-y-3">
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Mezzo *</label>
        <select required value={f.vehicle_id} onChange={(e) => setF({ ...f, vehicle_id: e.target.value })}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
          <option value="" disabled>Seleziona un mezzo</option>
          {vehicles.map((v) => <option key={v.id} value={v.id}>{v.plate}{v.model ? ` — ${v.model}` : ""}</option>)}
        </select>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Categoria *</label>
          <select value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })}
            className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
            {Object.entries(COST_CATEGORY_LABELS).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
          </select>
        </div>
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Importo (€) *</label>
          <input required type="number" step="0.01" min="0.01" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })}
            className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
        </div>
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Data *</label>
        <input required type="date" value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Descrizione</label>
        <textarea value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} rows={2}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      </div>
      <button type="submit" className="w-full bg-[#0A192F] text-white py-2.5 rounded-md text-[13px] font-medium">{submitLabel}</button>
    </form>
  );
}

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Wallet, Plus, Pencil, Trash2 } from "lucide-react";
import { listCompensation, createCompensation, updateCompensation, deleteCompensation } from "../../../api/employees";
import { MiniStat } from "./AssenzeTab";

const COMPENSATION_TYPE_LABELS = { stipendio: "Stipendio", bonus: "Bonus", rimborso: "Rimborso", altro: "Altro" };
const fmtEur = (v) => (v || 0).toLocaleString("it-IT", { style: "currency", currency: "EUR" });

export default function CompensiTab({ employeeId }) {
  const [items, setItems] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editTarget, setEditTarget] = useState(null);

  const load = async () => {
    setItems(await listCompensation(employeeId));
  };
  useEffect(() => { load(); }, [employeeId]); // eslint-disable-line react-hooks/exhaustive-deps

  const openNew = () => { setEditTarget(null); setFormOpen(true); };
  const openEdit = (item) => { setEditTarget(item); setFormOpen(true); };
  const closeForm = () => { setFormOpen(false); setEditTarget(null); };

  const remove = async (item) => {
    if (!window.confirm(`Eliminare il compenso del ${item.date}? Verrà rimossa anche la spesa collegata.`)) return;
    try {
      await deleteCompensation(employeeId, item.id);
      toast.success("Compenso eliminato");
      load();
    } catch {
      toast.error("Errore eliminazione");
    }
  };

  const currentYear = new Date().getFullYear();
  const yearTotal = (items || [])
    .filter((it) => it.date?.startsWith(String(currentYear)))
    .reduce((sum, it) => sum + (it.amount || 0), 0);

  return (
    <div>
      {items && (
        <div className="mb-4"><MiniStat label={`Totale ${currentYear}`} value={fmtEur(yearTotal)} /></div>
      )}
      <div className="flex justify-end mb-3">
        <button onClick={openNew} className="flex items-center gap-1.5 px-3 py-2 bg-[#0A192F] text-white rounded-md text-[12px] font-medium">
          <Plus className="w-3.5 h-3.5" /> Aggiungi compenso
        </button>
      </div>
      {formOpen && (
        <CompensationForm employeeId={employeeId} initial={editTarget} onDone={() => { closeForm(); load(); }} onCancel={closeForm} />
      )}
      <div className="space-y-2 mt-3">
        {(items || []).map((it) => (
          <div key={it.id} className="bg-white border border-[#E4E4E1] rounded-md p-3 flex items-center justify-between gap-2 flex-wrap text-[13px]">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <Wallet className="w-4 h-4 text-[#6B6B72] shrink-0" />
                <span className="font-medium">{COMPENSATION_TYPE_LABELS[it.type] || it.type}</span>
                <span className="text-[#52525B]">{it.date}</span>
              </div>
              {it.notes && <div className="text-[11px] text-[#6B6B72] mt-0.5">{it.notes}</div>}
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <span className="font-cabinet font-bold">{fmtEur(it.amount)}</span>
              <button onClick={() => openEdit(it)} title="Modifica" aria-label="Modifica compenso"
                className="p-1.5 text-[#6B6B72] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded"><Pencil className="w-4 h-4" /></button>
              <button onClick={() => remove(it)} title="Elimina" aria-label="Elimina compenso"
                className="p-1.5 text-[#6B6B72] hover:text-red-500 hover:bg-red-50 rounded"><Trash2 className="w-4 h-4" /></button>
            </div>
          </div>
        ))}
        {items && items.length === 0 && !formOpen && (
          <div className="bg-white border border-[#E4E4E1] rounded-md p-6 text-center text-[#6B6B72] text-[13px]">Nessun compenso registrato.</div>
        )}
      </div>
    </div>
  );
}

function CompensationForm({ employeeId, initial, onDone, onCancel }) {
  const [f, setF] = useState({
    type: initial?.type || "stipendio", amount: initial?.amount ?? "",
    date: initial?.date || new Date().toISOString().slice(0, 10), notes: initial?.notes || "",
  });
  const [saving, setSaving] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!f.amount || Number(f.amount) <= 0) { toast.error("Inserisci un importo valido"); return; }
    if (!f.date) { toast.error("Inserisci una data"); return; }
    setSaving(true);
    const payload = { ...f, amount: Number(f.amount) };
    try {
      if (initial) {
        await updateCompensation(employeeId, initial.id, payload);
        toast.success("Compenso aggiornato");
      } else {
        await createCompensation(employeeId, payload);
        toast.success("Compenso aggiunto");
      }
      onDone();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Salvataggio non riuscito");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={submit} className="bg-[#F9F9F8] border border-[#E4E4E1] rounded-md p-3 space-y-2.5 mb-3">
      <div className="grid grid-cols-3 gap-2">
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1">Tipo</label>
          <select value={f.type} onChange={(e) => setF({ ...f, type: e.target.value })}
            className="w-full bg-white border border-[#E4E4E1] rounded-md px-2 py-2 text-[13px]">
            {Object.entries(COMPENSATION_TYPE_LABELS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </select>
        </div>
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1">Importo (€)</label>
          <input type="number" min="0.01" step="0.01" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })}
            className="w-full bg-white border border-[#E4E4E1] rounded-md px-2 py-2 text-[13px]" />
        </div>
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1">Data</label>
          <input type="date" value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })}
            className="w-full bg-white border border-[#E4E4E1] rounded-md px-2 py-2 text-[13px]" />
        </div>
      </div>
      <input value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} placeholder="Note (opzionale)"
        className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      <p className="text-[11px] text-[#6B6B72]">Genera automaticamente una spesa collegata, visibile in Spese.</p>
      <div className="flex gap-2">
        <button type="submit" disabled={saving} className="flex-1 bg-[#0A192F] text-white py-2 rounded-md text-[12px] font-medium disabled:opacity-60">
          {saving ? "Salvataggio…" : initial ? "Aggiorna" : "Aggiungi"}
        </button>
        <button type="button" onClick={onCancel} className="px-4 py-2 border border-[#E4E4E1] rounded-md text-[12px] font-medium">
          Annulla
        </button>
      </div>
    </form>
  );
}

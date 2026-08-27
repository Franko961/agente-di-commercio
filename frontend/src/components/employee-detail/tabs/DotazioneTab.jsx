import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Package, Plus, Pencil, Trash2 } from "lucide-react";
import api from "../../../api";
import { formatApiError } from "../constants";

const EQUIPMENT_STATUS_LABELS = { consegnato: "Consegnato", restituito: "Restituito" };

export default function DotazioneTab({ employeeId }) {
  const [items, setItems] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editTarget, setEditTarget] = useState(null);

  const load = async () => {
    const { data } = await api.get(`/employees/${employeeId}/equipment`);
    setItems(data);
  };
  useEffect(() => { load(); }, [employeeId]); // eslint-disable-line react-hooks/exhaustive-deps

  const openNew = () => { setEditTarget(null); setFormOpen(true); };
  const openEdit = (item) => { setEditTarget(item); setFormOpen(true); };
  const closeForm = () => { setFormOpen(false); setEditTarget(null); };

  const remove = async (item) => {
    if (!window.confirm(`Eliminare "${item.name}" dalla dotazione?`)) return;
    try {
      await api.delete(`/employees/${employeeId}/equipment/${item.id}`);
      toast.success("Dotazione eliminata");
      load();
    } catch {
      toast.error("Errore eliminazione");
    }
  };

  return (
    <div>
      <div className="flex justify-end mb-3">
        <button onClick={openNew} className="flex items-center gap-1.5 px-3 py-2 bg-[#0A192F] text-white rounded-md text-[12px] font-medium">
          <Plus className="w-3.5 h-3.5" /> Aggiungi dotazione
        </button>
      </div>
      {formOpen && (
        <EquipmentForm employeeId={employeeId} initial={editTarget} onDone={() => { closeForm(); load(); }} onCancel={closeForm} />
      )}
      <div className="space-y-2 mt-3">
        {(items || []).map((it) => (
          <div key={it.id} className="bg-white border border-[#E4E4E1] rounded-md p-3 flex items-center justify-between gap-2 flex-wrap text-[13px]">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <Package className="w-4 h-4 text-[#6B6B72] shrink-0" />
                <span className="font-medium truncate">{it.name}</span>
                <span className="font-mono text-[10px] uppercase tracking-widest px-1.5 py-0.5 rounded-full shrink-0"
                  style={{ background: it.status === "restituito" ? "#F3F3F1" : "#05966920", color: it.status === "restituito" ? "#6B6B72" : "#059669" }}>
                  {EQUIPMENT_STATUS_LABELS[it.status]}
                </span>
              </div>
              <div className="text-[11px] text-[#6B6B72] mt-0.5">
                {it.delivered_date ? `Consegnata il ${it.delivered_date}` : "Data consegna non indicata"}
                {it.returned_date ? ` · Restituita il ${it.returned_date}` : ""}
                {it.notes ? ` · ${it.notes}` : ""}
              </div>
            </div>
            <div className="flex gap-1 shrink-0">
              <button onClick={() => openEdit(it)} title="Modifica" aria-label="Modifica dotazione"
                className="p-1.5 text-[#6B6B72] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded"><Pencil className="w-4 h-4" /></button>
              <button onClick={() => remove(it)} title="Elimina" aria-label="Elimina dotazione"
                className="p-1.5 text-[#6B6B72] hover:text-red-500 hover:bg-red-50 rounded"><Trash2 className="w-4 h-4" /></button>
            </div>
          </div>
        ))}
        {items && items.length === 0 && !formOpen && (
          <div className="bg-white border border-[#E4E4E1] rounded-md p-6 text-center text-[#6B6B72] text-[13px]">Nessuna dotazione assegnata.</div>
        )}
      </div>
    </div>
  );
}

function EquipmentForm({ employeeId, initial, onDone, onCancel }) {
  const [f, setF] = useState({
    name: initial?.name || "", delivered_date: initial?.delivered_date || "",
    returned_date: initial?.returned_date || "", status: initial?.status || "consegnato",
    notes: initial?.notes || "",
  });
  const [saving, setSaving] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!f.name.trim()) { toast.error("Inserisci un nome"); return; }
    setSaving(true);
    const payload = {
      ...f,
      delivered_date: f.delivered_date || null,
      returned_date: f.returned_date || null,
    };
    try {
      if (initial) {
        await api.put(`/employees/${employeeId}/equipment/${initial.id}`, payload);
        toast.success("Dotazione aggiornata");
      } else {
        await api.post(`/employees/${employeeId}/equipment`, payload);
        toast.success("Dotazione aggiunta");
      }
      onDone();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={submit} className="bg-[#F9F9F8] border border-[#E4E4E1] rounded-md p-3 space-y-2.5 mb-3">
      <input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} placeholder="Es. Divisa taglia L, telefono aziendale, chiavi ufficio"
        className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      <div className="grid grid-cols-3 gap-2">
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1">Consegnata il</label>
          <input type="date" value={f.delivered_date} onChange={(e) => setF({ ...f, delivered_date: e.target.value })}
            className="w-full bg-white border border-[#E4E4E1] rounded-md px-2 py-2 text-[13px]" />
        </div>
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1">Stato</label>
          <select value={f.status} onChange={(e) => {
            const status = e.target.value;
            // Coerente con la normalizzazione lato backend (models/employee_equipment.py):
            // "consegnato" non ha senso con una data di restituzione residua di un giro precedente.
            setF({ ...f, status, returned_date: status === "consegnato" ? "" : f.returned_date });
          }} className="w-full bg-white border border-[#E4E4E1] rounded-md px-2 py-2 text-[13px]">
            {Object.entries(EQUIPMENT_STATUS_LABELS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </select>
        </div>
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1">Restituita il</label>
          <input type="date" value={f.returned_date} onChange={(e) => setF({ ...f, returned_date: e.target.value })}
            className="w-full bg-white border border-[#E4E4E1] rounded-md px-2 py-2 text-[13px]" />
        </div>
      </div>
      <input value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} placeholder="Note (opzionale)"
        className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
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

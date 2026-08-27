import { useEffect, useState } from "react";
import { format, parseISO } from "date-fns";
import { toast } from "sonner";
import { Plus, Pencil, Trash2, Timer } from "lucide-react";
import api from "../../../api";
import { formatApiError } from "../constants";

function formatDuration(clockIn, clockOut) {
  if (!clockOut) return "In corso";
  const totalMinutes = Math.round((new Date(clockOut) - new Date(clockIn)) / 60000);
  return `${Math.floor(totalMinutes / 60)}h ${totalMinutes % 60}m`;
}

function fmtTime(iso) {
  return new Date(iso).toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" });
}

export default function PresenzeTab({ employeeId }) {
  const [items, setItems] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editTarget, setEditTarget] = useState(null);

  const load = async () => {
    const { data } = await api.get(`/employees/${employeeId}/attendance`);
    setItems(data);
  };
  useEffect(() => { load(); }, [employeeId]); // eslint-disable-line react-hooks/exhaustive-deps

  const openNew = () => { setEditTarget(null); setFormOpen(true); };
  const openEdit = (item) => { setEditTarget(item); setFormOpen(true); };
  const closeForm = () => { setFormOpen(false); setEditTarget(null); };

  const remove = async (item) => {
    if (!window.confirm("Eliminare questa sessione presenze?")) return;
    try {
      await api.delete(`/employees/${employeeId}/attendance/${item.id}`);
      toast.success("Sessione eliminata");
      load();
    } catch {
      toast.error("Errore eliminazione");
    }
  };

  return (
    <div>
      <p className="text-[11px] text-[#6B6B72] mb-3">
        Timbrature dal chiosco QR aziendale (orario registrato lato server) e correzioni manuali. Nessuna geolocalizzazione.
      </p>
      <div className="flex justify-end mb-3">
        <button onClick={openNew} className="flex items-center gap-1.5 px-3 py-2 bg-[#0A192F] text-white rounded-md text-[12px] font-medium">
          <Plus className="w-3.5 h-3.5" /> Aggiungi sessione
        </button>
      </div>
      {formOpen && (
        <AttendanceForm employeeId={employeeId} initial={editTarget} onDone={() => { closeForm(); load(); }} onCancel={closeForm} />
      )}
      <div className="space-y-2 mt-3">
        {(items || []).map((it) => (
          <div key={it.id} className="bg-white border border-[#E4E4E1] rounded-md p-3 flex items-center justify-between gap-2 flex-wrap text-[13px]">
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <Timer className="w-4 h-4 text-[#6B6B72] shrink-0" />
                <span className="font-medium">{new Date(it.clock_in).toLocaleDateString("it-IT")}</span>
                <span className="text-[#52525B]">{fmtTime(it.clock_in)} → {it.clock_out ? fmtTime(it.clock_out) : "in corso"}</span>
                {!it.clock_out && (
                  <span className="font-mono text-[10px] uppercase tracking-widest px-1.5 py-0.5 rounded-full bg-[#05966920] text-[#059669]">In servizio</span>
                )}
                {it.corrected_by_admin && (
                  <span className="font-mono text-[10px] uppercase tracking-widest px-1.5 py-0.5 rounded-full bg-[#F3F3F1] text-[#6B6B72]">Corretta</span>
                )}
              </div>
              {it.note && <div className="text-[11px] text-[#6B6B72] mt-0.5">{it.note}</div>}
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <span className="font-cabinet font-bold">{formatDuration(it.clock_in, it.clock_out)}</span>
              <button onClick={() => openEdit(it)} title="Modifica" aria-label="Modifica sessione"
                className="p-1.5 text-[#6B6B72] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded"><Pencil className="w-4 h-4" /></button>
              <button onClick={() => remove(it)} title="Elimina" aria-label="Elimina sessione"
                className="p-1.5 text-[#6B6B72] hover:text-red-500 hover:bg-red-50 rounded"><Trash2 className="w-4 h-4" /></button>
            </div>
          </div>
        ))}
        {items && items.length === 0 && !formOpen && (
          <div className="bg-white border border-[#E4E4E1] rounded-md p-6 text-center text-[#6B6B72] text-[13px]">Nessuna sessione registrata.</div>
        )}
      </div>
    </div>
  );
}

function AttendanceForm({ employeeId, initial, onDone, onCancel }) {
  const [f, setF] = useState({
    clock_in: initial?.clock_in ? format(parseISO(initial.clock_in), "yyyy-MM-dd'T'HH:mm") : format(new Date(), "yyyy-MM-dd'T'HH:mm"),
    clock_out: initial?.clock_out ? format(parseISO(initial.clock_out), "yyyy-MM-dd'T'HH:mm") : "",
    note: initial?.note || "",
  });
  const [saving, setSaving] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!f.clock_in) { toast.error("Inserisci l'orario di ingresso"); return; }
    setSaving(true);
    const payload = {
      clock_in: new Date(f.clock_in).toISOString(),
      clock_out: f.clock_out ? new Date(f.clock_out).toISOString() : null,
      note: f.note,
    };
    try {
      if (initial) {
        await api.patch(`/employees/${employeeId}/attendance/${initial.id}`, payload);
        toast.success("Sessione aggiornata");
      } else {
        await api.post(`/employees/${employeeId}/attendance`, payload);
        toast.success("Sessione aggiunta");
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
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1">Ingresso</label>
          <input type="datetime-local" required value={f.clock_in} onChange={(e) => setF({ ...f, clock_in: e.target.value })}
            className="w-full bg-white border border-[#E4E4E1] rounded-md px-2 py-2 text-[13px]" />
        </div>
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1">Uscita</label>
          <input type="datetime-local" value={f.clock_out} onChange={(e) => setF({ ...f, clock_out: e.target.value })}
            className="w-full bg-white border border-[#E4E4E1] rounded-md px-2 py-2 text-[13px]" />
        </div>
      </div>
      <input value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} placeholder="Note (opzionale)"
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

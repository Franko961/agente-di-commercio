import { useState } from "react";
import { Plus, Trash2, Pencil, AlertTriangle } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../ui/dialog";
import { DEADLINE_TYPE_LABELS, REMINDER_DAY_OPTIONS, daysUntil, deadlineUrgency } from "./constants";

export default function ScadenzeTab({
  deadlines, activeVehicles, automazioniEnabled, reminderDays, toggleReminderDay,
  deadlineOpen, setDeadlineOpen, deadlineEditTarget, setDeadlineEditTarget,
  saveDeadline, deleteDeadline, emptyDeadline,
}) {
  return (
    <div>
      {automazioniEnabled ? (
        <div className="bg-white border border-[#E4E4E1] rounded-md p-4 mb-4 flex flex-wrap items-center gap-4">
          <div className="font-mono text-[11px] uppercase tracking-widest text-[#52525B]">Promemoria automatici</div>
          {REMINDER_DAY_OPTIONS.map((day) => (
            <label key={day} className="flex items-center gap-1.5 text-[13px] cursor-pointer">
              <input type="checkbox" checked={reminderDays.includes(day)} onChange={() => toggleReminderDay(day)} />
              {day} giorni prima
            </label>
          ))}
        </div>
      ) : (
        <div className="bg-[#F9F9F8] border border-[#E4E4E1] rounded-md p-4 mb-4 text-[13px] text-[#6B6B72]">
          Attiva il modulo Automazioni per i promemoria automatici delle scadenze.
        </div>
      )}
      <div className="flex justify-end mb-4">
        <Dialog open={deadlineOpen} onOpenChange={setDeadlineOpen}>
          <DialogTrigger asChild>
            <button className="flex items-center gap-2 px-4 py-2.5 bg-[#0A192F] text-white rounded-md text-[13px] font-medium">
              <Plus className="w-4 h-4" /> Nuova scadenza
            </button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Nuova scadenza</DialogTitle></DialogHeader>
            <DeadlineForm initial={emptyDeadline} vehicles={activeVehicles} onSave={saveDeadline} />
          </DialogContent>
        </Dialog>
      </div>
      <Dialog open={!!deadlineEditTarget} onOpenChange={(v) => !v && setDeadlineEditTarget(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Modifica scadenza</DialogTitle></DialogHeader>
          {deadlineEditTarget && <DeadlineForm initial={deadlineEditTarget} vehicles={activeVehicles} onSave={saveDeadline} submitLabel="Aggiorna" />}
        </DialogContent>
      </Dialog>

      <div className="space-y-2">
        {deadlines.map((d) => {
          const days = daysUntil(d.due_date);
          const urgency = deadlineUrgency(days);
          return (
            <div key={d.id} className="bg-white border border-[#E4E4E1] rounded-md p-4 flex items-center justify-between gap-3 flex-wrap">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-cabinet font-bold text-[14px]">{d.vehicle_plate}</span>
                  <span className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72]">{DEADLINE_TYPE_LABELS[d.type]}</span>
                </div>
                <div className="text-[12px] text-[#52525B] mt-1">{d.due_date}</div>
                {d.note && <div className="text-[12px] text-[#52525B] mt-1 italic">"{d.note}"</div>}
                <div className="flex items-center gap-1.5 mt-1.5 text-[12px] font-medium" style={{ color: urgency.color }}>
                  {days < 0 && <AlertTriangle className="w-3.5 h-3.5 shrink-0" />}
                  {urgency.label}
                </div>
              </div>
              <div className="flex gap-1">
                <button onClick={() => setDeadlineEditTarget(d)} title="Modifica" aria-label="Modifica scadenza"
                  className="p-1.5 text-[#6B6B72] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded"><Pencil className="w-4 h-4" /></button>
                <button onClick={() => deleteDeadline(d.id)} title="Elimina" aria-label="Elimina scadenza"
                  className="p-1.5 text-[#6B6B72] hover:text-red-500 hover:bg-red-50 rounded"><Trash2 className="w-4 h-4" /></button>
              </div>
            </div>
          );
        })}
        {deadlines.length === 0 && (
          <div className="bg-white border border-[#E4E4E1] rounded-md p-8 text-center text-[#6B6B72] text-[13px]">Nessuna scadenza registrata.</div>
        )}
      </div>
    </div>
  );
}

function DeadlineForm({ initial, vehicles, onSave, submitLabel = "Salva" }) {
  const [f, setF] = useState({
    vehicle_id: initial.vehicle_id || (vehicles[0]?.id || ""), type: initial.type || "assicurazione",
    due_date: initial.due_date || "", note: initial.note || "",
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
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Tipo *</label>
        <select value={f.type} onChange={(e) => setF({ ...f, type: e.target.value })}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
          {Object.entries(DEADLINE_TYPE_LABELS).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
        </select>
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Scadenza *</label>
        <input required type="date" value={f.due_date} onChange={(e) => setF({ ...f, due_date: e.target.value })}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Note</label>
        <textarea value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} rows={2}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      </div>
      <button type="submit" className="w-full bg-[#0A192F] text-white py-2.5 rounded-md text-[13px] font-medium">{submitLabel}</button>
    </form>
  );
}

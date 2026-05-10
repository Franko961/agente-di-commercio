import { useEffect, useState } from "react";
import api from "../api";
import { Plus, Trash2, MapPin, Pencil } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../components/ui/dialog";
import { format, parseISO, startOfWeek, addDays, isSameDay } from "date-fns";
import { it } from "date-fns/locale";
import { toast } from "sonner";

export default function Agenda() {
  const [appts, setAppts] = useState([]);
  const [clients, setClients] = useState([]);
  const [open, setOpen] = useState(false);
  const [editTarget, setEditTarget] = useState(null);
  const [base, setBase] = useState(new Date());

  const load = async () => {
    const [a, c] = await Promise.all([api.get("/appointments"), api.get("/clients")]);
    setAppts(a.data); setClients(c.data);
  };
  useEffect(() => { load(); }, []);

  const weekStart = startOfWeek(base, { weekStartsOn: 1 });
  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));

  const deleteAppt = async (id) => {
    if (!window.confirm("Eliminare questo appuntamento?")) return;
    await api.delete(`/appointments/${id}`);
    toast.success("Appuntamento eliminato");
    load();
  };

  return (
    <div className="p-4 md:p-8">
      <div className="flex items-end justify-between border-b border-[#E4E4E1] pb-6 mb-6">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00] mb-2">Pianificazione</div>
          <h1 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight">Agenda & Visite</h1>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <button data-testid="new-appt-button" className="flex items-center gap-2 px-4 py-2.5 bg-[#0A192F] text-white rounded-md text-[13px] font-medium">
              <Plus className="w-4 h-4" /> Nuovo appuntamento
            </button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Nuovo appuntamento</DialogTitle></DialogHeader>
            <ApptForm clients={clients} onSave={async (f) => { await api.post("/appointments", f); load(); toast.success("Appuntamento creato"); setOpen(false); }} />
          </DialogContent>
        </Dialog>
      </div>

      {/* Dialog modifica */}
      <Dialog open={!!editTarget} onOpenChange={(v) => !v && setEditTarget(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Modifica appuntamento</DialogTitle></DialogHeader>
          {editTarget && (
            <ApptForm clients={clients} initial={editTarget} submitLabel="Aggiorna" onSave={async (f) => {
              await api.put(`/appointments/${editTarget.id}`, f);
              load(); toast.success("Appuntamento aggiornato"); setEditTarget(null);
            }} />
          )}
        </DialogContent>
      </Dialog>

      {/* Week navigation */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <button onClick={() => setBase(addDays(base, -7))} className="px-3 py-1.5 border border-[#E4E4E1] rounded-md text-[12px]">←</button>
          <button onClick={() => setBase(new Date())} className="px-3 py-1.5 border border-[#E4E4E1] rounded-md text-[12px] font-medium">Oggi</button>
          <button onClick={() => setBase(addDays(base, 7))} className="px-3 py-1.5 border border-[#E4E4E1] rounded-md text-[12px]">→</button>
        </div>
        <div className="font-cabinet font-bold text-lg">
          {format(weekStart, "d MMM", { locale: it })} – {format(addDays(weekStart, 6), "d MMM yyyy", { locale: it })}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-7 gap-2">
        {days.map((d, i) => {
          const dayAppts = appts.filter(a => isSameDay(parseISO(a.start), d));
          const isToday = isSameDay(d, new Date());
          return (
            <div key={i} data-testid={`day-col-${format(d, "yyyy-MM-dd")}`} className={`bg-white border rounded-md p-3 min-h-[140px] ${isToday ? "border-[#FF5A00]" : "border-[#E4E4E1]"}`}>
              <div className="mb-3 pb-2 border-b border-[#E4E4E1]">
                <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA]">{format(d, "EEEE", { locale: it })}</div>
                <div className="font-cabinet font-black text-2xl">{format(d, "d")}</div>
              </div>
              <div className="space-y-2">
                {dayAppts.length === 0 && <div className="text-[11px] text-[#A1A1AA]">—</div>}
                {dayAppts.map((a) => {
                  const cli = clients.find(c => c.id === a.client_id);
                  return (
                    <div key={a.id} data-testid={`appt-${a.id}`} className="bg-[#F9F9F8] border-l-2 border-[#FF5A00] p-2 rounded-r-md">
                      <div className="font-mono text-[10px] text-[#FF5A00] font-bold">{format(parseISO(a.start), "HH:mm")}</div>
                      <div className="text-[12px] font-medium leading-tight mt-0.5">{a.title}</div>
                      {cli && <div className="text-[10px] text-[#52525B] mt-1 flex items-center gap-1"><MapPin className="w-2.5 h-2.5" />{cli.company_name}</div>}
                      <div className="flex gap-2 mt-1.5">
                        <button onClick={() => setEditTarget({ ...a, start: format(parseISO(a.start), "yyyy-MM-dd'T'HH:mm") })}
                          className="text-[10px] text-[#A1A1AA] hover:text-[#0A192F] flex items-center gap-0.5">
                          <Pencil className="w-2.5 h-2.5" /> modifica
                        </button>
                        <button onClick={() => deleteAppt(a.id)} className="text-[10px] text-[#A1A1AA] hover:text-red-500 flex items-center gap-0.5">
                          <Trash2 className="w-2.5 h-2.5" /> elimina
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ApptForm({ clients, initial, onSave, submitLabel = "Salva appuntamento" }) {
  const [f, setF] = useState(initial || {
    client_id: "", title: "", description: "",
    start: format(new Date(), "yyyy-MM-dd'T'HH:mm"),
    location: "", status: "pianificato"
  });
  useEffect(() => { if (initial) setF(initial); }, [initial]);

  return (
    <form onSubmit={async (e) => {
      e.preventDefault();
      const start = new Date(f.start).toISOString();
      await onSave({ ...f, start });
    }} className="space-y-3">
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Cliente</label>
        <select value={f.client_id} onChange={(e) => setF({ ...f, client_id: e.target.value })}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
          <option value="">— seleziona —</option>
          {clients.map(c => <option key={c.id} value={c.id}>{c.company_name}</option>)}
        </select>
      </div>
      <Field label="Titolo *" v={f.title} on={(v) => setF({ ...f, title: v })} required />
      <Field label="Data e ora" v={f.start} on={(v) => setF({ ...f, start: v })} type="datetime-local" />
      <Field label="Luogo" v={f.location} on={(v) => setF({ ...f, location: v })} />
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Stato</label>
        <select value={f.status} onChange={(e) => setF({ ...f, status: e.target.value })}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
          <option value="pianificato">Pianificato</option>
          <option value="completato">Completato</option>
          <option value="annullato">Annullato</option>
        </select>
      </div>
      <button data-testid="save-appt-button" type="submit" className="w-full bg-[#0A192F] text-white py-2.5 rounded-md text-[13px] font-medium">{submitLabel}</button>
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

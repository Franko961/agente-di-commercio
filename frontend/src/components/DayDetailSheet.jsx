import { useEffect, useState } from "react";
import { format, parseISO } from "date-fns";
import { toast } from "sonner";
import { ChevronLeft, ChevronRight, Plus, Pencil, Trash2, Timer } from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "./ui/sheet";
import api from "../api";

const ADMIN_TYPE_LABELS = { smartworking: "Smartworking", trasferta: "Trasferta", straordinari: "Straordinari", reperibilita: "Reperibilità" };
const ADMIN_TYPE_COLORS = { smartworking: "#D97706", trasferta: "#78350F", straordinari: "#DB2777", reperibilita: "#6366F1" };
const TYPE_LABELS = { ferie: "Ferie", permesso: "Permesso", malattia: "Malattia", ...ADMIN_TYPE_LABELS };
const TYPE_COLORS = { ferie: "#B23E00", permesso: "#0A192F", malattia: "#DC2626", ...ADMIN_TYPE_COLORS };

// Stesso helper di EmployeeDetailSheet.jsx (duplicato qui apposta: un file
// più piccolo e indipendente è preferibile a un import incrociato per una
// manciata di righe pure senza stato condiviso).
function formatApiError(err, fallback = "Operazione non riuscita") {
  const detail = err?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail.map((e) => (e?.msg || "").replace(/^Value error,\s*/, "")).filter(Boolean).join(" · ") || fallback;
  }
  return fallback;
}

function fmtTime(iso) {
  return new Date(iso).toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" });
}

// clock_in è salvato in UTC (vedi backend/core/utils.local_date_str, la
// stessa conversione lato server): una timbratura delle 00:30 italiane del
// 1° agosto è "2026-07-31T22:30:00+00:00" in UTC — un confronto con
// .slice(0,10) sulla stringa grezza la attribuirebbe al 31 luglio invece
// che al 1° agosto. new Date(iso) interpreta correttamente l'offset UTC e
// getFullYear/getMonth/getDate leggono poi l'ora locale del browser.
function localDateStr(iso) {
  const d = new Date(iso);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function formatDuration(clockIn, clockOut) {
  if (!clockOut) return "in corso";
  const totalMinutes = Math.round((new Date(clockOut) - new Date(clockIn)) / 60000);
  return `${Math.floor(totalMinutes / 60)}h ${totalMinutes % 60}m`;
}

function dateLabel(iso) {
  const d = new Date(`${iso}T00:00:00`);
  const label = d.toLocaleDateString("it-IT", { weekday: "long", day: "numeric", month: "long" });
  return label.charAt(0).toUpperCase() + label.slice(1);
}

// Pannello di dettaglio giorno×dipendente, aperto cliccando una cella della
// griglia in Presenze.jsx: mostra le sessioni presenze (timbrature/correzioni
// manuali, endpoint già usati da EmployeeDetailSheet/PresenzeTab) e i
// giustificativi (leave_requests) di quel giorno, con la possibilità di
// aggiungere/modificare/eliminare entrambi senza uscire dalla griglia.
export default function DayDetailSheet({ employeeId, employeeName, date, requests, canGoPrev, canGoNext, onNavigate, onClose, onChanged }) {
  const [sessions, setSessions] = useState(null);
  const [sessionForm, setSessionForm] = useState(null); // null=chiuso, {}=nuova, {...sessione}=modifica
  const [requestFormOpen, setRequestFormOpen] = useState(false);

  const loadSessions = async () => {
    const { data } = await api.get(`/employees/${employeeId}/attendance`);
    setSessions(data.filter((s) => localDateStr(s.clock_in) === date));
  };
  useEffect(() => {
    loadSessions();
    setSessionForm(null);
    setRequestFormOpen(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [employeeId, date]);

  const deleteSession = async (s) => {
    if (!window.confirm("Eliminare questa presenza?")) return;
    try {
      await api.delete(`/employees/${employeeId}/attendance/${s.id}`);
      toast.success("Presenza eliminata");
      loadSessions();
      onChanged();
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  const deleteRequest = async (r) => {
    if (!window.confirm(`Eliminare "${TYPE_LABELS[r.type] || r.type}"?`)) return;
    try {
      await api.delete(`/leave-requests/${r.id}`);
      toast.success("Giustificativo eliminato");
      onChanged();
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  return (
    <Sheet open onOpenChange={(v) => !v && onClose()}>
      <SheetContent side="right" className="w-full sm:max-w-md p-0 flex flex-col">
        <SheetHeader className="p-6 pb-4 border-b border-[#E4E4E1] space-y-0">
          <SheetTitle className="sr-only">Dettaglio giornata</SheetTitle>
          <div className="flex items-center justify-between gap-2 pr-6">
            <button onClick={() => onNavigate(-1)} disabled={!canGoPrev}
              className="p-1.5 rounded hover:bg-[#F3F3F1] disabled:opacity-30" aria-label="Giorno precedente">
              <ChevronLeft className="w-4 h-4" />
            </button>
            <div className="text-center">
              <div className="font-cabinet font-bold text-[15px]">{employeeName}</div>
              <div className="text-[12px] text-[#52525B]">{dateLabel(date)}</div>
            </div>
            <button onClick={() => onNavigate(1)} disabled={!canGoNext}
              className="p-1.5 rounded hover:bg-[#F3F3F1] disabled:opacity-30" aria-label="Giorno successivo">
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <section>
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-mono text-[10px] uppercase tracking-widest text-[#52525B]">Presenza</h3>
              <button onClick={() => setSessionForm({})} className="flex items-center gap-1 text-[11px] font-medium text-[#0A192F] hover:underline">
                <Plus className="w-3.5 h-3.5" /> Aggiungi
              </button>
            </div>
            {sessionForm && (
              <SessionForm employeeId={employeeId} date={date} initial={sessionForm.id ? sessionForm : null}
                onDone={() => { setSessionForm(null); loadSessions(); onChanged(); }} onCancel={() => setSessionForm(null)} />
            )}
            <div className="space-y-2">
              {(sessions || []).map((s) => (
                <div key={s.id} className="bg-white border border-[#E4E4E1] rounded-md p-3 flex items-center justify-between gap-2 text-[13px]">
                  <div className="flex items-center gap-2 min-w-0">
                    <Timer className="w-4 h-4 text-[#6B6B72] shrink-0" />
                    <span>{fmtTime(s.clock_in)} → {s.clock_out ? fmtTime(s.clock_out) : "in corso"}</span>
                    <span className="text-[#6B6B72] text-[11px]">({formatDuration(s.clock_in, s.clock_out)})</span>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <button onClick={() => setSessionForm(s)} className="p-1.5 text-[#6B6B72] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded" aria-label="Modifica presenza">
                      <Pencil className="w-3.5 h-3.5" />
                    </button>
                    <button onClick={() => deleteSession(s)} className="p-1.5 text-[#6B6B72] hover:text-red-500 hover:bg-red-50 rounded" aria-label="Elimina presenza">
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
              {sessions && sessions.length === 0 && !sessionForm && (
                <div className="text-[12px] text-[#6B6B72]">Nessuna presenza registrata.</div>
              )}
            </div>
          </section>

          <section>
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-mono text-[10px] uppercase tracking-widest text-[#52525B]">Giustificativi</h3>
              <button onClick={() => setRequestFormOpen(true)} className="flex items-center gap-1 text-[11px] font-medium text-[#0A192F] hover:underline">
                <Plus className="w-3.5 h-3.5" /> Aggiungi
              </button>
            </div>
            <p className="text-[11px] text-[#6B6B72] mb-2">
              Ferie/Permesso/Malattia si gestiscono dal link personale del dipendente o dalla scheda in Personale — qui puoi solo eliminarli. Gli altri tipi si registrano direttamente.
            </p>
            {requestFormOpen && (
              <RequestForm employeeId={employeeId} date={date}
                onDone={() => { setRequestFormOpen(false); onChanged(); }} onCancel={() => setRequestFormOpen(false)} />
            )}
            <div className="space-y-2">
              {requests.map((r) => (
                <div key={r.id} className="rounded-md p-3 flex items-center justify-between gap-2 text-[13px]"
                  style={{ background: `${TYPE_COLORS[r.type] || "#52525B"}15` }}>
                  <div className="min-w-0">
                    <span className="font-medium" style={{ color: TYPE_COLORS[r.type] || "#52525B" }}>{TYPE_LABELS[r.type] || r.type}</span>
                    {r.hours ? <span className="text-[#52525B] text-[12px] ml-2">{r.hours}h</span> : null}
                    {r.note ? <div className="text-[11px] text-[#52525B] mt-0.5">{r.note}</div> : null}
                  </div>
                  <button onClick={() => deleteRequest(r)} className="p-1.5 text-[#6B6B72] hover:text-red-500 hover:bg-red-50 rounded shrink-0" aria-label="Elimina giustificativo">
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
              {requests.length === 0 && !requestFormOpen && (
                <div className="text-[12px] text-[#6B6B72]">Nessun giustificativo per questo giorno.</div>
              )}
            </div>
          </section>
        </div>
      </SheetContent>
    </Sheet>
  );
}

function SessionForm({ employeeId, date, initial, onDone, onCancel }) {
  const [f, setF] = useState({
    clock_in: initial?.clock_in ? format(parseISO(initial.clock_in), "HH:mm") : "09:00",
    clock_out: initial?.clock_out ? format(parseISO(initial.clock_out), "HH:mm") : "",
  });
  const [saving, setSaving] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!f.clock_in) { toast.error("Inserisci l'orario di ingresso"); return; }
    setSaving(true);
    const payload = {
      clock_in: new Date(`${date}T${f.clock_in}:00`).toISOString(),
      clock_out: f.clock_out ? new Date(`${date}T${f.clock_out}:00`).toISOString() : null,
    };
    try {
      if (initial) {
        await api.patch(`/employees/${employeeId}/attendance/${initial.id}`, payload);
        toast.success("Presenza aggiornata");
      } else {
        await api.post(`/employees/${employeeId}/attendance`, payload);
        toast.success("Presenza aggiunta");
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
          <input type="time" required value={f.clock_in} onChange={(e) => setF({ ...f, clock_in: e.target.value })}
            className="w-full bg-white border border-[#E4E4E1] rounded-md px-2 py-2 text-[13px]" />
        </div>
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1">Uscita</label>
          <input type="time" value={f.clock_out} onChange={(e) => setF({ ...f, clock_out: e.target.value })}
            className="w-full bg-white border border-[#E4E4E1] rounded-md px-2 py-2 text-[13px]" />
        </div>
      </div>
      <div className="flex gap-2">
        <button type="submit" disabled={saving} className="flex-1 bg-[#0A192F] text-white py-2 rounded-md text-[12px] font-medium disabled:opacity-60">
          {saving ? "Salvataggio…" : initial ? "Aggiorna" : "Aggiungi"}
        </button>
        <button type="button" onClick={onCancel} className="px-4 py-2 border border-[#E4E4E1] rounded-md text-[12px] font-medium">Annulla</button>
      </div>
    </form>
  );
}

function RequestForm({ employeeId, date, onDone, onCancel }) {
  const [f, setF] = useState({ type: "smartworking", hours: "", note: "" });
  const [saving, setSaving] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    const payload = {
      type: f.type,
      date_from: date,
      date_to: date,
      hours: f.hours ? Number(f.hours) : null,
      note: f.note,
    };
    try {
      await api.post(`/employees/${employeeId}/leave-requests`, payload);
      toast.success("Giustificativo aggiunto");
      onDone();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={submit} className="bg-[#F9F9F8] border border-[#E4E4E1] rounded-md p-3 space-y-2.5 mb-3">
      <select value={f.type} onChange={(e) => setF({ ...f, type: e.target.value })}
        className="w-full bg-white border border-[#E4E4E1] rounded-md px-2 py-2 text-[13px]">
        {Object.entries(ADMIN_TYPE_LABELS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
      </select>
      <input type="number" min="0.5" max="24" step="0.5" value={f.hours} onChange={(e) => setF({ ...f, hours: e.target.value })}
        placeholder="Ore (opzionale)" className="w-full bg-white border border-[#E4E4E1] rounded-md px-2 py-2 text-[13px]" />
      <input value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} placeholder="Note (opzionale)"
        className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      <div className="flex gap-2">
        <button type="submit" disabled={saving} className="flex-1 bg-[#0A192F] text-white py-2 rounded-md text-[12px] font-medium disabled:opacity-60">
          {saving ? "Salvataggio…" : "Aggiungi"}
        </button>
        <button type="button" onClick={onCancel} className="px-4 py-2 border border-[#E4E4E1] rounded-md text-[12px] font-medium">Annulla</button>
      </div>
    </form>
  );
}

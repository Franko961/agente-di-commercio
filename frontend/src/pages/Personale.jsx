import { useEffect, useState } from "react";
import {
  Plus, Trash2, Pencil, Check, X, Link2, Download, Clock,
  CalendarDays, Users, ChevronLeft, ChevronRight,
} from "lucide-react";
import { toast } from "sonner";
import api from "../api";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../components/ui/dialog";
import { exportLeaveRequests } from "../utils/export";

const TYPE_LABELS = { ferie: "Ferie", permesso: "Permesso", malattia: "Malattia" };
const TYPE_COLORS = { ferie: "#FF5A00", permesso: "#0A192F", malattia: "#DC2626" };
const STATUS_LABELS = { in_attesa: "In attesa", approvata: "Approvata", rifiutata: "Rifiutata" };
const STATUS_COLORS = { in_attesa: "#FF5A00", approvata: "#059669", rifiutata: "#DC2626" };

const EMPTY_EMPLOYEE = { name: "", role: "", email: "" };

function monthKeyToday() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export default function Personale() {
  const [tab, setTab] = useState("richieste"); // richieste | dipendenti | calendario
  const [employees, setEmployees] = useState([]);
  const [requests, setRequests] = useState([]);
  const [open, setOpen] = useState(false);
  const [editTarget, setEditTarget] = useState(null);
  const [month, setMonth] = useState(monthKeyToday());
  const [calendarRows, setCalendarRows] = useState([]);

  const loadEmployees = async () => {
    const { data } = await api.get("/employees");
    setEmployees(data);
  };
  const loadRequests = async () => {
    const { data } = await api.get("/leave-requests");
    setRequests(data);
  };
  const loadCalendar = async (m) => {
    const { data } = await api.get("/leave-requests/calendar", { params: { month: m } });
    setCalendarRows(data);
  };

  useEffect(() => { loadEmployees(); loadRequests(); }, []);
  useEffect(() => { loadCalendar(month); }, [month]);

  const pending = requests.filter((r) => r.status === "in_attesa");
  const decided = requests.filter((r) => r.status !== "in_attesa");

  const decide = async (id, status) => {
    try {
      await api.patch(`/leave-requests/${id}/decision`, { status });
      toast.success(status === "approvata" ? "Richiesta approvata" : "Richiesta rifiutata");
      loadRequests();
      loadCalendar(month);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Operazione non riuscita");
    }
  };

  const saveEmployee = async (f) => {
    if (editTarget) {
      await api.put(`/employees/${editTarget.id}`, f);
      toast.success("Dipendente aggiornato");
      setEditTarget(null);
    } else {
      await api.post("/employees", f);
      toast.success("Dipendente aggiunto");
      setOpen(false);
    }
    loadEmployees();
  };

  const deleteEmployee = async (id, name) => {
    if (!window.confirm(`Eliminare "${name}"? Le richieste già inviate restano nello storico.`)) return;
    await api.delete(`/employees/${id}`);
    toast.success("Dipendente eliminato");
    loadEmployees();
  };

  const copyLink = (token) => {
    const url = `${window.location.origin}/richiedi-assenza/${token}`;
    navigator.clipboard.writeText(url);
    toast.success("Link copiato — condividilo con il dipendente");
  };

  const exportCsv = async () => {
    try {
      await exportLeaveRequests();
    } catch {
      toast.error("Esportazione non riuscita");
    }
  };

  const shiftMonth = (delta) => {
    const [y, m] = month.split("-").map(Number);
    const d = new Date(y, m - 1 + delta, 1);
    setMonth(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`);
  };
  const monthLabel = (() => {
    const [y, m] = month.split("-").map(Number);
    const label = new Intl.DateTimeFormat("it-IT", { month: "long", year: "numeric" }).format(new Date(y, m - 1, 1));
    return label.charAt(0).toUpperCase() + label.slice(1);
  })();

  return (
    <div className="p-4 md:p-8">
      <div className="flex items-end justify-between border-b border-[#E4E4E1] pb-6 mb-6 flex-wrap gap-3">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00] mb-2">Gestione Personale</div>
          <h1 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight">Personale</h1>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={exportCsv} className="flex items-center gap-2 px-3 py-2.5 border border-[#E4E4E1] rounded-md text-[13px] font-medium hover:border-[#0A192F]">
            <Download className="w-4 h-4" /> Esporta CSV
          </button>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <button data-testid="new-employee-button" className="flex items-center gap-2 px-4 py-2.5 bg-[#0A192F] text-white rounded-md text-[13px] font-medium">
                <Plus className="w-4 h-4" /> Nuovo dipendente
              </button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader><DialogTitle>Nuovo dipendente</DialogTitle></DialogHeader>
              <EmployeeForm initial={EMPTY_EMPLOYEE} onSave={saveEmployee} />
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <Dialog open={!!editTarget} onOpenChange={(v) => !v && setEditTarget(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Modifica dipendente</DialogTitle></DialogHeader>
          {editTarget && <EmployeeForm initial={editTarget} onSave={saveEmployee} submitLabel="Aggiorna" />}
        </DialogContent>
      </Dialog>

      <div className="flex items-center gap-1 mb-6 border-b border-[#E4E4E1] overflow-x-auto">
        {[
          ["richieste", "Richieste", Clock, pending.length],
          ["dipendenti", "Dipendenti", Users, 0],
          ["calendario", "Calendario", CalendarDays, 0],
        ].map(([key, label, Icon, badge]) => (
          <button key={key} onClick={() => setTab(key)}
            className={`flex items-center gap-1.5 px-3 py-2.5 text-[13px] font-medium whitespace-nowrap border-b-2 -mb-px transition-colors ${
              tab === key ? "border-[#FF5A00] text-[#0A192F]" : "border-transparent text-[#A1A1AA] hover:text-[#52525B]"
            }`}>
            <Icon className="w-3.5 h-3.5" /> {label}
            {badge > 0 && <span className="ml-1 px-1.5 py-0.5 rounded-full bg-[#FF5A00] text-white text-[10px] font-bold">{badge}</span>}
          </button>
        ))}
      </div>

      {tab === "richieste" && (
        <div className="space-y-6">
          {pending.length > 0 && (
            <div>
              <div className="font-mono text-[11px] uppercase tracking-widest text-[#52525B] mb-3">In attesa di decisione</div>
              <div className="space-y-2">
                {pending.map((r) => (
                  <div key={r.id} data-testid={`leave-request-${r.id}`} className="bg-white border border-[#E4E4E1] rounded-md p-4 flex items-center justify-between gap-3 flex-wrap">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full" style={{ background: TYPE_COLORS[r.type] }} />
                        <span className="font-cabinet font-bold text-[14px]">{r.employee_name}</span>
                        <span className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA]">{TYPE_LABELS[r.type]}</span>
                      </div>
                      <div className="text-[12px] text-[#52525B] mt-1">{r.date_from} → {r.date_to}</div>
                      {r.note && <div className="text-[12px] text-[#52525B] mt-1 italic">"{r.note}"</div>}
                    </div>
                    <div className="flex gap-2">
                      <button onClick={() => decide(r.id, "approvata")} data-testid={`approve-${r.id}`}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-[#059669] text-white rounded-md text-[12px] font-medium">
                        <Check className="w-3.5 h-3.5" /> Approva
                      </button>
                      <button onClick={() => decide(r.id, "rifiutata")} data-testid={`reject-${r.id}`}
                        className="flex items-center gap-1.5 px-3 py-1.5 border border-[#E4E4E1] hover:border-[#DC2626] hover:text-[#DC2626] rounded-md text-[12px] font-medium">
                        <X className="w-3.5 h-3.5" /> Rifiuta
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          <div>
            <div className="font-mono text-[11px] uppercase tracking-widest text-[#52525B] mb-3">Storico decisioni</div>
            {decided.length === 0 ? (
              <div className="bg-white border border-[#E4E4E1] rounded-md p-8 text-center text-[#A1A1AA] text-[13px]">Nessuna richiesta ancora decisa.</div>
            ) : (
              <div className="space-y-2">
                {decided.map((r) => (
                  <div key={r.id} className="bg-white border border-[#E4E4E1] rounded-md p-3 flex items-center justify-between gap-3 flex-wrap text-[13px]">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full" style={{ background: TYPE_COLORS[r.type] }} />
                      <span className="font-medium">{r.employee_name}</span>
                      <span className="text-[#A1A1AA]">{TYPE_LABELS[r.type]} · {r.date_from} → {r.date_to}</span>
                    </div>
                    <span className="font-mono text-[10px] uppercase tracking-widest" style={{ color: STATUS_COLORS[r.status] }}>
                      {STATUS_LABELS[r.status]}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {tab === "dipendenti" && (
        <div className="space-y-2">
          {employees.map((e) => (
            <div key={e.id} data-testid={`employee-${e.id}`} className="bg-white border border-[#E4E4E1] rounded-md p-4 flex items-center justify-between gap-3 flex-wrap">
              <div>
                <div className="font-cabinet font-bold text-[14px]">{e.name}</div>
                <div className="text-[12px] text-[#52525B]">{e.role || "—"}{e.email ? ` · ${e.email}` : ""}</div>
              </div>
              <div className="flex gap-1">
                <button onClick={() => copyLink(e.request_token)} title="Copia link personale" aria-label="Copia link personale"
                  className="p-1.5 text-[#A1A1AA] hover:text-[#FF5A00] hover:bg-[#FFF3EC] rounded"><Link2 className="w-4 h-4" /></button>
                <button onClick={() => setEditTarget(e)} title="Modifica" aria-label="Modifica dipendente"
                  className="p-1.5 text-[#A1A1AA] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded"><Pencil className="w-4 h-4" /></button>
                <button onClick={() => deleteEmployee(e.id, e.name)} title="Elimina" aria-label="Elimina dipendente"
                  className="p-1.5 text-[#A1A1AA] hover:text-red-500 hover:bg-red-50 rounded"><Trash2 className="w-4 h-4" /></button>
              </div>
            </div>
          ))}
          {employees.length === 0 && (
            <div className="bg-white border border-[#E4E4E1] rounded-md p-8 text-center text-[#A1A1AA] text-[13px]">Nessun dipendente ancora registrato.</div>
          )}
        </div>
      )}

      {tab === "calendario" && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <button onClick={() => shiftMonth(-1)} className="p-2 border border-[#E4E4E1] rounded-md hover:border-[#0A192F]"><ChevronLeft className="w-4 h-4" /></button>
            <span className="font-cabinet font-bold text-[15px]">{monthLabel}</span>
            <button onClick={() => shiftMonth(1)} className="p-2 border border-[#E4E4E1] rounded-md hover:border-[#0A192F]"><ChevronRight className="w-4 h-4" /></button>
          </div>
          {calendarRows.length === 0 ? (
            <div className="bg-white border border-[#E4E4E1] rounded-md p-8 text-center text-[#A1A1AA] text-[13px]">Nessuna assenza approvata in questo mese.</div>
          ) : (
            <div className="space-y-2">
              {calendarRows.map((r) => (
                <div key={r.id} className="bg-white border border-[#E4E4E1] rounded-md p-3 flex items-center gap-3 text-[13px]">
                  <span className="w-2 h-2 rounded-full shrink-0" style={{ background: TYPE_COLORS[r.type] }} />
                  <span className="font-medium">{r.employee_name}</span>
                  <span className="text-[#A1A1AA]">{TYPE_LABELS[r.type]} · {r.date_from} → {r.date_to}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function EmployeeForm({ initial, onSave, submitLabel = "Salva" }) {
  const [f, setF] = useState({ name: initial.name, role: initial.role || "", email: initial.email || "" });

  return (
    <form onSubmit={async (e) => {
      e.preventDefault();
      await onSave({ ...f, email: f.email || null });
    }} className="space-y-3">
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Nome completo *</label>
        <input required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Ruolo</label>
        <input value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Email (opzionale)</label>
        <input type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })}
          placeholder="Per notificargli l'esito delle richieste"
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      </div>
      <button type="submit" className="w-full bg-[#0A192F] text-white py-2.5 rounded-md text-[13px] font-medium">
        {submitLabel}
      </button>
    </form>
  );
}

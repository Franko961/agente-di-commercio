import { useEffect, useState } from "react";
import {
  Plus, Trash2, Check, X, Link2, Download, Clock,
  Users, AlertTriangle, RefreshCw, Power, PowerOff,
} from "lucide-react";
import { toast } from "sonner";
import api from "../api";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../components/ui/dialog";
import { exportLeaveRequests } from "../utils/export";
import EmployeeDetailSheet from "../components/EmployeeDetailSheet";

const TYPE_LABELS = { ferie: "Ferie", permesso: "Permesso", malattia: "Malattia" };
const TYPE_COLORS = { ferie: "#FF5A00", permesso: "#0A192F", malattia: "#DC2626" };
const STATUS_LABELS = { in_attesa: "In attesa", approvata: "Approvata", rifiutata: "Rifiutata" };
const STATUS_COLORS = { in_attesa: "#FF5A00", approvata: "#059669", rifiutata: "#DC2626" };

const EMPTY_EMPLOYEE = { name: "", role: "", email: "" };

export default function Personale() {
  const [tab, setTab] = useState("richieste"); // richieste | dipendenti
  const [employees, setEmployees] = useState([]);
  const [requests, setRequests] = useState([]);
  const [open, setOpen] = useState(false);
  const [detailTarget, setDetailTarget] = useState(null);
  const [newLink, setNewLink] = useState(null); // { name, token } — mostrato una sola volta dopo creazione/rigenerazione
  const [deleteTarget, setDeleteTarget] = useState(null); // dipendente per cui è aperta la scelta disattiva/elimina

  const loadEmployees = async () => {
    const { data } = await api.get("/employees");
    setEmployees(data);
  };
  const loadRequests = async () => {
    const { data } = await api.get("/leave-requests");
    setRequests(data);
  };

  useEffect(() => { loadEmployees(); loadRequests(); }, []);

  const pending = requests.filter((r) => r.status === "in_attesa");
  const decided = requests.filter((r) => r.status !== "in_attesa");

  const decide = async (id, status) => {
    try {
      await api.patch(`/leave-requests/${id}/decision`, { status });
      toast.success(status === "approvata" ? "Richiesta approvata" : "Richiesta rifiutata");
      loadRequests();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Operazione non riuscita");
    }
  };

  const deleteRequest = async (r) => {
    if (!window.confirm(`Eliminare la richiesta di ${TYPE_LABELS[r.type].toLowerCase()} di ${r.employee_name}?`)) return;
    try {
      await api.delete(`/leave-requests/${r.id}`);
      toast.success("Richiesta eliminata");
      loadRequests();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Eliminazione non riuscita");
    }
  };

  const saveEmployee = async (f) => {
    const { data } = await api.post("/employees", f);
    toast.success("Dipendente aggiunto");
    setOpen(false);
    setNewLink({ name: data.name, token: data.request_token });
    loadEmployees();
  };

  const deactivateFromDialog = async () => {
    await toggleActive(deleteTarget);
    setDeleteTarget(null);
  };

  const confirmDelete = async () => {
    await api.delete(`/employees/${deleteTarget.id}`);
    toast.success("Dipendente eliminato");
    setDeleteTarget(null);
    loadEmployees();
  };

  const regenerateToken = async (emp) => {
    if (!window.confirm(`Rigenerare il link di "${emp.name}"? Il link precedente smetterà subito di funzionare.`)) return;
    const { data } = await api.post(`/employees/${emp.id}/regenerate-token`);
    toast.success("Nuovo link generato");
    setNewLink({ name: emp.name, token: data.request_token });
  };

  const toggleActive = async (emp) => {
    await api.patch(`/employees/${emp.id}/active`, { active: !emp.active });
    toast.success(emp.active ? "Dipendente disattivato" : "Dipendente riattivato");
    loadEmployees();
  };

  const copyNewLink = () => {
    const url = `${window.location.origin}/richiedi-assenza/${newLink.token}`;
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

      {detailTarget && (
        <EmployeeDetailSheet
          employee={detailTarget}
          requests={requests}
          onClose={() => setDetailTarget(null)}
          onEmployeeUpdated={loadEmployees}
          onRequestsChanged={loadRequests}
        />
      )}

      <Dialog open={!!newLink} onOpenChange={(v) => !v && setNewLink(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Link personale di {newLink?.name}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <p className="text-[13px] text-[#52525B]">
              Copia e condividi questo link con il dipendente ora: per sicurezza non verrà più mostrato in seguito.
              Se lo perdi, potrai generarne uno nuovo dalla scheda del dipendente (invaliderà quello attuale).
            </p>
            <div className="bg-[#F9F9F8] border border-[#E4E4E1] rounded-md px-3 py-2">
              <code className="text-[12px] break-all">{`${window.location.origin}/richiedi-assenza/${newLink?.token}`}</code>
            </div>
            <button onClick={copyNewLink} className="w-full flex items-center justify-center gap-2 bg-[#0A192F] text-white py-2.5 rounded-md text-[13px] font-medium">
              <Link2 className="w-4 h-4" /> Copia link
            </button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={!!deleteTarget} onOpenChange={(v) => !v && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Rimuovere {deleteTarget?.name}?</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <p className="text-[13px] text-[#52525B]">
              Le richieste già inviate restano comunque nello storico.{" "}
              {deleteTarget?.active && (
                <>Se vuoi solo interrompere l'accesso al link, disattivare è la scelta più sicura: puoi riattivarlo in qualsiasi momento. </>
              )}
              L'eliminazione definitiva invece non può essere annullata.
            </p>
            <div className="flex flex-col gap-2">
              {deleteTarget?.active && (
                <button onClick={deactivateFromDialog} className="w-full flex items-center justify-center gap-2 bg-[#0A192F] text-white py-2.5 rounded-md text-[13px] font-medium">
                  <PowerOff className="w-4 h-4" /> Disattiva dipendente
                </button>
              )}
              <button onClick={confirmDelete} className="w-full flex items-center justify-center gap-2 border border-red-200 text-red-600 py-2.5 rounded-md text-[13px] font-medium hover:bg-red-50">
                <Trash2 className="w-4 h-4" /> Elimina definitivamente
              </button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <div className="flex items-center gap-1 mb-6 border-b border-[#E4E4E1] overflow-x-auto">
        {[
          ["richieste", "Richieste", Clock, pending.length],
          ["dipendenti", "Dipendenti", Users, 0],
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
                      {r.overlaps && (
                        <div className="flex items-center gap-1.5 mt-1.5 text-[12px] text-[#FF5A00]">
                          <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                          Si sovrappone a un'altra richiesta di {r.employee_name}
                        </div>
                      )}
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
                      <button onClick={() => deleteRequest(r)} title="Elimina" aria-label="Elimina richiesta"
                        className="p-1.5 text-[#A1A1AA] hover:text-red-500 hover:bg-red-50 rounded"><Trash2 className="w-4 h-4" /></button>
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
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[10px] uppercase tracking-widest" style={{ color: STATUS_COLORS[r.status] }}>
                        {STATUS_LABELS[r.status]}
                      </span>
                      <button onClick={() => deleteRequest(r)} title="Elimina" aria-label="Elimina richiesta"
                        className="p-1 text-[#A1A1AA] hover:text-red-500 hover:bg-red-50 rounded"><Trash2 className="w-3.5 h-3.5" /></button>
                    </div>
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
            <div key={e.id} data-testid={`employee-${e.id}`} onClick={() => setDetailTarget(e)}
              className="bg-white border border-[#E4E4E1] rounded-md p-4 flex items-center justify-between gap-3 flex-wrap cursor-pointer hover:border-[#0A192F] transition-colors">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-cabinet font-bold text-[14px]">{e.name}</span>
                  {!e.active && (
                    <span className="font-mono text-[10px] uppercase tracking-widest px-1.5 py-0.5 rounded-full bg-[#F3F3F1] text-[#A1A1AA]">Disattivato</span>
                  )}
                </div>
                <div className="text-[12px] text-[#52525B]">{e.role || "—"}{e.email ? ` · ${e.email}` : ""}</div>
                <div className="text-[11px] text-[#A1A1AA] mt-0.5">
                  {e.last_used_at ? `Link usato l'ultima volta il ${new Date(e.last_used_at).toLocaleString("it-IT")}` : "Link non ancora utilizzato"}
                </div>
              </div>
              <div className="flex gap-1" onClick={(evt) => evt.stopPropagation()}>
                <button onClick={() => regenerateToken(e)} title="Rigenera link personale" aria-label="Rigenera link personale"
                  className="p-1.5 text-[#A1A1AA] hover:text-[#FF5A00] hover:bg-[#FFF3EC] rounded"><RefreshCw className="w-4 h-4" /></button>
                <button onClick={() => toggleActive(e)} title={e.active ? "Disattiva" : "Riattiva"} aria-label={e.active ? "Disattiva dipendente" : "Riattiva dipendente"}
                  className="p-1.5 text-[#A1A1AA] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded">
                  {e.active ? <Power className="w-4 h-4" /> : <PowerOff className="w-4 h-4" />}
                </button>
                <button onClick={() => setDeleteTarget(e)} title="Elimina" aria-label="Elimina dipendente"
                  className="p-1.5 text-[#A1A1AA] hover:text-red-500 hover:bg-red-50 rounded"><Trash2 className="w-4 h-4" /></button>
              </div>
            </div>
          ))}
          {employees.length === 0 && (
            <div className="bg-white border border-[#E4E4E1] rounded-md p-8 text-center text-[#A1A1AA] text-[13px]">Nessun dipendente ancora registrato.</div>
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

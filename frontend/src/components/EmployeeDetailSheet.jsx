import { useEffect, useRef, useState } from "react";
import { format, parseISO } from "date-fns";
import { QRCodeSVG } from "qrcode.react";
import { toast } from "sonner";
import {
  User, CalendarDays, Palmtree, Clock, Thermometer, Truck, Link2, BarChart3,
  RefreshCw, Power, PowerOff, Camera, Copy, FileText, Upload, Download, Trash2,
  Package, Plus, Pencil, Wallet, History, Send, Check, X, Sparkles, Timer,
} from "lucide-react";
import { ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "./ui/sheet";
import api from "../api";

const EMPLOYMENT_STATUS_LABELS = { attivo: "Attivo", sospeso: "Sospeso", cessato: "Cessato" };
const EMPLOYMENT_STATUS_COLORS = { attivo: "#059669", sospeso: "#FF5A00", cessato: "#A1A1AA" };
const CURRENT_STATUS_LABELS = { in_ferie: "In ferie", in_malattia: "In malattia" };
const CURRENT_STATUS_COLORS = { in_ferie: "#FF5A00", in_malattia: "#DC2626" };
const LEAVE_TYPE_LABELS = { ferie: "Ferie", permesso: "Permesso", malattia: "Malattia" };
const LEAVE_TYPE_COLORS = { ferie: "#FF5A00", permesso: "#0A192F", malattia: "#DC2626" };
const REQUEST_STATUS_LABELS = { in_attesa: "In attesa", approvata: "Approvata", rifiutata: "Rifiutata" };
const REQUEST_STATUS_COLORS = { in_attesa: "#FF5A00", approvata: "#059669", rifiutata: "#DC2626" };
const DOCUMENT_CATEGORY_LABELS = { contratto: "Contratto", documento_identita: "Documento d'identità", patente: "Patente", altro: "Altro" };
const FILE_BASE = process.env.REACT_APP_BACKEND_URL;
const DOCUMENT_MAX_MB = 50;
const EQUIPMENT_STATUS_LABELS = { consegnato: "Consegnato", restituito: "Restituito" };
const COMPENSATION_TYPE_LABELS = { stipendio: "Stipendio", bonus: "Bonus", rimborso: "Rimborso", altro: "Altro" };
// Indice 0=lunedì … 6=domenica, coerente con date.weekday() lato backend
// (vedi models.employee.work_days e automation_engine._eval_attendance_missing).
const WEEKDAY_LABELS = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"];
const fmtEur = (v) => (v || 0).toLocaleString("it-IT", { style: "currency", currency: "EUR" });

const ACTIVITY_META = {
  assenza_inviata: { label: "Richiesta di assenza inviata", icon: Send, color: "#0A192F" },
  assenza_approvata: { label: "Richiesta di assenza approvata", icon: Check, color: "#059669" },
  assenza_rifiutata: { label: "Richiesta di assenza rifiutata", icon: X, color: "#DC2626" },
  documento_caricato: { label: "Documento caricato", icon: FileText, color: "#0A192F" },
  dotazione_aggiunta: { label: "Dotazione assegnata", icon: Package, color: "#0A192F" },
  dotazione_restituita: { label: "Dotazione restituita", icon: Package, color: "#A1A1AA" },
  compenso_registrato: { label: "Compenso registrato", icon: Wallet, color: "#0A192F" },
};

const TABS = [
  ["info", "Informazioni", User],
  ["assenze", "Assenze", CalendarDays],
  ["ferie", "Ferie", Palmtree],
  ["permessi", "Permessi", Clock],
  ["malattie", "Malattie", Thermometer],
  ["presenze", "Presenze", Timer],
  ["mezzo", "Mezzo", Truck],
  ["dotazione", "Dotazione", Package],
  ["documenti", "Documenti", FileText],
  ["compensi", "Compensi", Wallet],
  ["attivita", "Attività", History],
  ["ai", "AI", Sparkles],
  ["link", "Link", Link2],
  ["kpi", "KPI", BarChart3],
];

// 13 tab in un'unica riga scorrevole erano troppi da scoprire su
// smartphone (facile non accorgersi che ce ne sono altri fuori schermo):
// raggruppati in 5 categorie sempre visibili, ognuna con i propri
// sotto-tab — ogni tab resta raggiungibile in al massimo 2 tocchi, stessa
// struttura su mobile e desktop (a differenza di un menu a tendina solo
// mobile, che avrebbe reso i due layout incoerenti).
const TAB_GROUPS = [
  { key: "profilo", label: "Profilo", icon: User, tabs: ["info", "ai", "link"] },
  { key: "assenze", label: "Assenze", icon: CalendarDays, tabs: ["assenze", "ferie", "permessi", "malattie", "presenze"] },
  { key: "risorse", label: "Risorse", icon: Truck, tabs: ["mezzo", "dotazione", "documenti"] },
  { key: "economia", label: "Economia", icon: Wallet, tabs: ["compensi", "kpi"] },
  { key: "attivita_gruppo", label: "Attività", icon: History, tabs: ["attivita"] },
];

// Estrae un messaggio leggibile da un errore API: FastAPI risponde con una
// stringa per un errore applicativo, ma con una LISTA di errori per un 422
// di Pydantic (es. i @model_validator su employee/employee_equipment/
// attendance) — senza questo l'utente vedeva solo un fallback generico e
// non capiva cosa correggere. Il prefisso "Value error, " è aggiunto
// automaticamente da Pydantic quando l'errore arriva da un model_validator
// che solleva ValueError.
function formatApiError(err, fallback = "Salvataggio non riuscito") {
  const detail = err?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail.map((e) => (e?.msg || "").replace(/^Value error,\s*/, "")).filter(Boolean).join(" · ") || fallback;
  }
  return fallback;
}

// Ridimensiona l'immagine lato client prima di convertirla in data URL: una
// foto profilo non ha bisogno di essere a piena risoluzione, e mandarla
// intera gonfierebbe inutilmente il documento MongoDB (vedi
// PHOTO_MAX_LENGTH in core/validation_limits.py, pensato per una miniatura
// compressa, non per una foto originale da smartphone).
function resizeImageToDataUrl(file, maxDim = 300) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = reject;
    reader.onload = () => {
      const img = new Image();
      img.onerror = reject;
      img.onload = () => {
        const scale = Math.min(1, maxDim / Math.max(img.width, img.height));
        const canvas = document.createElement("canvas");
        canvas.width = Math.round(img.width * scale);
        canvas.height = Math.round(img.height * scale);
        const ctx = canvas.getContext("2d");
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        resolve(canvas.toDataURL("image/jpeg", 0.8));
      };
      img.src = reader.result;
    };
    reader.readAsDataURL(file);
  });
}

export default function EmployeeDetailSheet({ employee, requests, onClose, onEmployeeUpdated, onRequestsChanged }) {
  const [tab, setTab] = useState("info");
  const [detail, setDetail] = useState(null); // { employee, summary, vehicle, next_revisione }
  const [newLink, setNewLink] = useState(null); // { token } — mostrato una sola volta dopo rigenerazione
  const [newPin, setNewPin] = useState(null); // { pin } — mostrato una sola volta dopo generazione

  const loadDetail = async () => {
    const { data } = await api.get(`/employees/${employee.id}/detail`);
    setDetail(data);
  };
  useEffect(() => { loadDetail(); }, [employee.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const emp = detail?.employee || employee;
  const summary = detail?.summary;

  const myRequests = requests.filter((r) => r.employee_id === employee.id)
    .sort((a, b) => b.date_from.localeCompare(a.date_from));

  const refreshAll = async () => {
    await loadDetail();
    onEmployeeUpdated();
  };

  const regenerateToken = async () => {
    if (!window.confirm(`Rigenerare il link di "${emp.name}"? Il link precedente smetterà subito di funzionare.`)) return;
    const { data } = await api.post(`/employees/${emp.id}/regenerate-token`);
    setNewLink({ token: data.request_token });
    toast.success("Nuovo link generato");
    refreshAll();
  };

  const toggleActive = async () => {
    await api.patch(`/employees/${emp.id}/active`, { active: !emp.active });
    toast.success(emp.active ? "Dipendente disattivato" : "Dipendente riattivato");
    refreshAll();
  };

  const setCertificate = async (rid, received) => {
    await api.patch(`/leave-requests/${rid}/certificate`, { certificate_received: received });
    toast.success(received ? "Certificato segnato come ricevuto" : "Certificato segnato come non ricevuto");
    onRequestsChanged();
    loadDetail();
  };

  const copyLink = (token) => {
    const url = `${window.location.origin}/richiedi-assenza/${token}`;
    navigator.clipboard.writeText(url);
    toast.success("Link copiato");
  };

  const regeneratePin = async () => {
    if (emp.has_pin && !window.confirm(`Rigenerare il PIN chiosco di "${emp.name}"? Il PIN precedente smetterà subito di funzionare.`)) return;
    const { data } = await api.post(`/employees/${emp.id}/attendance/pin`);
    setNewPin({ pin: data.pin });
    toast.success("Nuovo PIN generato");
    refreshAll();
  };

  return (
    <Sheet open onOpenChange={(v) => !v && onClose()}>
      <SheetContent side="right" className="w-full sm:max-w-4xl p-0 flex flex-col">
        <SheetHeader className="px-6 pt-6 pb-0">
          <SheetTitle className="sr-only">Scheda dipendente</SheetTitle>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto px-6 pb-6 pt-2">
          <div className="flex flex-col md:flex-row gap-6">
            {/* Colonna dashboard, sempre visibile */}
            <EmployeeSidebar employee={emp} summary={summary} vehicle={detail?.vehicle} />

            {/* Contenuto a tab */}
            <div className="flex-1 min-w-0">
              <div className="mb-4">
                {/* Griglia a colonne fisse (non una riga scorrevole): con
                    solo 5 categorie, tutte devono restare visibili senza
                    scroll anche sullo schermo più stretto — è proprio
                    l'assenza di elementi "fuori schermo" a risolvere il
                    problema originale (13 tab in una riga scorrevole). */}
                <div className="grid grid-cols-5 gap-0.5 border-b border-[#E4E4E1]">
                  {TAB_GROUPS.map((group) => {
                    const isActiveGroup = group.tabs.includes(tab);
                    const GroupIcon = group.icon;
                    return (
                      <button key={group.key} onClick={() => { if (!isActiveGroup) setTab(group.tabs[0]); }}
                        className={`flex flex-col items-center justify-end gap-1 px-1 py-2 text-[11px] font-semibold text-center leading-tight border-b-2 -mb-px transition-colors ${
                          isActiveGroup ? "border-[#FF5A00] text-[#0A192F]" : "border-transparent text-[#A1A1AA] hover:text-[#52525B]"
                        }`}>
                        <GroupIcon className="w-4 h-4 shrink-0" />
                        <span>{group.label}</span>
                      </button>
                    );
                  })}
                </div>
                {(() => {
                  const activeGroup = TAB_GROUPS.find((g) => g.tabs.includes(tab)) || TAB_GROUPS[0];
                  if (activeGroup.tabs.length < 2) return null;
                  return (
                    <div className="flex items-center gap-1 mt-2 overflow-x-auto">
                      {activeGroup.tabs.map((key) => {
                        const [, label, Icon] = TABS.find(([k]) => k === key);
                        return (
                          <button key={key} onClick={() => setTab(key)}
                            className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md text-[11px] font-medium whitespace-nowrap transition-colors ${
                              tab === key ? "bg-[#0A192F] text-white" : "bg-[#F3F3F1] text-[#52525B] hover:bg-[#E4E4E1]"
                            }`}>
                            <Icon className="w-3 h-3" /> {label}
                          </button>
                        );
                      })}
                    </div>
                  );
                })()}
              </div>

              {tab === "info" && <InfoTab employee={emp} onSaved={refreshAll} />}
              {tab === "assenze" && <AssenzeTab requests={myRequests} summary={summary} onDeleted={onRequestsChanged} />}
              {tab === "ferie" && <FerieTab summary={summary} />}
              {tab === "permessi" && <PermessiTab summary={summary} />}
              {tab === "malattie" && <MalattieTab summary={summary} onSetCertificate={setCertificate} />}
              {tab === "presenze" && <PresenzeTab employeeId={employee.id} />}
              {tab === "mezzo" && <MezzoTab vehicle={detail?.vehicle} nextRevisione={detail?.next_revisione} />}
              {tab === "dotazione" && <DotazioneTab employeeId={employee.id} />}
              {tab === "documenti" && <DocumentiTab employeeId={employee.id} />}
              {tab === "compensi" && <CompensiTab employeeId={employee.id} />}
              {tab === "attivita" && <AttivitaTab employeeId={employee.id} />}
              {tab === "ai" && <AiTab employeeId={employee.id} summary={summary} />}
              {tab === "link" && (
                <LinkTab employee={emp} newLink={newLink} onRegenerate={regenerateToken}
                  onToggleActive={toggleActive} onCopy={copyLink}
                  newPin={newPin} onRegeneratePin={regeneratePin} />
              )}
              {tab === "kpi" && <KpiTab summary={summary} />}
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}

function EmployeeSidebar({ employee, summary, vehicle }) {
  const currentStatus = summary?.current_status;
  const statusKey = currentStatus || employee.employment_status || "attivo";
  const statusLabel = CURRENT_STATUS_LABELS[currentStatus] || EMPLOYMENT_STATUS_LABELS[employee.employment_status] || "Attivo";
  const statusColor = CURRENT_STATUS_COLORS[currentStatus] || EMPLOYMENT_STATUS_COLORS[employee.employment_status] || "#059669";

  return (
    <div className="w-full md:w-56 shrink-0 bg-[#F9F9F8] border border-[#E4E4E1] rounded-md p-4 md:sticky md:top-4 self-start">
      <div className="flex flex-col items-center text-center mb-4">
        {employee.photo ? (
          <img src={employee.photo} alt={employee.name} className="w-16 h-16 rounded-full object-cover mb-2 border border-[#E4E4E1]" />
        ) : (
          <div className="w-16 h-16 rounded-full bg-[#0A192F] text-white flex items-center justify-center font-cabinet font-bold text-xl mb-2">
            {employee.name?.[0]?.toUpperCase()}{employee.surname?.[0]?.toUpperCase() || ""}
          </div>
        )}
        <div className="font-cabinet font-bold text-[15px] leading-tight">{employee.name} {employee.surname}</div>
        <div className="text-[12px] text-[#52525B]">{employee.role || "—"}</div>
        <span className="mt-1.5 inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-widest px-2 py-0.5 rounded-full"
          style={{ background: `${statusColor}1A`, color: statusColor }}>
          <span className="w-1.5 h-1.5 rounded-full" style={{ background: statusColor }} /> {statusLabel}
        </span>
      </div>
      <div className="space-y-2.5 text-[12px]">
        <SidebarStat label="Ferie residue" value={summary ? `${summary.ferie.residue} gg` : "—"} />
        <SidebarStat label="Permessi" value={summary ? `${summary.permessi.ore_approvate} h` : "—"} />
        <SidebarStat label="Malattie anno" value={summary ? `${summary.malattie.giorni} gg` : "—"} />
        <SidebarStat label="Ultimo accesso" value={employee.last_used_at ? new Date(employee.last_used_at).toLocaleDateString("it-IT") : "Mai"} />
        {vehicle && <SidebarStat label="Mezzo" value={vehicle.plate} />}
      </div>
    </div>
  );
}

function SidebarStat({ label, value }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-[#A1A1AA]">{label}</span>
      <span className="font-medium text-[#0A192F]">{value}</span>
    </div>
  );
}

function InfoTab({ employee, onSaved }) {
  const [f, setF] = useState({
    name: employee.name || "", surname: employee.surname || "", role: employee.role || "",
    department: employee.department || "", email: employee.email || "", phone: employee.phone || "",
    mobile: employee.mobile || "", birth_date: employee.birth_date || "", hire_date: employee.hire_date || "",
    employment_status: employee.employment_status || "attivo",
    address: employee.address || "", city: employee.city || "", zip_code: employee.zip_code || "", province: employee.province || "",
    notes: employee.notes || "", annual_vacation_days: employee.annual_vacation_days ?? 26,
    photo: employee.photo || null,
    work_days: employee.work_days || [], shift_start_time: employee.shift_start_time || "",
    shift_end_time: employee.shift_end_time || "", unpaid_break_minutes: employee.unpaid_break_minutes ?? 0,
  });
  const [saving, setSaving] = useState(false);
  const fileRef = useRef(null);

  const toggleWorkDay = (day) => {
    setF((prev) => ({
      ...prev,
      work_days: prev.work_days.includes(day) ? prev.work_days.filter((d) => d !== day) : [...prev.work_days, day].sort(),
    }));
  };

  const handlePhoto = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const dataUrl = await resizeImageToDataUrl(file);
      setF({ ...f, photo: dataUrl });
    } catch {
      toast.error("Impossibile caricare l'immagine");
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.put(`/employees/${employee.id}`, {
        ...f,
        email: f.email || null,
        birth_date: f.birth_date || null,
        hire_date: f.hire_date || null,
        // Entrambi vuoti = "nessun orario configurato" (vedi
        // models.employee._valida_orario_contrattuale): un array vuoto o
        // una stringa vuota andrebbero rifiutati dal backend, che si
        // aspetta o entrambi i campi valorizzati o entrambi null.
        work_days: f.work_days.length ? f.work_days : null,
        shift_start_time: f.shift_start_time || null,
        shift_end_time: f.shift_end_time || null,
      });
      toast.success("Informazioni aggiornate");
      onSaved();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setSaving(false);
    }
  };

  const field = (label, key, type = "text") => (
    <div>
      <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">{label}</label>
      <input type={type} value={f[key]} onChange={(e) => setF({ ...f, [key]: e.target.value })}
        className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
    </div>
  );

  return (
    <form onSubmit={submit} className="space-y-5">
      <div className="flex items-center gap-3">
        {f.photo ? (
          <img src={f.photo} alt="" className="w-14 h-14 rounded-full object-cover border border-[#E4E4E1]" />
        ) : (
          <div className="w-14 h-14 rounded-full bg-[#F3F3F1] flex items-center justify-center text-[#A1A1AA]">
            <Camera className="w-5 h-5" />
          </div>
        )}
        <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handlePhoto} />
        <button type="button" onClick={() => fileRef.current?.click()}
          className="px-3 py-2 border border-[#E4E4E1] rounded-md text-[12px] font-medium hover:border-[#0A192F]">
          Cambia foto
        </button>
      </div>

      <div>
        <div className="font-mono text-[11px] uppercase tracking-widest text-[#52525B] mb-2">Dati personali</div>
        <div className="grid grid-cols-2 gap-3">
          {field("Nome *", "name")}
          {field("Cognome", "surname")}
          {field("Ruolo", "role")}
          {field("Reparto", "department")}
          {field("Email", "email", "email")}
          {field("Telefono", "phone")}
          {field("Cellulare", "mobile")}
          {field("Data di nascita", "birth_date", "date")}
          {field("Data di assunzione", "hire_date", "date")}
          <div>
            <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Stato</label>
            <select value={f.employment_status} onChange={(e) => setF({ ...f, employment_status: e.target.value })}
              className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
              {Object.entries(EMPLOYMENT_STATUS_LABELS).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
            </select>
          </div>
          <div>
            <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Ferie spettanti/anno</label>
            <input type="number" min="0" step="0.5" value={f.annual_vacation_days}
              onChange={(e) => setF({ ...f, annual_vacation_days: e.target.value })}
              className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
          </div>
        </div>
      </div>

      <div>
        <div className="font-mono text-[11px] uppercase tracking-widest text-[#52525B] mb-2">Orario contrattuale</div>
        <p className="text-[12px] text-[#52525B] mb-2">
          Giorni e inizio turno servono a segnalare una timbratura mancante (Personale → "Avvisami se un dipendente non timbra").
          La fine turno (facoltativa) abilita anche il confronto ore attese/reali nella griglia Calendario.
          Se lasci tutto vuoto, il dipendente non viene monitorato.
        </p>
        <div className="flex gap-1.5 mb-2">
          {WEEKDAY_LABELS.map((label, day) => (
            <button key={day} type="button" onClick={() => toggleWorkDay(day)}
              className={`flex-1 py-2 rounded-md text-[11px] font-medium border ${
                f.work_days.includes(day) ? "bg-[#0A192F] text-white border-[#0A192F]" : "bg-white border-[#E4E4E1] text-[#52525B]"
              }`}>
              {label}
            </button>
          ))}
        </div>
        <div className="flex gap-3">
          <div className="max-w-[160px]">
            <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Inizio turno</label>
            <input type="time" value={f.shift_start_time} onChange={(e) => setF({ ...f, shift_start_time: e.target.value })}
              className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
          </div>
          <div className="max-w-[160px]">
            <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Fine turno</label>
            <input type="time" value={f.shift_end_time} onChange={(e) => setF({ ...f, shift_end_time: e.target.value })}
              className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
          </div>
          <div className="max-w-[160px]">
            <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Pausa non retribuita (min)</label>
            <input type="number" min="0" max="480" step="5" value={f.unpaid_break_minutes}
              onChange={(e) => setF({ ...f, unpaid_break_minutes: e.target.value === "" ? 0 : Number(e.target.value) })}
              className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
          </div>
        </div>
      </div>

      <div>
        <div className="font-mono text-[11px] uppercase tracking-widest text-[#52525B] mb-2">Contatti</div>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">{field("Indirizzo", "address")}</div>
          {field("Città", "city")}
          {field("CAP", "zip_code")}
          {field("Provincia", "province")}
        </div>
      </div>

      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Note</label>
        <textarea value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} rows={3}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      </div>

      <button type="submit" disabled={saving} className="w-full bg-[#0A192F] text-white py-2.5 rounded-md text-[13px] font-medium disabled:opacity-60">
        {saving ? "Salvataggio…" : "Salva informazioni"}
      </button>
    </form>
  );
}

function AssenzeTab({ requests, summary, onDeleted }) {
  const [filterType, setFilterType] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const filtered = requests.filter((r) => (!filterType || r.type === filterType) && (!filterStatus || r.status === filterStatus));

  const deleteRequest = async (r) => {
    if (!window.confirm(`Eliminare la richiesta di ${LEAVE_TYPE_LABELS[r.type].toLowerCase()}?`)) return;
    try {
      await api.delete(`/leave-requests/${r.id}`);
      toast.success("Richiesta eliminata");
      onDeleted();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Eliminazione non riuscita");
    }
  };

  return (
    <div>
      {summary && (
        <div className="grid grid-cols-3 gap-2 mb-4">
          <MiniStat label="Ferie (gg)" value={summary.ferie.godute} />
          <MiniStat label="Permessi (h)" value={summary.permessi.ore_approvate} />
          <MiniStat label="Malattia (gg)" value={summary.malattie.giorni} />
        </div>
      )}
      <div className="flex gap-2 mb-3">
        <select value={filterType} onChange={(e) => setFilterType(e.target.value)}
          className="border border-[#E4E4E1] rounded-md px-2 py-1.5 text-[12px]">
          <option value="">Tutti i tipi</option>
          {Object.entries(LEAVE_TYPE_LABELS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
        </select>
        <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}
          className="border border-[#E4E4E1] rounded-md px-2 py-1.5 text-[12px]">
          <option value="">Tutti gli stati</option>
          {Object.entries(REQUEST_STATUS_LABELS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
        </select>
      </div>
      <div className="space-y-2">
        {filtered.map((r) => (
          <div key={r.id} className="bg-white border border-[#E4E4E1] rounded-md p-3 text-[13px]">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full" style={{ background: LEAVE_TYPE_COLORS[r.type] }} />
                <span className="font-medium">{LEAVE_TYPE_LABELS[r.type]}</span>
                <span className="text-[#52525B]">{r.date_from} → {r.date_to}</span>
                {r.hours && <span className="text-[#A1A1AA]">({r.hours} h)</span>}
              </div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-[10px] uppercase tracking-widest" style={{ color: REQUEST_STATUS_COLORS[r.status] }}>
                  {REQUEST_STATUS_LABELS[r.status]}
                </span>
                <button onClick={() => deleteRequest(r)} title="Elimina" aria-label="Elimina richiesta"
                  className="p-1 text-[#A1A1AA] hover:text-red-500 hover:bg-red-50 rounded"><Trash2 className="w-3.5 h-3.5" /></button>
              </div>
            </div>
            {r.note && <div className="text-[12px] text-[#52525B] mt-1 italic">"{r.note}"</div>}
          </div>
        ))}
        {filtered.length === 0 && (
          <div className="bg-white border border-[#E4E4E1] rounded-md p-6 text-center text-[#A1A1AA] text-[13px]">Nessuna richiesta.</div>
        )}
      </div>
    </div>
  );
}

function MiniStat({ label, value }) {
  return (
    <div className="bg-white border border-[#E4E4E1] rounded-md p-3 text-center">
      <div className="font-cabinet font-black text-xl">{value}</div>
      <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] mt-0.5">{label}</div>
    </div>
  );
}

function FerieTab({ summary }) {
  if (!summary) return null;
  const { spettanti, godute, residue } = summary.ferie;
  const data = [
    { name: "Godute", value: godute, color: "#FF5A00" },
    { name: "Residue", value: Math.max(residue, 0), color: "#E4E4E1" },
  ];
  return (
    <div>
      <div className="grid grid-cols-3 gap-2 mb-4">
        <MiniStat label="Spettanti" value={spettanti} />
        <MiniStat label="Godute" value={godute} />
        <MiniStat label="Residue" value={residue} />
      </div>
      <div className="bg-white border border-[#E4E4E1] rounded-md p-4 h-56">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80} paddingAngle={2}>
              {data.map((d, i) => <Cell key={i} fill={d.color} />)}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function PermessiTab({ summary }) {
  if (!summary) return null;
  return (
    <div className="grid grid-cols-2 gap-2">
      <MiniStat label="Ore richieste" value={summary.permessi.ore_richieste} />
      <MiniStat label="Ore approvate" value={summary.permessi.ore_approvate} />
    </div>
  );
}

function MalattieTab({ summary, onSetCertificate }) {
  if (!summary) return null;
  return (
    <div>
      <div className="mb-4"><MiniStat label="Giorni malattia (anno)" value={summary.malattie.giorni} /></div>
      <div className="text-[11px] text-[#A1A1AA] mb-3">Nessun dato sanitario: solo date, giorni e conferma di ricezione del certificato.</div>
      <div className="space-y-2">
        {summary.malattie.richieste.map((r) => (
          <div key={r.id} className="bg-white border border-[#E4E4E1] rounded-md p-3 flex items-center justify-between gap-2 flex-wrap text-[13px]">
            <div>
              <div>{r.date_from} → {r.date_to} <span className="text-[#A1A1AA]">({r.giorni} gg)</span></div>
              <span className="font-mono text-[10px] uppercase tracking-widest" style={{ color: REQUEST_STATUS_COLORS[r.status] }}>
                {REQUEST_STATUS_LABELS[r.status]}
              </span>
            </div>
            <button onClick={() => onSetCertificate(r.id, !r.certificate_received)}
              className={`px-2.5 py-1.5 rounded-md text-[12px] font-medium border ${
                r.certificate_received ? "bg-[#059669] text-white border-[#059669]" : "border-[#E4E4E1] text-[#52525B]"
              }`}>
              Certificato: {r.certificate_received ? "Sì" : "No"}
            </button>
          </div>
        ))}
        {summary.malattie.richieste.length === 0 && (
          <div className="bg-white border border-[#E4E4E1] rounded-md p-6 text-center text-[#A1A1AA] text-[13px]">Nessuna richiesta di malattia quest'anno.</div>
        )}
      </div>
    </div>
  );
}

function MezzoTab({ vehicle, nextRevisione }) {
  if (!vehicle) {
    return <div className="bg-white border border-[#E4E4E1] rounded-md p-6 text-center text-[#A1A1AA] text-[13px]">Nessun mezzo assegnato (o modulo Flotta non attivo).</div>;
  }
  return (
    <div className="space-y-2">
      <div className="bg-white border border-[#E4E4E1] rounded-md p-4">
        <div className="font-cabinet font-bold text-[16px]">{vehicle.plate}</div>
        <div className="text-[13px] text-[#52525B] mt-1">{vehicle.model || "—"}</div>
        {vehicle.current_km != null && <div className="text-[13px] text-[#52525B] mt-1">Km attuali: {vehicle.current_km.toLocaleString("it-IT")}</div>}
        {nextRevisione ? (
          <div className="text-[13px] text-[#52525B] mt-1">Prossima revisione: {nextRevisione.due_date}</div>
        ) : (
          <div className="text-[13px] text-[#A1A1AA] mt-1">Nessuna revisione in programma</div>
        )}
      </div>
    </div>
  );
}

function DotazioneTab({ employeeId }) {
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
                <Package className="w-4 h-4 text-[#A1A1AA] shrink-0" />
                <span className="font-medium truncate">{it.name}</span>
                <span className="font-mono text-[10px] uppercase tracking-widest px-1.5 py-0.5 rounded-full shrink-0"
                  style={{ background: it.status === "restituito" ? "#F3F3F1" : "#05966920", color: it.status === "restituito" ? "#A1A1AA" : "#059669" }}>
                  {EQUIPMENT_STATUS_LABELS[it.status]}
                </span>
              </div>
              <div className="text-[11px] text-[#A1A1AA] mt-0.5">
                {it.delivered_date ? `Consegnata il ${it.delivered_date}` : "Data consegna non indicata"}
                {it.returned_date ? ` · Restituita il ${it.returned_date}` : ""}
                {it.notes ? ` · ${it.notes}` : ""}
              </div>
            </div>
            <div className="flex gap-1 shrink-0">
              <button onClick={() => openEdit(it)} title="Modifica" aria-label="Modifica dotazione"
                className="p-1.5 text-[#A1A1AA] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded"><Pencil className="w-4 h-4" /></button>
              <button onClick={() => remove(it)} title="Elimina" aria-label="Elimina dotazione"
                className="p-1.5 text-[#A1A1AA] hover:text-red-500 hover:bg-red-50 rounded"><Trash2 className="w-4 h-4" /></button>
            </div>
          </div>
        ))}
        {items && items.length === 0 && !formOpen && (
          <div className="bg-white border border-[#E4E4E1] rounded-md p-6 text-center text-[#A1A1AA] text-[13px]">Nessuna dotazione assegnata.</div>
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

function CompensiTab({ employeeId }) {
  const [items, setItems] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editTarget, setEditTarget] = useState(null);

  const load = async () => {
    const { data } = await api.get(`/employees/${employeeId}/compensation`);
    setItems(data);
  };
  useEffect(() => { load(); }, [employeeId]); // eslint-disable-line react-hooks/exhaustive-deps

  const openNew = () => { setEditTarget(null); setFormOpen(true); };
  const openEdit = (item) => { setEditTarget(item); setFormOpen(true); };
  const closeForm = () => { setFormOpen(false); setEditTarget(null); };

  const remove = async (item) => {
    if (!window.confirm(`Eliminare il compenso del ${item.date}? Verrà rimossa anche la spesa collegata.`)) return;
    try {
      await api.delete(`/employees/${employeeId}/compensation/${item.id}`);
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
                <Wallet className="w-4 h-4 text-[#A1A1AA] shrink-0" />
                <span className="font-medium">{COMPENSATION_TYPE_LABELS[it.type] || it.type}</span>
                <span className="text-[#52525B]">{it.date}</span>
              </div>
              {it.notes && <div className="text-[11px] text-[#A1A1AA] mt-0.5">{it.notes}</div>}
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <span className="font-cabinet font-bold">{fmtEur(it.amount)}</span>
              <button onClick={() => openEdit(it)} title="Modifica" aria-label="Modifica compenso"
                className="p-1.5 text-[#A1A1AA] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded"><Pencil className="w-4 h-4" /></button>
              <button onClick={() => remove(it)} title="Elimina" aria-label="Elimina compenso"
                className="p-1.5 text-[#A1A1AA] hover:text-red-500 hover:bg-red-50 rounded"><Trash2 className="w-4 h-4" /></button>
            </div>
          </div>
        ))}
        {items && items.length === 0 && !formOpen && (
          <div className="bg-white border border-[#E4E4E1] rounded-md p-6 text-center text-[#A1A1AA] text-[13px]">Nessun compenso registrato.</div>
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
        await api.put(`/employees/${employeeId}/compensation/${initial.id}`, payload);
        toast.success("Compenso aggiornato");
      } else {
        await api.post(`/employees/${employeeId}/compensation`, payload);
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
      <p className="text-[11px] text-[#A1A1AA]">Genera automaticamente una spesa collegata, visibile in Spese.</p>
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

function formatDuration(clockIn, clockOut) {
  if (!clockOut) return "In corso";
  const totalMinutes = Math.round((new Date(clockOut) - new Date(clockIn)) / 60000);
  return `${Math.floor(totalMinutes / 60)}h ${totalMinutes % 60}m`;
}

function fmtTime(iso) {
  return new Date(iso).toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" });
}

function PresenzeTab({ employeeId }) {
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
      <p className="text-[11px] text-[#A1A1AA] mb-3">
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
                <Timer className="w-4 h-4 text-[#A1A1AA] shrink-0" />
                <span className="font-medium">{new Date(it.clock_in).toLocaleDateString("it-IT")}</span>
                <span className="text-[#52525B]">{fmtTime(it.clock_in)} → {it.clock_out ? fmtTime(it.clock_out) : "in corso"}</span>
                {!it.clock_out && (
                  <span className="font-mono text-[10px] uppercase tracking-widest px-1.5 py-0.5 rounded-full bg-[#05966920] text-[#059669]">In servizio</span>
                )}
                {it.corrected_by_admin && (
                  <span className="font-mono text-[10px] uppercase tracking-widest px-1.5 py-0.5 rounded-full bg-[#F3F3F1] text-[#A1A1AA]">Corretta</span>
                )}
              </div>
              {it.note && <div className="text-[11px] text-[#A1A1AA] mt-0.5">{it.note}</div>}
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <span className="font-cabinet font-bold">{formatDuration(it.clock_in, it.clock_out)}</span>
              <button onClick={() => openEdit(it)} title="Modifica" aria-label="Modifica sessione"
                className="p-1.5 text-[#A1A1AA] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded"><Pencil className="w-4 h-4" /></button>
              <button onClick={() => remove(it)} title="Elimina" aria-label="Elimina sessione"
                className="p-1.5 text-[#A1A1AA] hover:text-red-500 hover:bg-red-50 rounded"><Trash2 className="w-4 h-4" /></button>
            </div>
          </div>
        ))}
        {items && items.length === 0 && !formOpen && (
          <div className="bg-white border border-[#E4E4E1] rounded-md p-6 text-center text-[#A1A1AA] text-[13px]">Nessuna sessione registrata.</div>
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

function formatActivityDate(at) {
  // "at" può essere un ISO datetime completo (created_at/decided_at) o una
  // semplice data "AAAA-MM-DD" (returned_date della dotazione): entrambi
  // sono accettati da new Date(), qui si sceglie solo se mostrare anche
  // l'orario in base a quanti caratteri ha la stringa originale.
  const d = new Date(at);
  if (Number.isNaN(d.getTime())) return at;
  return at.length > 10 ? d.toLocaleString("it-IT") : d.toLocaleDateString("it-IT");
}

function AttivitaTab({ employeeId }) {
  const [events, setEvents] = useState(null);

  useEffect(() => {
    api.get(`/employees/${employeeId}/activity`).then(({ data }) => setEvents(data));
  }, [employeeId]);

  return (
    <div>
      <p className="text-[11px] text-[#A1A1AA] mb-3">
        Cronologia sola lettura: assenze, documenti, dotazione e compensi. Non include modifiche all'anagrafica o rigenerazioni del link.
      </p>
      <div className="space-y-2">
        {(events || []).map((ev, i) => {
          const meta = ACTIVITY_META[ev.type] || { label: ev.type, icon: History, color: "#52525B" };
          const Icon = meta.icon;
          return (
            <div key={i} className="bg-white border border-[#E4E4E1] rounded-md p-3 flex items-start gap-3 text-[13px]">
              <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0" style={{ background: `${meta.color}1A` }}>
                <Icon className="w-3.5 h-3.5" style={{ color: meta.color }} />
              </div>
              <div className="min-w-0">
                <div className="font-medium">{meta.label}</div>
                <div className="text-[#52525B] truncate">{ev.detail}</div>
                <div className="text-[11px] text-[#A1A1AA] mt-0.5">{formatActivityDate(ev.at)}</div>
              </div>
            </div>
          );
        })}
        {events && events.length === 0 && (
          <div className="bg-white border border-[#E4E4E1] rounded-md p-6 text-center text-[#A1A1AA] text-[13px]">Nessuna attività registrata.</div>
        )}
      </div>
    </div>
  );
}

// Riepilogo testuale deterministico, calcolato qui dal solo `summary` già
// caricato per la scheda (nessuna chiamata di rete, nessun coinvolgimento
// dell'AI): mostrato sempre, così chi vuole solo i numeri non deve inviare
// nulla a un servizio esterno. Il riepilogo AI resta un'azione separata ed
// esplicita più sotto (vedi generate/handleGenerate) — coerente col fatto
// che i giorni di malattia, per quanto solo un numero, restano un dato
// collegato alla salute della persona.
function localSummaryText(summary) {
  if (!summary) return "";
  const { ferie, permessi, malattie } = summary;
  const parts = [`Ferie residue: ${ferie.residue} giorni`];
  if (permessi.ore_approvate) parts.push(`Permessi approvati: ${permessi.ore_approvate} ore`);
  if (malattie.giorni) parts.push(`Malattie registrate: ${malattie.giorni} giorni`);
  return parts.join(". ") + ".";
}

function AiTab({ employeeId, summary }) {
  const [aiSummary, setAiSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const generate = async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get(`/employees/${employeeId}/ai-summary`);
      if (data.summary) {
        setAiSummary(data.summary);
      } else {
        setError("Assistente AI non configurato per questo account.");
      }
    } catch (err) {
      setError(err?.response?.status === 429
        ? "Troppe richieste, riprova tra qualche minuto."
        : "Impossibile generare il riepilogo al momento.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="bg-white border border-[#E4E4E1] rounded-md p-4">
        <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] mb-2">Riepilogo</div>
        <p className="text-[13px] text-[#0A192F] leading-relaxed">{localSummaryText(summary)}</p>
      </div>

      {!aiSummary && !loading && !error && (
        <div className="bg-white border border-[#E4E4E1] rounded-md p-6 text-center">
          <Sparkles className="w-6 h-6 text-[#A1A1AA] mx-auto mb-2" />
          <p className="text-[13px] text-[#52525B] mb-1">Genera un riepilogo in linguaggio naturale della situazione di questo dipendente.</p>
          <p className="text-[11px] text-[#A1A1AA] mb-4">Invia questi valori a un servizio AI esterno (Anthropic) per generare il testo.</p>
          <button onClick={generate} className="px-4 py-2.5 bg-[#0A192F] text-white rounded-md text-[13px] font-medium">
            Genera riepilogo AI
          </button>
        </div>
      )}
      {loading && (
        <div className="bg-white border border-[#E4E4E1] rounded-md p-6 text-center text-[#A1A1AA] text-[13px]">Generazione in corso…</div>
      )}
      {error && !loading && (
        <div className="bg-white border border-[#E4E4E1] rounded-md p-6 text-center">
          <p className="text-[13px] text-[#DC2626] mb-3">{error}</p>
          <button onClick={generate} className="px-3 py-2 border border-[#E4E4E1] rounded-md text-[12px] font-medium hover:border-[#0A192F]">Riprova</button>
        </div>
      )}
      {aiSummary && !loading && (
        <div className="bg-[#F9F9F8] border border-[#E4E4E1] rounded-md p-4">
          <div className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] mb-2">
            <Sparkles className="w-3 h-3" /> Riepilogo AI
          </div>
          <p className="text-[13px] text-[#0A192F] leading-relaxed">{aiSummary}</p>
          <button onClick={generate} className="mt-3 text-[12px] font-medium text-[#52525B] hover:text-[#0A192F]">Rigenera</button>
        </div>
      )}
    </div>
  );
}

function DocumentiTab({ employeeId }) {
  const [docs, setDocs] = useState(null);
  const [showUpload, setShowUpload] = useState(false);

  const load = async () => {
    const { data } = await api.get(`/employees/${employeeId}/documents`);
    setDocs(data);
  };
  useEffect(() => { load(); }, [employeeId]); // eslint-disable-line react-hooks/exhaustive-deps

  const download = async (doc) => {
    try {
      const res = await fetch(`${FILE_BASE}/api/employees/${employeeId}/documents/${doc.id}/download`, {
        credentials: "include",
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = doc.original_filename || doc.name;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch {
      toast.error("Errore download");
    }
  };

  const remove = async (doc) => {
    if (!window.confirm(`Eliminare "${doc.name}"?`)) return;
    try {
      await api.delete(`/employees/${employeeId}/documents/${doc.id}`);
      toast.success("Documento eliminato");
      load();
    } catch {
      toast.error("Errore eliminazione");
    }
  };

  return (
    <div>
      <div className="flex justify-end mb-3">
        <button onClick={() => setShowUpload((v) => !v)}
          className="flex items-center gap-1.5 px-3 py-2 bg-[#0A192F] text-white rounded-md text-[12px] font-medium">
          <Upload className="w-3.5 h-3.5" /> Carica documento
        </button>
      </div>
      {showUpload && (
        <EmployeeDocumentUploadForm employeeId={employeeId} onDone={() => { setShowUpload(false); load(); }} />
      )}
      <div className="space-y-2 mt-3">
        {(docs || []).map((d) => (
          <div key={d.id} className="bg-white border border-[#E4E4E1] rounded-md p-3 flex items-center justify-between gap-2 flex-wrap text-[13px]">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-[#A1A1AA] shrink-0" />
                <span className="font-medium truncate">{d.name}</span>
                <span className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] shrink-0">{DOCUMENT_CATEGORY_LABELS[d.category] || d.category}</span>
              </div>
              <div className="text-[11px] text-[#A1A1AA] mt-0.5">{new Date(d.created_at).toLocaleDateString("it-IT")}{d.notes ? ` · ${d.notes}` : ""}</div>
            </div>
            <div className="flex gap-1 shrink-0">
              <button onClick={() => download(d)} title="Scarica" aria-label="Scarica documento"
                className="p-1.5 text-[#A1A1AA] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded"><Download className="w-4 h-4" /></button>
              <button onClick={() => remove(d)} title="Elimina" aria-label="Elimina documento"
                className="p-1.5 text-[#A1A1AA] hover:text-red-500 hover:bg-red-50 rounded"><Trash2 className="w-4 h-4" /></button>
            </div>
          </div>
        ))}
        {docs && docs.length === 0 && !showUpload && (
          <div className="bg-white border border-[#E4E4E1] rounded-md p-6 text-center text-[#A1A1AA] text-[13px]">Nessun documento caricato.</div>
        )}
      </div>
    </div>
  );
}

function EmployeeDocumentUploadForm({ employeeId, onDone }) {
  const fileRef = useRef(null);
  const [file, setFile] = useState(null);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("altro");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);

  const onPick = (f) => {
    if (!f) return;
    if (f.size > DOCUMENT_MAX_MB * 1024 * 1024) {
      toast.error(`File troppo grande (max ${DOCUMENT_MAX_MB} MB)`);
      return;
    }
    setFile(f);
    if (!name) setName(f.name.replace(/\.[^.]+$/, ""));
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!file) { toast.error("Seleziona un file"); return; }
    setBusy(true);
    const fd = new FormData();
    fd.append("file", file);
    fd.append("name", name.trim());
    fd.append("category", category);
    fd.append("notes", notes);
    try {
      await api.post(`/employees/${employeeId}/documents/upload`, fd);
      toast.success("Documento caricato");
      onDone();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Errore caricamento");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="bg-[#F9F9F8] border border-[#E4E4E1] rounded-md p-3 space-y-2.5 mb-3">
      <input ref={fileRef} type="file" className="hidden" onChange={(e) => onPick(e.target.files?.[0])} />
      <button type="button" onClick={() => fileRef.current?.click()}
        className="w-full flex items-center justify-center gap-2 px-3 py-2.5 border border-dashed border-[#E4E4E1] rounded-md text-[12px] font-medium hover:border-[#FF5A00]">
        <Upload className="w-4 h-4" /> {file ? file.name : "Scegli file (PDF, immagine, Word, Excel)"}
      </button>
      <div className="grid grid-cols-2 gap-2">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Nome documento"
          className="bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
        <select value={category} onChange={(e) => setCategory(e.target.value)}
          className="bg-white border border-[#E4E4E1] rounded-md px-2 py-2 text-[13px]">
          {Object.entries(DOCUMENT_CATEGORY_LABELS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
        </select>
      </div>
      <input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Note (opzionale)"
        className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      <button type="submit" disabled={busy} className="w-full bg-[#0A192F] text-white py-2 rounded-md text-[12px] font-medium disabled:opacity-60">
        {busy ? "Caricamento…" : "Carica"}
      </button>
    </form>
  );
}

function LinkTab({ employee, newLink, onRegenerate, onToggleActive, onCopy, newPin, onRegeneratePin }) {
  const url = newLink ? `${window.location.origin}/richiedi-assenza/${newLink.token}` : null;
  return (
    <div className="space-y-4">
      <div className="bg-white border border-[#E4E4E1] rounded-md p-4 space-y-2 text-[13px]">
        <div className="flex justify-between"><span className="text-[#A1A1AA]">Stato</span><span className="font-medium">{employee.active ? "Attivo" : "Disattivato"}</span></div>
        <div className="flex justify-between"><span className="text-[#A1A1AA]">Ultimo utilizzo</span><span className="font-medium">{employee.last_used_at ? new Date(employee.last_used_at).toLocaleString("it-IT") : "Mai"}</span></div>
      </div>
      <div className="flex gap-2">
        <button onClick={onRegenerate} className="flex-1 flex items-center justify-center gap-2 px-3 py-2.5 border border-[#E4E4E1] rounded-md text-[13px] font-medium hover:border-[#FF5A00]">
          <RefreshCw className="w-4 h-4" /> Rigenera
        </button>
        <button onClick={onToggleActive} className="flex-1 flex items-center justify-center gap-2 px-3 py-2.5 border border-[#E4E4E1] rounded-md text-[13px] font-medium hover:border-[#0A192F]">
          {employee.active ? <PowerOff className="w-4 h-4" /> : <Power className="w-4 h-4" />} {employee.active ? "Disattiva" : "Riattiva"}
        </button>
      </div>
      {newLink && (
        <div className="bg-[#F9F9F8] border border-[#E4E4E1] rounded-md p-4 space-y-3">
          <p className="text-[12px] text-[#52525B]">Nuovo link generato: copialo ora, non verrà più mostrato.</p>
          <div className="flex justify-center bg-white p-3 rounded-md border border-[#E4E4E1]">
            <QRCodeSVG value={url} size={140} />
          </div>
          <code className="block text-[11px] break-all text-[#52525B]">{url}</code>
          <button onClick={() => onCopy(newLink.token)} className="w-full flex items-center justify-center gap-2 bg-[#0A192F] text-white py-2 rounded-md text-[12px] font-medium">
            <Copy className="w-3.5 h-3.5" /> Copia link
          </button>
        </div>
      )}

      <div className="bg-white border border-[#E4E4E1] rounded-md p-4 space-y-3">
        <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA]">PIN chiosco presenze</div>
        <p className="text-[12px] text-[#52525B]">
          Usato per identificarsi al QR di timbratura affisso in azienda (Personale → QR Timbratura).{" "}
          {employee.has_pin ? "PIN già impostato." : "Nessun PIN impostato: il dipendente non può ancora timbrare al chiosco."}
        </p>
        <button onClick={onRegeneratePin} className="w-full flex items-center justify-center gap-2 px-3 py-2 border border-[#E4E4E1] rounded-md text-[13px] font-medium hover:border-[#FF5A00]">
          <RefreshCw className="w-4 h-4" /> {employee.has_pin ? "Rigenera PIN" : "Genera PIN"}
        </button>
        {newPin && (
          <div className="bg-[#F9F9F8] border border-[#E4E4E1] rounded-md p-4 text-center">
            <p className="text-[12px] text-[#52525B] mb-2">Nuovo PIN generato: comunicalo ora al dipendente, non verrà più mostrato.</p>
            <div className="font-cabinet font-black text-3xl tracking-[0.3em]">{newPin.pin}</div>
          </div>
        )}
      </div>
    </div>
  );
}

function KpiTab({ summary }) {
  if (!summary) return null;
  const { kpi } = summary;
  return (
    <div className="grid grid-cols-2 gap-2">
      <MiniStat label="Presenze stimate" value={kpi.presenze_stimate} />
      <MiniStat label="Assenze (gg)" value={kpi.assenze_giorni} />
      <MiniStat label="Ferie (gg)" value={kpi.ferie_giorni} />
      <MiniStat label="Permessi (h)" value={kpi.permessi_ore} />
      <MiniStat label="Malattie (gg)" value={kpi.malattie_giorni} />
    </div>
  );
}

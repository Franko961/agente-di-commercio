import { useEffect, useRef, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { toast } from "sonner";
import {
  User, CalendarDays, Palmtree, Clock, Thermometer, Truck, Link2, BarChart3,
  RefreshCw, Power, PowerOff, Camera, Copy,
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

const TABS = [
  ["info", "Informazioni", User],
  ["assenze", "Assenze", CalendarDays],
  ["ferie", "Ferie", Palmtree],
  ["permessi", "Permessi", Clock],
  ["malattie", "Malattie", Thermometer],
  ["mezzo", "Mezzo", Truck],
  ["link", "Link", Link2],
  ["kpi", "KPI", BarChart3],
];

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
              <div className="flex items-center gap-1 mb-4 border-b border-[#E4E4E1] overflow-x-auto">
                {TABS.map(([key, label, Icon]) => (
                  <button key={key} onClick={() => setTab(key)}
                    className={`flex items-center gap-1.5 px-2.5 py-2 text-[12px] font-medium whitespace-nowrap border-b-2 -mb-px transition-colors ${
                      tab === key ? "border-[#FF5A00] text-[#0A192F]" : "border-transparent text-[#A1A1AA] hover:text-[#52525B]"
                    }`}>
                    <Icon className="w-3.5 h-3.5" /> {label}
                  </button>
                ))}
              </div>

              {tab === "info" && <InfoTab employee={emp} onSaved={refreshAll} />}
              {tab === "assenze" && <AssenzeTab requests={myRequests} summary={summary} />}
              {tab === "ferie" && <FerieTab summary={summary} />}
              {tab === "permessi" && <PermessiTab summary={summary} />}
              {tab === "malattie" && <MalattieTab summary={summary} onSetCertificate={setCertificate} />}
              {tab === "mezzo" && <MezzoTab vehicle={detail?.vehicle} nextRevisione={detail?.next_revisione} />}
              {tab === "link" && (
                <LinkTab employee={emp} newLink={newLink} onRegenerate={regenerateToken}
                  onToggleActive={toggleActive} onCopy={copyLink} />
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
  });
  const [saving, setSaving] = useState(false);
  const fileRef = useRef(null);

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
      });
      toast.success("Informazioni aggiornate");
      onSaved();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Salvataggio non riuscito");
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

function AssenzeTab({ requests, summary }) {
  const [filterType, setFilterType] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const filtered = requests.filter((r) => (!filterType || r.type === filterType) && (!filterStatus || r.status === filterStatus));

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
              <span className="font-mono text-[10px] uppercase tracking-widest" style={{ color: REQUEST_STATUS_COLORS[r.status] }}>
                {REQUEST_STATUS_LABELS[r.status]}
              </span>
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

function LinkTab({ employee, newLink, onRegenerate, onToggleActive, onCopy }) {
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

import { useEffect, useState, Fragment } from "react";
import {
  QrCode, RefreshCw, Download, ChevronLeft, ChevronRight, ChevronDown,
  Palmtree, Clock, Thermometer, Home, Car, Timer, Phone,
} from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { toast } from "sonner";
import api from "../api";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";
import { Switch } from "../components/ui/switch";
import { exportAttendance } from "../utils/export";
import { useAuth } from "../contexts/AuthContext";
import DayDetailSheet from "../components/DayDetailSheet";

const TYPE_LABELS = { ferie: "Ferie", permesso: "Permesso", malattia: "Malattia" };
const TYPE_COLORS = { ferie: "#FF5A00", permesso: "#0A192F", malattia: "#DC2626" };
// Tipi registrabili solo dal responsabile direttamente dal pannello giorno
// (vedi DayDetailSheet.jsx e backend/models/leave_request.py ADMIN_LEAVE_TYPES):
// a differenza di ferie/permesso/malattia non passano da richiesta+approvazione.
const ADMIN_TYPE_LABELS = { smartworking: "Smartworking", trasferta: "Trasferta", straordinari: "Straordinari", reperibilita: "Reperibilità" };
const ADMIN_TYPE_COLORS = { smartworking: "#D97706", trasferta: "#78350F", straordinari: "#DB2777", reperibilita: "#6366F1" };
const ALL_TYPE_LABELS = { ...TYPE_LABELS, ...ADMIN_TYPE_LABELS };
const ALL_TYPE_COLORS = { ...TYPE_COLORS, ...ADMIN_TYPE_COLORS };
const ALL_TYPE_ICONS = { ferie: Palmtree, permesso: Clock, malattia: Thermometer, smartworking: Home, trasferta: Car, straordinari: Timer, reperibilita: Phone };
const PRESENTE_COLOR = "#16A34A";

function monthKeyToday() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export default function Presenze() {
  const { user } = useAuth();
  const automazioniEnabled = !(user?.disabled_modules || []).includes("automazioni");
  const [employees, setEmployees] = useState([]);
  const [month, setMonth] = useState(monthKeyToday());
  const [calendarRows, setCalendarRows] = useState([]);
  const [hoursRows, setHoursRows] = useState([]); // [{ employee_id, date, hours }] — ore lavorate dal chiosco
  const [expectedRows, setExpectedRows] = useState([]); // [{ employee_id, date, hours }] — ore attese da orario contrattuale
  const [kioskDialogOpen, setKioskDialogOpen] = useState(false);
  const [kioskHasToken, setKioskHasToken] = useState(null); // null = non ancora caricato
  const [kioskToken, setKioskToken] = useState(null); // token in chiaro, mostrato una sola volta dopo generazione
  const [attendanceReminder, setAttendanceReminder] = useState(null); // automazione "attendance_missing", null finché non caricata/creata

  const loadEmployees = async () => {
    const { data } = await api.get("/employees");
    setEmployees(data);
  };
  const loadCalendar = async (m) => {
    const { data } = await api.get("/leave-requests/calendar", { params: { month: m } });
    setCalendarRows(data);
  };
  const loadHours = async (m) => {
    const { data } = await api.get("/attendance/calendar", { params: { month: m } });
    setHoursRows(data);
  };
  const loadExpectedHours = async (m) => {
    const { data } = await api.get("/attendance/expected", { params: { month: m } });
    setExpectedRows(data);
  };
  const loadAttendanceReminder = async () => {
    if (!automazioniEnabled) return;
    const { data } = await api.get("/automations");
    const existing = data.find((a) => a.trigger === "attendance_missing");
    if (existing) setAttendanceReminder(existing);
  };

  useEffect(() => { loadEmployees(); loadAttendanceReminder(); }, []);
  useEffect(() => { loadCalendar(month); loadHours(month); loadExpectedHours(month); }, [month]);

  // Richiamato dal pannello di dettaglio giorno (DayDetailSheet) dopo
  // un'aggiunta/modifica/eliminazione: ricarica gli stessi dati già usati
  // per popolare la griglia, così il pannello e la griglia restano coerenti
  // senza un reload di pagina.
  const refreshMonthData = () => { loadCalendar(month); loadHours(month); loadExpectedHours(month); };

  // Nessun campo di config oltre enabled: l'orario del controllo (1h dopo
  // l'inizio turno di ciascun dipendente) viene già dall'orario
  // contrattuale impostato sulla scheda dipendente (vedi
  // automation_engine._eval_attendance_missing), non serve altro qui —
  // stesso schema di toggleReminderDay in Flotta.jsx, ma senza soglie da
  // configurare.
  const toggleAttendanceReminder = async (enabled) => {
    const payload = {
      name: "Timbratura mancante", trigger: "attendance_missing", action: "send_reminder",
      enabled, config: {},
    };
    try {
      if (attendanceReminder) {
        // PUT /automations/{id} ritorna solo {ok:true} (vedi
        // automation_service.update_automation), non il documento
        // aggiornato: a differenza della creazione, qui l'id non cambia,
        // quindi si aggiorna lo stato locale con lo stesso payload inviato.
        await api.put(`/automations/${attendanceReminder.id}`, payload);
        setAttendanceReminder({ ...attendanceReminder, ...payload });
      } else {
        const { data } = await api.post("/automations", payload);
        setAttendanceReminder(data);
      }
      toast.success(enabled ? "Segnalazione attivata" : "Segnalazione disattivata");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Operazione non riuscita");
    }
  };

  const openKioskDialog = async () => {
    setKioskDialogOpen(true);
    if (kioskHasToken === null) {
      const { data } = await api.get("/settings/attendance-kiosk");
      setKioskHasToken(data.has_token);
    }
  };

  const regenerateKiosk = async () => {
    if (kioskHasToken && !window.confirm("Il QR attuale smetterà subito di funzionare. Rigenerare?")) return;
    const { data } = await api.post("/settings/attendance-kiosk/regenerate");
    setKioskToken(data.token);
    setKioskHasToken(true);
    toast.success("QR generato");
  };

  const kioskUrl = kioskToken ? `${window.location.origin}/timbra/${kioskToken}` : null;

  // Cartellino del mese selezionato (timbrature + assenze approvate) per il
  // consulente del lavoro.
  const exportAttendanceCsv = async () => {
    try {
      await exportAttendance(month);
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
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00] mb-2">Gestione Presenze</div>
          <h1 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight">Presenze</h1>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={openKioskDialog} className="flex items-center gap-2 px-3 py-2.5 border border-[#E4E4E1] rounded-md text-[13px] font-medium hover:border-[#0A192F]">
            <QrCode className="w-4 h-4" /> QR Timbratura
          </button>
        </div>
      </div>

      <Dialog open={kioskDialogOpen} onOpenChange={(v) => { setKioskDialogOpen(v); if (!v) setKioskToken(null); }}>
        <DialogContent>
          <DialogHeader><DialogTitle>QR per la timbratura</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <p className="text-[13px] text-[#52525B]">
              Un unico QR per tutti i dipendenti, da stampare e affiggere all'ingresso: chi lo scansiona sceglie il proprio
              nome e inserisce il proprio PIN (impostabile dalla scheda di ciascun dipendente, tab Link) per timbrare
              ingresso/uscita. Nessuna posizione GPS: solo l'orario, registrato quando si scansiona il QR fisico.
            </p>
            {kioskToken ? (
              <div className="bg-[#F9F9F8] border border-[#E4E4E1] rounded-md p-4 space-y-3">
                <p className="text-[12px] text-[#52525B]">Nuovo QR generato: stampalo ora, non verrà più mostrato.</p>
                <div className="flex justify-center bg-white p-3 rounded-md border border-[#E4E4E1]">
                  <QRCodeSVG value={kioskUrl} size={180} />
                </div>
                <code className="block text-[11px] break-all text-[#52525B]">{kioskUrl}</code>
              </div>
            ) : kioskHasToken ? (
              <p className="text-[13px] text-[#52525B]">Un QR è già configurato. Rigeneralo solo se quello affisso è stato smarrito o va sostituito: quello attuale smetterà subito di funzionare.</p>
            ) : kioskHasToken === false ? (
              <p className="text-[13px] text-[#52525B]">Nessun QR generato finora.</p>
            ) : (
              <p className="text-[13px] text-[#A1A1AA]">Caricamento…</p>
            )}
            {kioskHasToken !== null && (
              <button onClick={regenerateKiosk} className="w-full flex items-center justify-center gap-2 bg-[#0A192F] text-white py-2.5 rounded-md text-[13px] font-medium">
                <RefreshCw className="w-4 h-4" /> {kioskHasToken ? "Rigenera QR" : "Genera QR"}
              </button>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {automazioniEnabled ? (
        <div className="bg-white border border-[#E4E4E1] rounded-md p-4 mb-4 flex items-center justify-between gap-4">
          <div>
            <div className="text-[13px] font-medium">Avvisami se un dipendente non timbra</div>
            <div className="text-[12px] text-[#A1A1AA]">
              Un'ora dopo l'inizio del turno contrattuale (impostato sulla scheda dipendente), se non ha timbrato e non ha un'assenza approvata.
            </div>
          </div>
          <Switch checked={attendanceReminder?.enabled || false} onCheckedChange={toggleAttendanceReminder} />
        </div>
      ) : (
        <div className="bg-[#F9F9F8] border border-[#E4E4E1] rounded-md p-4 mb-4 text-[13px] text-[#A1A1AA]">
          Attiva il modulo Automazioni per la segnalazione delle timbrature mancanti.
        </div>
      )}
      <div className="flex items-center justify-between mb-4 gap-3 flex-wrap">
        <div className="flex items-center gap-3">
          <button onClick={() => shiftMonth(-1)} className="p-2 border border-[#E4E4E1] rounded-md hover:border-[#0A192F]"><ChevronLeft className="w-4 h-4" /></button>
          <span className="font-cabinet font-bold text-[15px]">{monthLabel}</span>
          <button onClick={() => shiftMonth(1)} className="p-2 border border-[#E4E4E1] rounded-md hover:border-[#0A192F]"><ChevronRight className="w-4 h-4" /></button>
        </div>
        <button onClick={exportAttendanceCsv} title="Cartellino del mese: timbrature e assenze approvate, per il consulente del lavoro"
          className="flex items-center gap-2 px-3 py-2 border border-[#E4E4E1] rounded-md text-[13px] font-medium hover:border-[#0A192F]">
          <Download className="w-4 h-4" /> Esporta cartellino
        </button>
      </div>
      <AbsenceCalendarGrid employees={employees} month={month} rows={calendarRows} hoursRows={hoursRows} expectedRows={expectedRows} onChanged={refreshMonthData} />
    </div>
  );
}

function daysInMonthCount(monthKey) {
  const [y, m] = monthKey.split("-").map(Number);
  return new Date(y, m, 0).getDate();
}

function dayIso(monthKey, day) {
  const [y, m] = monthKey.split("-").map(Number);
  return `${y}-${String(m).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

function isWeekend(monthKey, day) {
  const [y, m] = monthKey.split("-").map(Number);
  const dow = new Date(y, m - 1, day).getDay();
  return dow === 0 || dow === 6;
}

function shiftIso(iso, delta) {
  const d = new Date(`${iso}T00:00:00`);
  d.setDate(d.getDate() + delta);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

// Vista a griglia (dipendenti sulle righe, giorni del mese sulle colonne)
// pensata per aziende con diversi dipendenti (es. CACI SRL, ~40): la
// precedente semplice lista mensile non dava un colpo d'occhio su chi è
// assente quando, né segnalava sovrapposizioni. `rows` sono le richieste
// APPROVATE del mese già filtrate dal backend (vedi
// leave_request_service.calendar, include anche i tipi in ADMIN_TYPE_LABELS
// perché il backend le tratta in modo generico); `hoursRows` sono le ore
// lavorate dal chiosco di timbratura nello stesso mese (vedi
// attendance_service.calendar); `expectedRows` sono le ore ATTESE da orario
// contrattuale nello stesso mese (vedi attendance_service.expected_hours,
// presenti solo per i dipendenti che hanno compilato anche la fine turno) —
// tutto il resto è calcolato qui. `onChanged` ricarica questi tre dataset
// dopo una modifica fatta dal pannello giorno (DayDetailSheet).
function AbsenceCalendarGrid({ employees, month, rows, hoursRows, expectedRows, onChanged }) {
  const [viewMode, setViewMode] = useState("mensile");
  const [weekOffset, setWeekOffset] = useState(0);
  const [collapsedGroups, setCollapsedGroups] = useState(() => new Set());
  const [selectedDay, setSelectedDay] = useState(null); // { employeeId, employeeName, date }

  useEffect(() => { setWeekOffset(0); }, [month]);

  const activeEmployees = employees.filter((e) => e.active);

  if (activeEmployees.length === 0) {
    return (
      <div className="bg-white border border-[#E4E4E1] rounded-md p-8 text-center text-[#A1A1AA] text-[13px]">
        Nessun dipendente attivo registrato.
      </div>
    );
  }

  const dayCount = daysInMonthCount(month);
  const days = Array.from({ length: dayCount }, (_, i) => i + 1);
  const maxWeekOffset = Math.max(0, Math.ceil(dayCount / 7) - 1);
  const visibleDays = viewMode === "settimanale" ? days.slice(weekOffset * 7, weekOffset * 7 + 7) : days;

  const byEmployee = {};
  rows.forEach((r) => {
    (byEmployee[r.employee_id] ||= []).push(r);
  });
  const covering = (employeeId, iso) =>
    (byEmployee[employeeId] || []).filter((r) => r.date_from <= iso && r.date_to >= iso);

  // Ore lavorate dal chiosco di timbratura (vedi attendance_service.calendar):
  // una mappa "employeeId|data" -> ore, per un accesso O(1) per cella.
  const hoursByKey = {};
  (hoursRows || []).forEach((r) => { hoursByKey[`${r.employee_id}|${r.date}`] = r.hours; });

  // Ore ATTESE da orario contrattuale (vedi attendance_service.expected_hours):
  // stessa mappa, usata per confrontare reale vs atteso sui giorni senza
  // assenza. Solo i giorni odierni/passati vengono evidenziati come
  // scostamento: un giorno futuro ha legittimamente 0 ore reali finché non
  // arriva, non è un allarme.
  const expectedByKey = {};
  (expectedRows || []).forEach((r) => { expectedByKey[`${r.employee_id}|${r.date}`] = r.hours; });
  const now = new Date();
  const todayIso = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;

  const absentCountByDay = days.map((day) => {
    const iso = dayIso(month, day);
    return activeEmployees.filter((e) => covering(e.id, iso).length > 0).length;
  });

  // Raggruppamento per reparto (models.employee.department, testo libero):
  // se nessun dipendente ne ha impostato uno, resta la lista piatta di
  // sempre — niente intestazioni di gruppo per chi non usa questo campo.
  const groupMap = {};
  activeEmployees.forEach((e) => { (groupMap[e.department || ""] ||= []).push(e); });
  const groupKeys = Object.keys(groupMap);
  const hasGroups = groupKeys.length > 1 || (groupKeys.length === 1 && groupKeys[0] !== "");
  const orderedGroupKeys = hasGroups
    ? [...groupKeys].sort((a, b) => (a === "" ? 1 : b === "" ? -1 : a.localeCompare(b)))
    : [""];

  const toggleGroup = (key) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  };

  const monthStartIso = dayIso(month, 1);
  const monthEndIso = dayIso(month, dayCount);

  return (
    <div>
      <div className="flex items-center justify-between mb-3 gap-3 flex-wrap">
        <div className="flex flex-wrap items-center gap-4 text-[11px] text-[#52525B]">
          {Object.entries(ALL_TYPE_LABELS).map(([key, label]) => {
            const Icon = ALL_TYPE_ICONS[key];
            return (
              <div key={key} className="flex items-center gap-1.5">
                <span className="w-3.5 h-3.5 rounded-full inline-flex items-center justify-center" style={{ background: ALL_TYPE_COLORS[key] }}>
                  {Icon ? <Icon className="w-2 h-2 text-white" strokeWidth={3} /> : null}
                </span>
                {label}
              </div>
            );
          })}
          <div className="flex items-center gap-1.5">
            <span className="w-3.5 h-3.5 rounded-full inline-block" style={{ background: PRESENTE_COLOR }} />
            Presente
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3.5 h-3.5 rounded-full inline-block ring-2 ring-violet-500 ring-inset" style={{ background: TYPE_COLORS.ferie }} />
            Sovrapposizione
          </div>
          <div className="flex items-center gap-1.5">
            <span className="font-mono text-[10px] text-red-600">6/8</span>
            Ore reali/attese (se sotto l'orario contrattuale)
          </div>
        </div>
        <div className="flex items-center border border-[#E4E4E1] rounded-md overflow-hidden text-[11px] font-medium shrink-0">
          <button onClick={() => setViewMode("mensile")}
            className={`px-3 py-1.5 ${viewMode === "mensile" ? "bg-[#0A192F] text-white" : "bg-white text-[#52525B] hover:bg-[#F9F9F8]"}`}>
            Mensile
          </button>
          <button onClick={() => setViewMode("settimanale")}
            className={`px-3 py-1.5 border-l border-[#E4E4E1] ${viewMode === "settimanale" ? "bg-[#0A192F] text-white" : "bg-white text-[#52525B] hover:bg-[#F9F9F8]"}`}>
            Settimanale
          </button>
        </div>
      </div>

      {viewMode === "settimanale" && (
        <div className="flex items-center gap-3 mb-3">
          <button onClick={() => setWeekOffset((w) => Math.max(0, w - 1))} disabled={weekOffset === 0}
            className="p-1.5 border border-[#E4E4E1] rounded-md hover:border-[#0A192F] disabled:opacity-30">
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
          <span className="text-[12px] text-[#52525B]">
            {dayIso(month, visibleDays[0])} → {dayIso(month, visibleDays[visibleDays.length - 1])}
          </span>
          <button onClick={() => setWeekOffset((w) => Math.min(maxWeekOffset, w + 1))} disabled={weekOffset === maxWeekOffset}
            className="p-1.5 border border-[#E4E4E1] rounded-md hover:border-[#0A192F] disabled:opacity-30">
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      <div className="overflow-x-auto border border-[#E4E4E1] rounded-md bg-white">
        <table className="border-collapse text-[11px]">
          <thead>
            <tr>
              <th className="sticky left-0 z-10 bg-white border-b border-r border-[#E4E4E1] px-3 py-2 text-left font-mono text-[10px] uppercase tracking-widest text-[#52525B] min-w-[150px]">
                Dipendente
              </th>
              {visibleDays.map((day) => (
                <th key={day}
                  className={`border-b border-[#E4E4E1] w-7 text-center font-mono text-[10px] py-2 ${isWeekend(month, day) ? "bg-[#F9F9F8] text-[#A1A1AA]" : "text-[#52525B]"}`}>
                  {day}
                </th>
              ))}
            </tr>
            <tr>
              <th className="sticky left-0 z-10 bg-white border-b border-r border-[#E4E4E1] px-3 py-1 text-left font-mono text-[10px] text-[#A1A1AA] whitespace-nowrap">
                Assenti / {activeEmployees.length}
              </th>
              {visibleDays.map((day) => {
                const count = absentCountByDay[day - 1];
                return (
                  <th key={day}
                    className={`border-b border-[#E4E4E1] text-center font-mono text-[10px] py-1 ${count > 0 ? "text-[#FF5A00] font-bold" : "text-[#D4D4D1]"}`}>
                    {count || "–"}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {orderedGroupKeys.map((key) => {
              const groupEmployees = hasGroups ? groupMap[key] : activeEmployees;
              const collapsed = hasGroups && collapsedGroups.has(key);
              return (
                <Fragment key={key || "_nessuno"}>
                  {hasGroups && (
                    <tr>
                      <td colSpan={visibleDays.length + 1} className="bg-[#F9F9F8] border-b border-[#E4E4E1] px-3 py-1.5">
                        <button onClick={() => toggleGroup(key)} className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-widest text-[#52525B]">
                          <ChevronDown className={`w-3 h-3 transition-transform ${collapsed ? "-rotate-90" : ""}`} />
                          {key || "Non assegnato"} <span className="text-[#A1A1AA]">({groupEmployees.length})</span>
                        </button>
                      </td>
                    </tr>
                  )}
                  {!collapsed && groupEmployees.map((emp) => (
                    <tr key={emp.id}>
                      <td className="sticky left-0 z-10 bg-white border-r border-b border-[#E4E4E1] px-3 py-1 font-medium whitespace-nowrap">
                        {emp.name}
                      </td>
                      {visibleDays.map((day) => {
                        const iso = dayIso(month, day);
                        const matches = covering(emp.id, iso);
                        const weekend = isWeekend(month, day);
                        const hours = hoursByKey[`${emp.id}|${iso}`];
                        const expected = expectedByKey[`${emp.id}|${iso}`];
                        const openDay = () => setSelectedDay({ employeeId: emp.id, employeeName: emp.name, date: iso });
                        // Sotto l'orario contrattuale evidenziato in rosso SOLO
                        // per oggi/giorni passati: un giorno futuro ha
                        // legittimamente 0 ore reali finché non arriva, non è
                        // uno scostamento da segnalare.
                        const shortfall = expected != null && iso <= todayIso && (hours || 0) < expected;

                        if (matches.length === 0) {
                          const content = expected != null ? `${hours || 0}/${expected}` : (hours || null);
                          const cellTitle = expected != null ? `${hours || 0}h reali su ${expected}h attese` : undefined;
                          // Presente = almeno un'ora registrata dal chiosco di
                          // timbratura in questo giorno: riempimento verde come
                          // le celle di assenza, con anello rosso se sotto
                          // l'orario atteso (stesso linguaggio visivo della
                          // sovrapposizione).
                          if (hours) {
                            return (
                              <td key={day} title={cellTitle} onClick={openDay} className="border-b border-[#E4E4E1] w-7 h-7 p-0.5 cursor-pointer">
                                <div className={`w-full h-full rounded-sm flex items-center justify-center ${shortfall ? "ring-2 ring-red-500 ring-inset" : ""}`}
                                  style={{ background: PRESENTE_COLOR }}>
                                  <span className="font-mono text-[8px] text-white/90">{content}</span>
                                </div>
                              </td>
                            );
                          }
                          return (
                            <td key={day} title={cellTitle} onClick={openDay}
                              className={`border-b border-[#E4E4E1] w-7 h-7 text-center cursor-pointer hover:bg-[#F3F3F1] ${weekend ? "bg-[#F9F9F8]" : ""}`}>
                              {content ? (
                                <span className={`font-mono text-[9px] ${shortfall ? "text-red-600 font-bold" : "text-[#52525B]"}`}>{content}</span>
                              ) : null}
                            </td>
                          );
                        }

                        const conflict = matches.length > 1;
                        const title = matches.map((m) => ALL_TYPE_LABELS[m.type] || m.type).join(" + ") + (hours ? ` · ${hours}h lavorate` : "");

                        // Un solo tipo di assenza e nessuna presenza quel
                        // giorno: riempimento pieno come prima (caso comune,
                        // comportamento invariato).
                        if (matches.length === 1 && !hours) {
                          return (
                            <td key={day} title={title} onClick={openDay} className="border-b border-[#E4E4E1] w-7 h-7 p-0.5 cursor-pointer">
                              <div className="w-full h-full rounded-sm" style={{ background: ALL_TYPE_COLORS[matches[0].type] }} />
                            </td>
                          );
                        }

                        // Più elementi lo stesso giorno (assenze sovrapposte,
                        // o un'assenza parziale insieme a ore lavorate):
                        // badge colorati impilati invece di un unico
                        // riempimento, per non perdere l'informazione che
                        // sono più cose diverse. L'anello viola segnala
                        // specificamente la sovrapposizione tra assenze.
                        return (
                          <td key={day} title={title} onClick={openDay} className="border-b border-[#E4E4E1] w-7 h-7 p-0.5 cursor-pointer">
                            <div className={`w-full h-full rounded-sm flex flex-wrap items-center justify-center gap-0.5 ${conflict ? "ring-2 ring-violet-500 ring-inset" : ""}`}>
                              {hours ? <span className="w-2 h-2 rounded-full" style={{ background: PRESENTE_COLOR }} /> : null}
                              {matches.map((m) => {
                                const Icon = ALL_TYPE_ICONS[m.type];
                                return (
                                  <span key={m.id} className="w-2.5 h-2.5 rounded-full flex items-center justify-center" style={{ background: ALL_TYPE_COLORS[m.type] }}>
                                    {Icon ? <Icon className="w-1.5 h-1.5 text-white" strokeWidth={3} /> : null}
                                  </span>
                                );
                              })}
                            </div>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      {selectedDay && (
        <DayDetailSheet
          employeeId={selectedDay.employeeId}
          employeeName={selectedDay.employeeName}
          date={selectedDay.date}
          requests={covering(selectedDay.employeeId, selectedDay.date)}
          canGoPrev={selectedDay.date > monthStartIso}
          canGoNext={selectedDay.date < monthEndIso}
          onNavigate={(delta) => setSelectedDay((d) => ({ ...d, date: shiftIso(d.date, delta) }))}
          onClose={() => setSelectedDay(null)}
          onChanged={onChanged}
        />
      )}
    </div>
  );
}

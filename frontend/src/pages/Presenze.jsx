import { useEffect, useState } from "react";
import { Download, ChevronLeft, ChevronRight } from "lucide-react";
import { toast } from "sonner";
import { Switch } from "../components/ui/switch";
import { exportAttendance } from "../utils/export";
import { useAuth } from "../contexts/AuthContext";
import { listEmployees, getLeaveRequestsCalendar } from "../api/employees";
import { getAttendanceCalendar, getAttendanceExpected } from "../api/attendance";
import { listAutomations, createAutomation, updateAutomation } from "../api/automations";
import { getLeaveSettings } from "../api/settings";
import { monthKeyToday } from "../components/presenze/constants";
import KioskDialog from "../components/presenze/KioskDialog";
import AbsenceCalendarGrid from "../components/presenze/AbsenceCalendarGrid";

export default function Presenze() {
  const { user } = useAuth();
  const automazioniEnabled = !(user?.disabled_modules || []).includes("automazioni");
  const [employees, setEmployees] = useState([]);
  const [month, setMonth] = useState(monthKeyToday());
  const [calendarRows, setCalendarRows] = useState([]);
  const [hoursRows, setHoursRows] = useState([]); // [{ employee_id, date, hours }] — ore lavorate dal chiosco
  const [expectedRows, setExpectedRows] = useState([]); // [{ employee_id, date, hours }] — ore attese da orario contrattuale
  const [attendanceReminder, setAttendanceReminder] = useState(null); // automazione "attendance_missing", null finché non caricata/creata
  const [ferieCountMode, setFerieCountMode] = useState("calendario"); // vedi Impostazioni > Ferie

  const loadEmployees = async () => {
    setEmployees(await listEmployees());
  };
  const loadCalendar = async (m) => {
    setCalendarRows(await getLeaveRequestsCalendar({ month: m }));
  };
  const loadHours = async (m) => {
    setHoursRows(await getAttendanceCalendar({ month: m }));
  };
  const loadExpectedHours = async (m) => {
    setExpectedRows(await getAttendanceExpected({ month: m }));
  };
  const loadAttendanceReminder = async () => {
    if (!automazioniEnabled) return;
    const data = await listAutomations();
    const existing = data.find((a) => a.trigger === "attendance_missing");
    if (existing) setAttendanceReminder(existing);
  };
  const loadLeaveSettings = async () => {
    const data = await getLeaveSettings();
    setFerieCountMode(data.ferie_count_mode);
  };

  useEffect(() => { loadEmployees(); loadAttendanceReminder(); loadLeaveSettings(); }, []);
  useEffect(() => { loadCalendar(month); loadHours(month); loadExpectedHours(month); }, [month]);

  // Polling leggero: le timbrature dal chiosco avvengono lato server, non
  // c'è un evento che avvisi questa pagina se resta aperta — un intervallo
  // ogni 60s (invece di websocket/SSE, sproporzionati per poche timbrature
  // al giorno per dipendente) tiene la griglia ragionevolmente aggiornata
  // senza bisogno di ricaricare la pagina a mano. Si aggiorna solo lo
  // stesso mese già visualizzato, non la lista dipendenti/impostazioni.
  useEffect(() => {
    const id = setInterval(() => { loadCalendar(month); loadHours(month); loadExpectedHours(month); }, 60000);
    return () => clearInterval(id);
  }, [month]);

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
        await updateAutomation(attendanceReminder.id, payload);
        setAttendanceReminder({ ...attendanceReminder, ...payload });
      } else {
        const data = await createAutomation(payload);
        setAttendanceReminder(data);
      }
      toast.success(enabled ? "Segnalazione attivata" : "Segnalazione disattivata");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Operazione non riuscita");
    }
  };

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
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#B23E00] mb-2">Gestione Presenze</div>
          <h1 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight">Presenze</h1>
        </div>
        <div className="flex items-center gap-2">
          <KioskDialog />
        </div>
      </div>

      {automazioniEnabled ? (
        <div className="bg-white border border-[#E4E4E1] rounded-md p-4 mb-4 flex items-center justify-between gap-4">
          <div>
            <div className="text-[13px] font-medium">Avvisami se un dipendente non timbra</div>
            <div className="text-[12px] text-[#6B6B72]">
              Un'ora dopo l'inizio del turno contrattuale (impostato sulla scheda dipendente), se non ha timbrato e non ha un'assenza approvata.
            </div>
          </div>
          <Switch checked={attendanceReminder?.enabled || false} onCheckedChange={toggleAttendanceReminder} />
        </div>
      ) : (
        <div className="bg-[#F9F9F8] border border-[#E4E4E1] rounded-md p-4 mb-4 text-[13px] text-[#6B6B72]">
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
      <AbsenceCalendarGrid employees={employees} month={month} rows={calendarRows} hoursRows={hoursRows} expectedRows={expectedRows}
        ferieCountMode={ferieCountMode} onChanged={refreshMonthData} />
    </div>
  );
}

import { useRef, useState } from "react";
import { toast } from "sonner";
import { Camera } from "lucide-react";
import api from "../../../api";
import { resizeImageToDataUrl } from "../../../utils/image";
import { EMPLOYMENT_STATUS_LABELS, formatApiError } from "../constants";

// Indice 0=lunedì … 6=domenica, coerente con date.weekday() lato backend
// (vedi models.employee.work_days e automation_engine._eval_attendance_missing).
const WEEKDAY_LABELS = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"];

export default function InfoTab({ employee, onSaved }) {
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
          <div className="w-14 h-14 rounded-full bg-[#F3F3F1] flex items-center justify-center text-[#6B6B72]">
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

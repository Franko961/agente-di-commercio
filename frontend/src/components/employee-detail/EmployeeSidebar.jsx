import { EMPLOYMENT_STATUS_LABELS, EMPLOYMENT_STATUS_COLORS } from "./constants";

const CURRENT_STATUS_LABELS = { in_ferie: "In ferie", in_malattia: "In malattia" };
const CURRENT_STATUS_COLORS = { in_ferie: "#B23E00", in_malattia: "#DC2626" };

export default function EmployeeSidebar({ employee, summary, vehicle }) {
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
      <span className="text-[#6B6B72]">{label}</span>
      <span className="font-medium text-[#0A192F]">{value}</span>
    </div>
  );
}

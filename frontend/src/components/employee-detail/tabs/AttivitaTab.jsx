import { useEffect, useState } from "react";
import { FileText, Package, Wallet, History, Send, Check, X, AlertTriangle } from "lucide-react";
import { getEmployeeActivity } from "../../../api/employees";

const ACTIVITY_META = {
  assenza_inviata: { label: "Richiesta di assenza inviata", icon: Send, color: "#0A192F" },
  assenza_approvata: { label: "Richiesta di assenza approvata", icon: Check, color: "#059669" },
  assenza_rifiutata: { label: "Richiesta di assenza rifiutata", icon: X, color: "#DC2626" },
  documento_caricato: { label: "Documento caricato", icon: FileText, color: "#0A192F" },
  dotazione_aggiunta: { label: "Dotazione assegnata", icon: Package, color: "#0A192F" },
  dotazione_restituita: { label: "Dotazione restituita", icon: Package, color: "#6B6B72" },
  compenso_registrato: { label: "Compenso registrato", icon: Wallet, color: "#0A192F" },
  contestazione_registrata: { label: "Contestazione disciplinare registrata", icon: AlertTriangle, color: "#DC2626" },
};

function formatActivityDate(at) {
  const d = new Date(at);
  if (Number.isNaN(d.getTime())) return at;
  return at.length > 10 ? d.toLocaleString("it-IT") : d.toLocaleDateString("it-IT");
}

export default function AttivitaTab({ employeeId }) {
  const [events, setEvents] = useState(null);

  useEffect(() => {
    getEmployeeActivity(employeeId).then(setEvents);
  }, [employeeId]);

  return (
    <div>
      <p className="text-[11px] text-[#6B6B72] mb-3">
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
                <div className="text-[11px] text-[#6B6B72] mt-0.5">{formatActivityDate(ev.at)}</div>
              </div>
            </div>
          );
        })}
        {events && events.length === 0 && (
          <div className="bg-white border border-[#E4E4E1] rounded-md p-6 text-center text-[#6B6B72] text-[13px]">Nessuna attività registrata.</div>
        )}
      </div>
    </div>
  );
}

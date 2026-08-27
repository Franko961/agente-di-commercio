import { useState } from "react";
import { toast } from "sonner";
import { Trash2 } from "lucide-react";
import api from "../../../api";
import { REQUEST_STATUS_LABELS, REQUEST_STATUS_COLORS } from "../constants";

const LEAVE_TYPE_LABELS = { ferie: "Ferie", permesso: "Permesso", malattia: "Malattia" };
const LEAVE_TYPE_COLORS = { ferie: "#B23E00", permesso: "#0A192F", malattia: "#DC2626" };

export default function AssenzeTab({ requests, summary, onDeleted }) {
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
                {r.hours && <span className="text-[#6B6B72]">({r.hours} h)</span>}
              </div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-[10px] uppercase tracking-widest" style={{ color: REQUEST_STATUS_COLORS[r.status] }}>
                  {REQUEST_STATUS_LABELS[r.status]}
                </span>
                <button onClick={() => deleteRequest(r)} title="Elimina" aria-label="Elimina richiesta"
                  className="p-1 text-[#6B6B72] hover:text-red-500 hover:bg-red-50 rounded"><Trash2 className="w-3.5 h-3.5" /></button>
              </div>
            </div>
            {r.note && <div className="text-[12px] text-[#52525B] mt-1 italic">"{r.note}"</div>}
          </div>
        ))}
        {filtered.length === 0 && (
          <div className="bg-white border border-[#E4E4E1] rounded-md p-6 text-center text-[#6B6B72] text-[13px]">Nessuna richiesta.</div>
        )}
      </div>
    </div>
  );
}

export function MiniStat({ label, value }) {
  return (
    <div className="bg-white border border-[#E4E4E1] rounded-md p-3 text-center">
      <div className="font-cabinet font-black text-xl">{value}</div>
      <div className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72] mt-0.5">{label}</div>
    </div>
  );
}

import { useEffect, useState } from "react";
import { getAdminHealth } from "../../api/admin";
import { Bot, Mail, CalendarClock, Clock, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { fmtUsd } from "./constants";

// ---------------------------------------------------------------------
// Salute applicativa: endpoint lenti/con errori, AI, email, sync Calendar
// ---------------------------------------------------------------------
const WINDOW_OPTIONS = [
  { hours: 1, label: "Ultima ora" },
  { hours: 24, label: "Ultime 24 ore" },
  { hours: 168, label: "Ultimi 7 giorni" },
];

export default function HealthTab() {
  const [health, setHealth] = useState(null);
  const [hours, setHours] = useState(24);
  const [loading, setLoading] = useState(true);

  const load = async (h) => {
    setLoading(true);
    try {
      setHealth(await getAdminHealth(h));
    } catch {
      toast.error("Impossibile caricare i dati di salute applicativa");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(hours); }, [hours]);

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <div className="flex gap-1 bg-[#F3F3F1] rounded-md p-1">
          {WINDOW_OPTIONS.map((o) => (
            <button
              key={o.hours}
              onClick={() => setHours(o.hours)}
              className={`px-3 py-1.5 rounded text-[12px] font-medium transition-colors ${
                hours === o.hours ? "bg-white text-[#0A192F] shadow-sm" : "text-[#52525B] hover:text-[#0A192F]"
              }`}
            >
              {o.label}
            </button>
          ))}
        </div>
        {health && (
          <div className="text-[11px] text-[#6B6B72] font-mono">
            {health.endpoints.total_requests} richieste API nella finestra
          </div>
        )}
      </div>

      {loading || !health ? (
        <div className="p-8 text-center text-[#6B6B72]">Caricamento…</div>
      ) : (
        <div className="space-y-6">
          {/* Riepiloghi categoria */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <CategoryCard
              icon={Bot} title="Assistente AI" color="#B23E00"
              stats={health.ai}
              extra={`Costo stimato: ${fmtUsd(health.ai.cost_usd)} · ${health.ai.tokens_in ?? 0}+${health.ai.tokens_out ?? 0} token`}
            />
            <CategoryCard icon={Mail} title="Invio email" color="#0EA5E9" stats={health.email} />
            <CategoryCard icon={CalendarClock} title="Sync Google Calendar" color="#8B5CF6" stats={health.calendar_sync} />
          </div>

          {/* Endpoint più lenti */}
          <div className="bg-white border border-[#E4E4E1] rounded-md overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-[#E4E4E1]">
              <Clock className="w-4 h-4 text-[#52525B]" />
              <div className="font-mono text-[11px] uppercase tracking-widest text-[#52525B]">Endpoint più lenti</div>
            </div>
            {health.endpoints.slowest.length === 0 ? (
              <div className="p-6 text-center text-[13px] text-[#6B6B72]">Nessun dato nella finestra selezionata</div>
            ) : (
              <EndpointTable rows={health.endpoints.slowest} showDuration />
            )}
          </div>

          {/* Endpoint con più errori */}
          <div className="bg-white border border-[#E4E4E1] rounded-md overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-[#E4E4E1]">
              <AlertTriangle className="w-4 h-4 text-[#DC2626]" />
              <div className="font-mono text-[11px] uppercase tracking-widest text-[#52525B]">Endpoint con errori</div>
            </div>
            {health.endpoints.most_errors.length === 0 ? (
              <div className="p-6 text-center text-[13px] text-[#059669]">Nessun errore 4xx/5xx nella finestra selezionata ✓</div>
            ) : (
              <EndpointTable rows={health.endpoints.most_errors} showErrors />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function CategoryCard({ icon: Icon, title, color, stats, extra }) {
  const isHealthy = stats.total === 0 || stats.failure_rate_pct < 10;
  return (
    <div className="bg-white border border-[#E4E4E1] rounded-md p-5">
      <div className="flex items-center gap-2 mb-3">
        <Icon className="w-4 h-4" style={{ color }} />
        <div className="font-mono text-[10px] uppercase tracking-widest text-[#52525B]">{title}</div>
      </div>
      <div className="flex items-end justify-between mb-1">
        <div className="font-cabinet font-black text-2xl">{stats.total}</div>
        <div className={`font-mono text-[12px] font-semibold ${isHealthy ? "text-[#059669]" : "text-[#DC2626]"}`}>
          {stats.failure_rate_pct}% falliti
        </div>
      </div>
      <div className="text-[11px] text-[#6B6B72]">
        {stats.success} riuscite · {stats.failure} fallite
        {extra && <div className="mt-1">{extra}</div>}
      </div>
    </div>
  );
}

function EndpointTable({ rows, showDuration, showErrors }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead className="bg-[#F3F3F1]">
          <tr className="text-left">
            <th className="px-4 py-2 font-mono text-[10px] uppercase tracking-widest text-[#52525B]">Endpoint</th>
            <th className="px-4 py-2 font-mono text-[10px] uppercase tracking-widest text-[#52525B]">Chiamate</th>
            {showDuration && <>
              <th className="px-4 py-2 font-mono text-[10px] uppercase tracking-widest text-[#52525B]">Media</th>
              <th className="px-4 py-2 font-mono text-[10px] uppercase tracking-widest text-[#52525B]">Massimo</th>
            </>}
            {showErrors && <>
              <th className="px-4 py-2 font-mono text-[10px] uppercase tracking-widest text-[#52525B]">4xx</th>
              <th className="px-4 py-2 font-mono text-[10px] uppercase tracking-widest text-[#52525B]">5xx</th>
              <th className="px-4 py-2 font-mono text-[10px] uppercase tracking-widest text-[#52525B]">% errori</th>
            </>}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-t border-[#E4E4E1]">
              <td className="px-4 py-2.5 text-[12px]">
                <span className="font-mono text-[10px] text-[#6B6B72] mr-2">{r.method}</span>
                <span className="font-medium">{r.path}</span>
              </td>
              <td className="px-4 py-2.5 text-[12px] text-[#52525B]">{r.count}</td>
              {showDuration && <>
                <td className="px-4 py-2.5 text-[12px] font-mono">{r.avg_duration_ms} ms</td>
                <td className="px-4 py-2.5 text-[12px] font-mono text-[#6B6B72]">{r.max_duration_ms} ms</td>
              </>}
              {showErrors && <>
                <td className="px-4 py-2.5 text-[12px] text-[#B45309]">{r.status_4xx}</td>
                <td className="px-4 py-2.5 text-[12px] text-[#DC2626]">{r.status_5xx}</td>
                <td className="px-4 py-2.5 text-[12px] font-semibold text-[#DC2626]">{r.error_rate_pct}%</td>
              </>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

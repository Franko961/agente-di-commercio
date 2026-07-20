import { useEffect, useState } from "react";
import { History, RefreshCw, Loader2, Mic, MessageSquare } from "lucide-react";
import api from "../api";
import { EXPENSE_CATEGORY_LABELS } from "./AIActionConfirm";

const TOOL_LABELS = {
  add_client: "Nuovo cliente",
  add_appointment: "Nuovo appuntamento",
  add_lead: "Nuovo lead",
  add_note_to_client: "Nota a cliente",
  add_offer: "Vendita/Offerta",
  add_expense: "Spesa",
};

const STATUS_STYLE = {
  eseguita: { label: "Eseguita", bg: "#DCFCE7", fg: "#16A34A" },
  confermata: { label: "Confermata", bg: "#DCFCE7", fg: "#16A34A" },
  in_attesa: { label: "In attesa", bg: "#FFF7ED", fg: "#FF5A00" },
  in_esecuzione: { label: "In esecuzione", bg: "#FFF7ED", fg: "#FF5A00" },
  annullata: { label: "Annullata", bg: "#F3F3F1", fg: "#52525B" },
  fallita: { label: "Fallita", bg: "#FEE2E2", fg: "#DC2626" },
};

const fmtMoney = (n) => new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(n || 0);

const fmtDateTime = (iso) => {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleString("it-IT", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
};

/** Riepilogo leggibile dei parametri di un'azione, preferendo i valori finali
 * (dopo un'eventuale modifica dell'utente in fase di conferma) a quelli
 * proposti inizialmente dall'AI. */
function summarizeParams(log) {
  const p = log.final_params || log.resolved_params || log.proposed_params || {};
  switch (log.tool_name) {
    case "add_offer":
      return [p.client_name, p.mandante_name, p.amount != null ? fmtMoney(p.amount) : null]
        .filter(Boolean).join(" · ");
    case "add_expense":
      return [EXPENSE_CATEGORY_LABELS[p.category] || p.category, p.amount != null ? fmtMoney(p.amount) : null, p.description]
        .filter(Boolean).join(" · ");
    case "add_client":
      return p.company_name || "";
    case "add_appointment":
      return [p.title, p.client_name].filter(Boolean).join(" · ");
    case "add_lead":
      return p.company_name || "";
    case "add_note_to_client":
      return p.client_name || "";
    default:
      return "";
  }
}

export default function AiActionsLog() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ tool_name: "", status: "", date_from: "", date_to: "" });

  const load = async () => {
    setLoading(true);
    try {
      const params = {};
      Object.entries(filters).forEach(([k, v]) => { if (v) params[k] = v; });
      const { data } = await api.get("/ai/actions", { params });
      setLogs(data || []);
    } catch (e) {
      setLogs([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div>
      <div className="mb-6">
        <div className="font-mono text-[11px] uppercase tracking-widest text-[#FF5A00] mb-1">Impostazioni</div>
        <h1 className="font-cabinet text-3xl font-black">Registro AI</h1>
        <p className="text-[#52525B] mt-1">
          Ogni azione compiuta dall'assistente sul CRM — chi l'ha chiesta, con quale comando, con quali dati e con quale esito.
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-3 mb-4">
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1">Azione</label>
          <select value={filters.tool_name} onChange={(e) => setFilters(f => ({ ...f, tool_name: e.target.value }))}
            className="bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
            <option value="">Tutte</option>
            {Object.entries(TOOL_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1">Stato</label>
          <select value={filters.status} onChange={(e) => setFilters(f => ({ ...f, status: e.target.value }))}
            className="bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
            <option value="">Tutti</option>
            {Object.entries(STATUS_STYLE).map(([v, s]) => <option key={v} value={v}>{s.label}</option>)}
          </select>
        </div>
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1">Dal</label>
          <input type="date" value={filters.date_from} onChange={(e) => setFilters(f => ({ ...f, date_from: e.target.value }))}
            className="bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
        </div>
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1">Al</label>
          <input type="date" value={filters.date_to} onChange={(e) => setFilters(f => ({ ...f, date_to: e.target.value }))}
            className="bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
        </div>
        <button onClick={load} disabled={loading}
          className="flex items-center gap-1.5 px-3 py-2 border border-[#E4E4E1] hover:border-[#0A192F] rounded-md text-[12px] font-medium transition-colors disabled:opacity-50">
          {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />} Aggiorna
        </button>
      </div>

      <div className="border border-[#E4E4E1] rounded-lg overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-[13px] text-[#A1A1AA]">Caricamento…</div>
        ) : logs.length === 0 ? (
          <div className="p-8 text-center text-[13px] text-[#A1A1AA] flex flex-col items-center gap-2">
            <History className="w-5 h-5" /> Nessuna azione registrata con questi filtri.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-[13px]">
              <thead>
                <tr className="border-b border-[#E4E4E1] bg-[#F9F9F8] text-left">
                  <th className="px-3 py-2 font-mono text-[10px] uppercase tracking-widest text-[#52525B]">Data/ora</th>
                  <th className="px-3 py-2 font-mono text-[10px] uppercase tracking-widest text-[#52525B]">Canale</th>
                  <th className="px-3 py-2 font-mono text-[10px] uppercase tracking-widest text-[#52525B]">Comando</th>
                  <th className="px-3 py-2 font-mono text-[10px] uppercase tracking-widest text-[#52525B]">Azione</th>
                  <th className="px-3 py-2 font-mono text-[10px] uppercase tracking-widest text-[#52525B]">Dettagli</th>
                  <th className="px-3 py-2 font-mono text-[10px] uppercase tracking-widest text-[#52525B]">Stato</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => {
                  const st = STATUS_STYLE[log.status] || { label: log.status, bg: "#F3F3F1", fg: "#52525B" };
                  return (
                    <tr key={log.id} className="border-b border-[#E4E4E1] last:border-0 align-top">
                      <td className="px-3 py-2 whitespace-nowrap text-[#52525B]">{fmtDateTime(log.created_at)}</td>
                      <td className="px-3 py-2">
                        <span className="inline-flex items-center gap-1 text-[#52525B]" title={log.channel === "voice" ? "Comando vocale" : "Chat testuale"}>
                          {log.channel === "voice" ? <Mic className="w-3.5 h-3.5" /> : <MessageSquare className="w-3.5 h-3.5" />}
                        </span>
                      </td>
                      <td className="px-3 py-2 max-w-[220px] italic text-[#52525B]">"{log.raw_input}"</td>
                      <td className="px-3 py-2 font-medium">{TOOL_LABELS[log.tool_name] || log.tool_name}</td>
                      <td className="px-3 py-2 max-w-[260px] text-[#0A0A0A]">
                        {summarizeParams(log)}
                        {log.status === "fallita" && log.result && (
                          <div className="text-[11px] text-[#DC2626] mt-0.5">{log.result.replace(/^❌\s*/, "")}</div>
                        )}
                      </td>
                      <td className="px-3 py-2">
                        <span className="font-mono text-[10px] uppercase tracking-widest px-2 py-1 rounded"
                          style={{ background: st.bg, color: st.fg }}>
                          {st.label}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

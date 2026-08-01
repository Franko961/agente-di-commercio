import { useEffect, useMemo, useState } from "react";
import api from "../api";
import { Coins, Download, Trash2, Trophy, ChevronRight, ChevronDown } from "lucide-react";
import { toast } from "sonner";
import { exportCommissions } from "../utils/export";
import { useMandante } from "../contexts/MandanteContext";

const fmt = (n) => new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(n || 0);
const currentPeriod = () => new Date().toISOString().slice(0, 7); // "YYYY-MM"

function periodLabel(key) {
  const [y, m] = (key || "").split("-").map(Number);
  if (!y || !m) return key;
  const label = new Intl.DateTimeFormat("it-IT", { month: "long", year: "numeric" }).format(new Date(y, m - 1, 1));
  return label.charAt(0).toUpperCase() + label.slice(1);
}

// Raggruppa le provvigioni (già filtrate per cliente/stato) per periodo,
// stesso principio del raggruppamento mensile in Spese.jsx: il periodo
// corrente resta aperto di default, i periodi passati partono chiusi
// mostrando solo il totale. La provvigione manuale del mese (se presente)
// entra nel totale del gruppo, ma solo quando non è attivo un filtro per
// cliente specifico: un valore manuale non è collegato a nessun cliente,
// quindi non "appartiene" a un sottoinsieme filtrato per un cliente.
function groupByPeriod(list, manualByPeriod, includeManual) {
  const byKey = new Map();
  for (const c of list) {
    const key = c.period || "—";
    if (!byKey.has(key)) byKey.set(key, []);
    byKey.get(key).push(c);
  }
  if (includeManual) {
    for (const period of Object.keys(manualByPeriod)) {
      if (!byKey.has(period)) byKey.set(period, []);
    }
  }
  return [...byKey.entries()]
    .sort((a, b) => (a[0] < b[0] ? 1 : -1))
    .map(([key, items]) => {
      const manualAmount = includeManual ? manualByPeriod[key] : undefined;
      const calculatedTotal = items.reduce((s, c) => s + c.amount, 0);
      return { key, label: periodLabel(key), items, manualAmount, total: calculatedTotal + (manualAmount || 0) };
    });
}

export default function Commissions() {
  const { activeMandante } = useMandante();
  const mandanteParam = activeMandante && activeMandante !== "all" ? activeMandante : undefined;
  const [commissions, setCommissions] = useState([]);
  const [clients, setClients] = useState([]);
  const [mandanti, setMandanti] = useState([]);
  const [bonusSummary, setBonusSummary] = useState([]);
  const [filter, setFilter] = useState("all");
  const [clientFilter, setClientFilter] = useState("all");
  const [manualCommissions, setManualCommissions] = useState([]);
  const [manualPeriod, setManualPeriod] = useState(currentPeriod());
  const [manualAmount, setManualAmount] = useState("");
  const [savingManual, setSavingManual] = useState(false);
  const [expandedPeriods, setExpandedPeriods] = useState(() => new Set([currentPeriod()]));
  const togglePeriod = (key) => setExpandedPeriods((prev) => {
    const next = new Set(prev);
    if (next.has(key)) next.delete(key); else next.add(key);
    return next;
  });

  const load = async () => {
    const [c, cl, m, bs, mc] = await Promise.all([
      api.get("/commissions", { params: { mandante_id: mandanteParam } }),
      api.get("/clients"),
      api.get("/mandanti"),
      api.get("/commissions/bonus-summary").catch(() => ({ data: [] })),
      api.get("/commissions/manual").catch(() => ({ data: [] })),
    ]);
    setCommissions(c.data);
    setClients(cl.data);
    setMandanti(m.data);
    setBonusSummary(bs.data);
    setManualCommissions(mc.data);
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [mandanteParam]);

  // L'importo nel campo segue il mese selezionato: se per quel mese esiste
  // già un valore manuale salvato, lo mostra; altrimenti il campo resta
  // vuoto (non 0, per non far pensare che 0 sia già stato salvato).
  useEffect(() => {
    const existing = manualCommissions.find((m) => m.period === manualPeriod);
    setManualAmount(existing ? String(existing.amount) : "");
  }, [manualPeriod, manualCommissions]);

const byClient = clientFilter === "all" ? commissions : commissions.filter(c => c.client_id === clientFilter);
const filtered = filter === "all" ? byClient : byClient.filter(c => c.status === filter);
const accrued = byClient.filter(c => c.status === "maturato").reduce((s, c) => s + c.amount, 0);
const collected = byClient.filter(c => c.status === "incassato").reduce((s, c) => s + c.amount, 0);
const fatturatoClienteSelezionato = clientFilter === "all" ? null : byClient.reduce((s, c) => s + (c.base_amount ?? (c.rate ? c.amount / (c.rate / 100) : 0)), 0);
// Somma di TUTTI i mesi inseriti manualmente (non solo il mese selezionato
// nel box): si aggiunge al totale calcolato dagli ordini, per provvigioni
// concluse fuori dal flusso ordini del CRM.
const manualTotal = useMemo(() => manualCommissions.reduce((s, m) => s + (m.amount || 0), 0), [manualCommissions]);
const manualByPeriod = useMemo(
  () => Object.fromEntries(manualCommissions.map((m) => [m.period, m.amount])),
  [manualCommissions]
);
const periodGroups = useMemo(
  () => groupByPeriod(filtered, manualByPeriod, clientFilter === "all"),
  [filtered, manualByPeriod, clientFilter]
);

  const setStatus = async (id, status) => {
    await api.patch(`/commissions/${id}/status`, { status });
    toast.success("Stato aggiornato");
    load();
  };

  const saveManualCommission = async () => {
    const amount = parseFloat(manualAmount);
    if (Number.isNaN(amount) || amount < 0) {
      toast.error("Inserisci un importo valido");
      return;
    }
    setSavingManual(true);
    try {
      await api.put("/commissions/manual", { period: manualPeriod, amount });
      toast.success("Provvigione manuale salvata");
      setExpandedPeriods((prev) => new Set(prev).add(manualPeriod));
      setManualPeriod(currentPeriod());
      load();
    } catch {
      toast.error("Errore salvataggio provvigione manuale");
    } finally {
      setSavingManual(false);
    }
  };

  const removeManualCommission = async (period) => {
    if (!window.confirm(`Rimuovere la provvigione manuale di ${periodLabel(period)}?`)) return;
    await api.delete(`/commissions/manual/${period}`);
    toast.success("Provvigione manuale rimossa");
    load();
  };

  const deleteCommission = async (id) => {
    if (!window.confirm("Eliminare questa provvigione?")) return;
    await api.delete(`/commissions/${id}`);
    toast.success("Provvigione eliminata");
    load();
  };

  return (
    <div className="p-4 md:p-8">
      <div className="border-b border-[#E4E4E1] pb-6 mb-6 flex items-end justify-between">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00] mb-2">Guadagni</div>
          <h1 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight">Provvigioni</h1>
        </div>
        <button
          data-testid="export-commissions-button"
          onClick={() => exportCommissions().then(() => toast.success("Export scaricato")).catch(() => toast.error("Errore export"))}
          className="flex items-center gap-2 px-4 py-2.5 border border-[#E4E4E1] hover:border-[#0A192F] rounded-md text-[13px] font-medium"
        >
          <Download className="w-4 h-4" /> Esporta CSV
        </button>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        <div className="bg-white border border-[#E4E4E1] rounded-md p-5">
          <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] mb-2">Maturato</div>
          <div className="font-cabinet font-black text-3xl">{fmt(accrued)}</div>
          <div className="text-[11px] text-[#52525B] mt-2">In attesa di incasso</div>
        </div>
        <div className="bg-white border border-[#E4E4E1] rounded-md p-5">
          <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] mb-2">Incassato</div>
          <div className="font-cabinet font-black text-3xl text-[#059669]">{fmt(collected)}</div>
          <div className="text-[11px] text-[#52525B] mt-2">Già ricevuto</div>
        </div>
        <div className="bg-[#0A192F] text-white rounded-md p-5 col-span-2 lg:col-span-1">
          <div className="font-mono text-[10px] uppercase tracking-widest text-[#FF5A00] mb-2">Totale generato</div>
          <div className="font-cabinet font-black text-3xl">{fmt(accrued + collected + manualTotal)}</div>
          <div className="text-[11px] text-white/60 mt-2">
            {commissions.length} provvigioni totali
            {manualTotal > 0 && <> · di cui {fmt(manualTotal)} inserite manualmente</>}
          </div>
        </div>
      </div>

      {/* Provvigioni inserite manualmente: si sommano al totale calcolato
      dagli ordini, un valore per mese — per provvigioni concluse fuori dal
      flusso ordini del CRM. */}
      <div className="bg-white border border-[#E4E4E1] rounded-md p-5 mb-6">
        <div className="flex items-center gap-2 mb-3">
          <Coins className="w-4 h-4 text-[#FF5A00]" />
          <span className="font-mono text-[11px] uppercase tracking-widest text-[#52525B]">Provvigioni inserite manualmente</span>
        </div>
        <p className="text-[12px] text-[#52525B] mb-3">
          Per provvigioni non tracciate tramite gli ordini del CRM. Si sommano al totale generato, un importo per mese.
        </p>
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Mese</label>
            <input
              type="month"
              value={manualPeriod}
              onChange={(e) => setManualPeriod(e.target.value)}
              className="bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]"
            />
          </div>
          <div>
            <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Importo (€)</label>
            <input
              type="number" step="0.01" min="0" value={manualAmount}
              onChange={(e) => setManualAmount(e.target.value)}
              placeholder="0,00"
              className="bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px] w-32"
            />
          </div>
          <button
            onClick={saveManualCommission}
            disabled={savingManual}
            className="px-4 py-2 bg-[#0A192F] text-white rounded-md text-[13px] font-medium disabled:opacity-50"
          >
            Salva
          </button>
          {manualCommissions.some((m) => m.period === manualPeriod) && (
            <button
              onClick={() => removeManualCommission(manualPeriod)}
              className="flex items-center gap-1.5 px-3 py-2 text-[13px] text-[#A1A1AA] hover:text-red-500"
            >
              <Trash2 className="w-3.5 h-3.5" /> Rimuovi
            </button>
          )}
        </div>
      </div>

      {/* Scala premi bonus */}
      {bonusSummary.length > 0 && (
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-3">
            <Trophy className="w-4 h-4 text-[#FF5A00]" />
            <span className="font-mono text-[11px] uppercase tracking-widest text-[#52525B]">Scala premi maturati</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {bonusSummary.map(b => {
              const sorted = [...b.tiers].sort((a, b) => a.threshold - b.threshold);
              const maxThreshold = sorted[sorted.length - 1]?.threshold || 1;
              const progress = Math.min((b.fatturato / maxThreshold) * 100, 100);
              const nextThreshold = b.next_tier?.threshold;
              const toNext = nextThreshold ? nextThreshold - b.fatturato : 0;

              return (
                <div key={b.mandante_id} className="bg-white border border-[#E4E4E1] rounded-md p-5">
                  {/* Header */}
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-md flex items-center justify-center text-white text-[12px] font-black font-cabinet"
                        style={{ background: b.brand_color }}>
                        {b.mandante_name[0]}
                      </div>
                      <span className="font-cabinet font-bold text-[15px]">{b.mandante_name}</span>
                    </div>
                    <div className="text-right">
                      <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA]">Bonus totale</div>
                      <div className="font-cabinet font-black text-xl text-[#059669]">{fmt(b.total_bonus)}</div>
                    </div>
                  </div>

                  {/* Fatturato + barra progresso */}
                  <div className="mb-3">
                    <div className="flex justify-between text-[12px] mb-1.5">
                      <span className="text-[#52525B]">Fatturato attuale</span>
                      <span className="font-cabinet font-bold">{fmt(b.fatturato)}</span>
                    </div>
                    <div className="w-full bg-[#F3F3F1] rounded-full h-2">
                      <div className="h-2 rounded-full bg-[#FF5A00] transition-all"
                        style={{ width: `${progress}%` }} />
                    </div>
                    {b.next_tier && (
                      <div className="text-[11px] text-[#A1A1AA] mt-1.5 flex items-center gap-1">
                        <ChevronRight className="w-3 h-3" />
                        Mancano {fmt(toNext)} per il prossimo premio di {fmt(b.next_tier.bonus)}
                      </div>
                    )}
                    {!b.next_tier && b.tiers.length > 0 && (
                      <div className="text-[11px] text-[#059669] mt-1.5 font-medium">🏆 Tutti gli scaglioni raggiunti!</div>
                    )}
                  </div>

                  {/* Scaglioni */}
                  <div className="space-y-1 border-t border-[#E4E4E1] pt-3">
                    {sorted.map((t, i) => {
                      const reached = b.fatturato >= t.threshold;
                      return (
                        <div key={i} className={`flex justify-between items-center text-[12px] ${reached ? "opacity-100" : "opacity-40"}`}>
                          <div className="flex items-center gap-1.5">
                            <div className={`w-2 h-2 rounded-full ${reached ? "bg-[#059669]" : "bg-[#E4E4E1]"}`} />
                            <span className="text-[#52525B]">≥ {fmt(t.threshold)}</span>
                          </div>
                          <span className={`font-cabinet font-bold ${reached ? "text-[#059669]" : "text-[#A1A1AA]"}`}>
                            +{fmt(t.bonus)}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Filtri */}
      <div className="flex gap-2 mb-4">
        {["all", "maturato", "incassato"].map(s => (
          <button key={s} onClick={() => setFilter(s)} data-testid={`filter-${s}`}
            className={`px-4 py-2 rounded-md text-[12px] font-medium ${filter === s ? "bg-[#0A192F] text-white" : "bg-white border border-[#E4E4E1]"}`}>
            {s === "all" ? "Tutte" : s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>
{/* Filtro cliente */}
<div className="flex items-center gap-2 mb-4">
  <select
    value={clientFilter}
    onChange={(e) => setClientFilter(e.target.value)}
    className="px-3 py-2 rounded-md text-[12px] font-medium bg-white border border-[#E4E4E1]"
  >
    <option value="all">Tutti i clienti</option>
    {[...clients].sort((a, b) => (a.company_name || "").localeCompare(b.company_name || "")).map(cl => (
      <option key={cl.id} value={cl.id}>{cl.company_name}</option>
    ))}
  </select>
  {clientFilter !== "all" && fatturatoClienteSelezionato !== null && (
    <span className="font-mono text-[11px] text-[#52525B]">
      Fatturato generato: <span className="font-bold text-[#0A192F]">{fmt(fatturatoClienteSelezionato)}</span>
    </span>
  )}
</div>
      {/* Tabella provvigioni, raggruppata per periodo — stesso principio del
      raggruppamento mensile in Spese.jsx: il periodo corrente resta aperto,
      i periodi passati partono chiusi mostrando solo il totale. */}
      <div className="space-y-3">
        {periodGroups.map((group) => {
          const isExpanded = expandedPeriods.has(group.key);
          return (
            <div key={group.key} className="bg-white border border-[#E4E4E1] rounded-md overflow-hidden">
              <button
                onClick={() => togglePeriod(group.key)}
                data-testid={`commission-period-${group.key}`}
                className="w-full flex items-center justify-between gap-3 px-4 py-3 bg-[#F3F3F1] hover:bg-[#EDEDEA] transition-colors text-left"
              >
                <span className="flex items-center gap-2 font-cabinet font-bold text-[14px]">
                  <ChevronDown className={`w-4 h-4 text-[#A1A1AA] shrink-0 transition-transform ${isExpanded ? "rotate-180" : ""}`} />
                  {group.label}
                </span>
                <span className="font-mono text-[11px] uppercase tracking-widest text-[#52525B]">
                  Totale: <span className="font-cabinet font-black text-[14px] text-[#0A0A0A]">{fmt(group.total)}</span>
                </span>
              </button>
              {isExpanded && (
                <div>
                  <div className="hidden md:grid grid-cols-7 gap-2 px-4 py-3 border-b border-[#E4E4E1] font-mono text-[10px] uppercase tracking-widest text-[#52525B]">
                    <div>Periodo</div><div className="col-span-2">Cliente</div><div>Mandante</div><div>Aliquota</div><div className="text-right">Importo</div><div></div>
                  </div>
                  {group.items.map((c) => (
                    <CommissionRow key={c.id} c={c} clients={clients} mandanti={mandanti} onToggleStatus={setStatus} onDelete={deleteCommission} />
                  ))}
                  {group.manualAmount !== undefined && (
                    <div className="grid grid-cols-2 md:grid-cols-7 gap-2 px-4 py-3 border-b border-[#E4E4E1] items-center text-[13px] bg-[#FFF9F5]">
                      <div className="font-mono">{group.key}</div>
                      <div className="col-span-2 font-medium text-[#52525B] flex items-center gap-1.5">
                        <Coins className="w-3.5 h-3.5 text-[#FF5A00]" /> Inserita manualmente
                      </div>
                      <div className="text-[#A1A1AA]">—</div>
                      <div className="font-mono text-[#A1A1AA]">—</div>
                      <div className="text-right font-cabinet font-bold">{fmt(group.manualAmount)}</div>
                      <div className="flex justify-end">
                        <button onClick={() => removeManualCommission(group.key)}
                          className="p-1.5 text-[#A1A1AA] hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                          title="Rimuovi provvigione manuale">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
        {periodGroups.length === 0 && (
          <div className="bg-white border border-[#E4E4E1] rounded-md p-8 text-center text-[#A1A1AA] text-[13px]">Nessuna provvigione.</div>
        )}
      </div>
    </div>
  );
}

function CommissionRow({ c, clients, mandanti, onToggleStatus, onDelete }) {
  const cli = clients.find((x) => x.id === c.client_id);
  const m = mandanti.find((x) => x.id === c.mandante_id);
  return (
    <div data-testid={`commission-${c.id}`} className="grid grid-cols-2 md:grid-cols-7 gap-2 px-4 py-3 border-b border-[#E4E4E1] items-center text-[13px]">
      <div className="font-mono">{c.period}</div>
      <div className="col-span-2 font-medium">{cli?.company_name || "—"}</div>
      <div className="text-[#52525B]">{m?.name || "—"}</div>
      <div className="font-mono">
        {c.rate}%
        {c.sale_type && <span className="text-[#A1A1AA] ml-1">({c.sale_type})</span>}
      </div>
      <div className="text-right">
        <div className="font-cabinet font-bold">{fmt(c.amount)}</div>
        <button onClick={() => onToggleStatus(c.id, c.status === "maturato" ? "incassato" : "maturato")}
          className="font-mono text-[10px] uppercase tracking-widest mt-1"
          style={{ color: c.status === "incassato" ? "#059669" : "#FF5A00" }}>
          {c.status} ↻
        </button>
      </div>
      <div className="flex justify-end">
        <button onClick={() => onDelete(c.id)}
          className="p-1.5 text-[#A1A1AA] hover:text-red-500 hover:bg-red-50 rounded transition-colors"
          title="Elimina provvigione">
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

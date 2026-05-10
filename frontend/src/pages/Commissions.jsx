import { useEffect, useState } from "react";
import api from "../api";
import { Coins, Download, Trash2, Trophy, ChevronRight } from "lucide-react";
import { toast } from "sonner";
import { exportCommissions } from "../utils/export";

const fmt = (n) => new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(n || 0);

export default function Commissions() {
  const [commissions, setCommissions] = useState([]);
  const [clients, setClients] = useState([]);
  const [mandanti, setMandanti] = useState([]);
  const [bonusSummary, setBonusSummary] = useState([]);
  const [filter, setFilter] = useState("all");

  const load = async () => {
    const [c, cl, m, bs] = await Promise.all([
      api.get("/commissions"),
      api.get("/clients"),
      api.get("/mandanti"),
      api.get("/commissions/bonus-summary").catch(() => ({ data: [] })),
    ]);
    setCommissions(c.data);
    setClients(cl.data);
    setMandanti(m.data);
    setBonusSummary(bs.data);
  };
  useEffect(() => { load(); }, []);

  const filtered = filter === "all" ? commissions : commissions.filter(c => c.status === filter);
  const accrued = commissions.filter(c => c.status === "maturato").reduce((s, c) => s + c.amount, 0);
  const collected = commissions.filter(c => c.status === "incassato").reduce((s, c) => s + c.amount, 0);

  const setStatus = async (id, status) => {
    await api.patch(`/commissions/${id}/status`, { status });
    toast.success("Stato aggiornato");
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
          <div className="font-cabinet font-black text-3xl">{fmt(accrued + collected)}</div>
          <div className="text-[11px] text-white/60 mt-2">{commissions.length} provvigioni totali</div>
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

      {/* Tabella provvigioni */}
      <div className="bg-white border border-[#E4E4E1] rounded-md overflow-hidden">
        <div className="hidden md:grid grid-cols-7 gap-2 px-4 py-3 bg-[#F3F3F1] border-b border-[#E4E4E1] font-mono text-[10px] uppercase tracking-widest text-[#52525B]">
          <div>Periodo</div><div className="col-span-2">Cliente</div><div>Mandante</div><div>Aliquota</div><div className="text-right">Importo</div><div></div>
        </div>
        {filtered.map(c => {
          const cli = clients.find(x => x.id === c.client_id);
          const m = mandanti.find(x => x.id === c.mandante_id);
          return (
            <div key={c.id} data-testid={`commission-${c.id}`} className="grid grid-cols-2 md:grid-cols-7 gap-2 px-4 py-3 border-b border-[#E4E4E1] items-center text-[13px]">
              <div className="font-mono">{c.period}</div>
              <div className="col-span-2 font-medium">{cli?.company_name || "—"}</div>
              <div className="text-[#52525B]">{m?.name || "—"}</div>
              <div className="font-mono">{c.rate}%</div>
              <div className="text-right">
                <div className="font-cabinet font-bold">{fmt(c.amount)}</div>
                <button onClick={() => setStatus(c.id, c.status === "maturato" ? "incassato" : "maturato")}
                  className="font-mono text-[10px] uppercase tracking-widest mt-1"
                  style={{ color: c.status === "incassato" ? "#059669" : "#FF5A00" }}>
                  {c.status} ↻
                </button>
              </div>
              <div className="flex justify-end">
                <button onClick={() => deleteCommission(c.id)}
                  className="p-1.5 text-[#A1A1AA] hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                  title="Elimina provvigione">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          );
        })}
        {filtered.length === 0 && <div className="p-8 text-center text-[#A1A1AA] text-[13px]">Nessuna provvigione.</div>}
      </div>
    </div>
  );
}

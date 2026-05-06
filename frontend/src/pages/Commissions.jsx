import { useEffect, useState } from "react";
import api from "../api";
import { Coins } from "lucide-react";
import { format, parseISO } from "date-fns";
import { it } from "date-fns/locale";
import { toast } from "sonner";

const fmt = (n) => new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(n || 0);

export default function Commissions() {
  const [commissions, setCommissions] = useState([]);
  const [clients, setClients] = useState([]);
  const [mandanti, setMandanti] = useState([]);
  const [filter, setFilter] = useState("all");

  const load = async () => {
    const [c, cl, m] = await Promise.all([api.get("/commissions"), api.get("/clients"), api.get("/mandanti")]);
    setCommissions(c.data); setClients(cl.data); setMandanti(m.data);
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

  return (
    <div className="p-4 md:p-8">
      <div className="border-b border-[#E4E4E1] pb-6 mb-6">
        <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00] mb-2">Guadagni</div>
        <h1 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight">Provvigioni</h1>
      </div>

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

      <div className="flex gap-2 mb-4">
        {["all", "maturato", "incassato"].map(s => (
          <button key={s} onClick={() => setFilter(s)} data-testid={`filter-${s}`}
                  className={`px-4 py-2 rounded-md text-[12px] font-medium ${filter === s ? "bg-[#0A192F] text-white" : "bg-white border border-[#E4E4E1]"}`}>
            {s === "all" ? "Tutte" : s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      <div className="bg-white border border-[#E4E4E1] rounded-md overflow-hidden">
        <div className="hidden md:grid grid-cols-6 gap-2 px-4 py-3 bg-[#F3F3F1] border-b border-[#E4E4E1] font-mono text-[10px] uppercase tracking-widest text-[#52525B]">
          <div>Periodo</div><div className="col-span-2">Cliente</div><div>Mandante</div><div>Aliquota</div><div className="text-right">Importo</div>
        </div>
        {filtered.map(c => {
          const cli = clients.find(x => x.id === c.client_id);
          const m = mandanti.find(x => x.id === c.mandante_id);
          return (
            <div key={c.id} data-testid={`commission-${c.id}`} className="grid grid-cols-2 md:grid-cols-6 gap-2 px-4 py-3 border-b border-[#E4E4E1] items-center text-[13px]">
              <div className="font-mono">{c.period}</div>
              <div className="col-span-2 font-medium">{cli?.company_name || "—"}</div>
              <div className="text-[#52525B]">{m?.name || "—"}</div>
              <div className="font-mono">{c.rate}%</div>
              <div className="text-right">
                <div className="font-cabinet font-bold">{fmt(c.amount)}</div>
                <button onClick={() => setStatus(c.id, c.status === "maturato" ? "incassato" : "maturato")}
                        className="font-mono text-[10px] uppercase tracking-widest mt-1" style={{ color: c.status === "incassato" ? "#059669" : "#FF5A00" }}>
                  {c.status} ↻
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

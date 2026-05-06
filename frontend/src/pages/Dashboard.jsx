import { useEffect, useState } from "react";
import api from "../api";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  LineChart, Line, PieChart, Pie, Cell
} from "recharts";
import { TrendingUp, Coins, Users, FileText, Target, ArrowUpRight, Calendar } from "lucide-react";
import { Link } from "react-router-dom";
import { format, parseISO } from "date-fns";
import { it } from "date-fns/locale";

const fmt = (n) => new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(n || 0);

function KPICard({ label, value, sublabel, icon: Icon, accent }) {
  return (
    <div data-testid={`kpi-${label.toLowerCase().replace(/ /g, "-")}`} className="bg-white border border-[#E4E4E1] rounded-md p-5 fade-up">
      <div className="flex items-start justify-between mb-3">
        <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA]">{label}</div>
        <Icon className="w-4 h-4 text-[#A1A1AA]" strokeWidth={1.5} />
      </div>
      <div className="font-cabinet font-black text-3xl text-[#0A0A0A] tracking-tight">{value}</div>
      {sublabel && <div className={`mt-2 text-[12px] ${accent === "success" ? "text-[#059669]" : "text-[#52525B]"}`}>{sublabel}</div>}
    </div>
  );
}

export default function Dashboard() {
  const [data, setData] = useState(null);

  useEffect(() => { api.get("/dashboard/stats").then(({ data }) => setData(data)); }, []);

  if (!data) return <div className="p-8 font-mono text-sm text-[#A1A1AA]">caricamento dashboard…</div>;

  const { kpi, by_zone, monthly, upcoming_appointments, pipeline } = data;
  const pipelineData = Object.entries(pipeline).map(([k, v]) => ({ name: k, value: v }));
  const PIE_COLORS = ["#0A192F", "#172A45", "#52525B", "#FF5A00", "#059669", "#DC2626"];

  return (
    <div className="p-4 md:p-8 space-y-6">
      {/* Header */}
      <div className="hidden md:flex items-end justify-between border-b border-[#E4E4E1] pb-6">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00] mb-2">Cruscotto · {format(new Date(), "EEEE d MMMM yyyy", { locale: it })}</div>
          <h1 className="font-cabinet font-black text-4xl tracking-tight">Buongiorno, agente.</h1>
          <p className="text-[14px] text-[#52525B] mt-2">Una panoramica viva del tuo portafoglio commerciale.</p>
        </div>
        <Link to="/ai" data-testid="dashboard-ai-cta" className="hidden md:flex items-center gap-2 px-4 py-2.5 bg-[#0A192F] hover:bg-[#172A45] text-white rounded-md text-[13px] font-medium transition-all">
          Apri assistente AI <ArrowUpRight className="w-4 h-4 text-[#FF5A00]" />
        </Link>
      </div>

      {/* KPI grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard label="Fatturato vinto" value={fmt(kpi.revenue_won)} sublabel="Da inizio anno" icon={TrendingUp} accent="success" />
        <KPICard label="Pipeline aperta" value={fmt(kpi.revenue_pipeline)} sublabel={`${kpi.offers_count} offerte`} icon={FileText} />
        <KPICard label="Provvigioni" value={fmt(kpi.commissions_accrued + kpi.commissions_collected)} sublabel={`${fmt(kpi.commissions_collected)} incassate`} icon={Coins} />
        <KPICard label="Portafoglio" value={kpi.clients_count} sublabel={`${kpi.leads_count} lead in pipeline`} icon={Users} />
      </div>

      {/* Goal */}
      <div className="bg-white border border-[#E4E4E1] rounded-md p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Target className="w-4 h-4 text-[#FF5A00]" />
            <span className="font-mono text-[10px] uppercase tracking-widest text-[#52525B]">Obiettivo del mese</span>
          </div>
          <div className="font-mono text-[12px] text-[#0A0A0A] font-semibold">{kpi.goal_pct}%</div>
        </div>
        <div className="flex items-end justify-between mb-2">
          <div className="font-cabinet font-black text-2xl">{fmt(kpi.current_month_revenue)}</div>
          <div className="text-[12px] text-[#52525B]">target {fmt(kpi.monthly_goal)}</div>
        </div>
        <div className="h-2 bg-[#F3F3F1] rounded-full overflow-hidden">
          <div className="h-full bg-[#FF5A00] transition-all duration-500" style={{ width: `${Math.min(100, kpi.goal_pct)}%` }} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Monthly chart */}
        <div className="lg:col-span-2 bg-white border border-[#E4E4E1] rounded-md p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA]">Andamento mensile</div>
              <div className="font-cabinet font-bold text-lg mt-1">Fatturato per mese</div>
            </div>
          </div>
          <div className="h-56">
            <ResponsiveContainer>
              <LineChart data={monthly}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E1" />
                <XAxis dataKey="month" stroke="#A1A1AA" fontSize={11} />
                <YAxis stroke="#A1A1AA" fontSize={11} tickFormatter={(v) => `€${(v/1000).toFixed(0)}k`} />
                <Tooltip contentStyle={{ background: "white", border: "1px solid #E4E4E1", borderRadius: "6px" }} formatter={(v) => fmt(v)} />
                <Line type="monotone" dataKey="revenue" stroke="#FF5A00" strokeWidth={2.5} dot={{ fill: "#0A192F", r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Pipeline */}
        <div className="bg-white border border-[#E4E4E1] rounded-md p-5">
          <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] mb-1">Lead pipeline</div>
          <div className="font-cabinet font-bold text-lg mb-3">Per stato</div>
          <div className="h-44">
            <ResponsiveContainer>
              <PieChart>
                <Pie data={pipelineData} dataKey="value" nameKey="name" innerRadius={40} outerRadius={70} paddingAngle={2}>
                  {pipelineData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ background: "white", border: "1px solid #E4E4E1", borderRadius: "6px" }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="space-y-1 mt-2">
            {pipelineData.map((p, i) => (
              <div key={p.name} className="flex items-center justify-between text-[12px]">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                  <span className="capitalize text-[#52525B]">{p.name}</span>
                </div>
                <span className="font-mono font-semibold">{p.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* By zone */}
        <div className="bg-white border border-[#E4E4E1] rounded-md p-5">
          <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] mb-1">Geografia</div>
          <div className="font-cabinet font-bold text-lg mb-3">Fatturato per zona</div>
          <div className="h-48">
            <ResponsiveContainer>
              <BarChart data={by_zone}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E1" />
                <XAxis dataKey="zone" stroke="#A1A1AA" fontSize={11} />
                <YAxis stroke="#A1A1AA" fontSize={11} tickFormatter={(v) => `€${(v/1000).toFixed(0)}k`} />
                <Tooltip contentStyle={{ background: "white", border: "1px solid #E4E4E1", borderRadius: "6px" }} formatter={(v) => fmt(v)} />
                <Bar dataKey="revenue" fill="#0A192F" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Upcoming */}
        <div className="bg-white border border-[#E4E4E1] rounded-md p-5">
          <div className="flex items-center justify-between mb-3">
            <div>
              <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA]">Prossimi 7 giorni</div>
              <div className="font-cabinet font-bold text-lg mt-1">Visite in agenda</div>
            </div>
            <Link to="/agenda" className="font-mono text-[10px] uppercase tracking-widest text-[#FF5A00]">Vedi tutto</Link>
          </div>
          <div className="space-y-2">
            {upcoming_appointments.length === 0 && <div className="text-[13px] text-[#A1A1AA] py-6 text-center">Nessuna visita pianificata.</div>}
            {upcoming_appointments.map((a) => (
              <div key={a.id} data-testid={`upcoming-appt-${a.id}`} className="flex items-center gap-3 p-3 border border-[#E4E4E1] rounded-md hover:border-[#0A192F] transition-colors">
                <div className="w-12 text-center shrink-0">
                  <div className="font-cabinet font-black text-lg leading-none">{format(parseISO(a.start), "d")}</div>
                  <div className="font-mono text-[9px] uppercase tracking-widest text-[#A1A1AA] mt-0.5">{format(parseISO(a.start), "MMM", { locale: it })}</div>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-[13px] truncate">{a.title}</div>
                  <div className="text-[11px] text-[#52525B] truncate flex items-center gap-1.5"><Calendar className="w-3 h-3" />{format(parseISO(a.start), "HH:mm")} · {a.location}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

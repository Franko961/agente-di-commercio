import { useEffect, useState } from "react";
import api from "../api";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  LineChart, Line, PieChart, Pie, Cell
} from "recharts";
import { TrendingUp, Coins, Users, FileText, Target, ArrowUpRight, Calendar, PhoneCall, AlertTriangle, Banknote, Navigation, Sparkles, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { format, parseISO } from "date-fns";
import { it } from "date-fns/locale";
import { useMandante } from "../contexts/MandanteContext";

const fmt = (n) => new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(n || 0);
const EXPENSE_CATEGORY_LABELS = {
  carburante: "Carburante", vitto: "Vitto", alloggio: "Alloggio",
  pedaggio_parcheggio: "Pedaggio/Parcheggio", materiali: "Materiali",
  inps: "INPS", enasarco: "ENASARCO", assicurazione_auto: "Assicurazione auto",
  commercialista: "Commercialista", altro: "Altro",
};
// Colore fisso per categoria, coerente tra grafico mensile e grafico a torta
const EXPENSE_CATEGORY_COLORS = {
  carburante: "#FF5A00", vitto: "#059669", alloggio: "#7C3AED",
  pedaggio_parcheggio: "#0EA5E9", materiali: "#DC2626",
  inps: "#0A192F", enasarco: "#B45309", assicurazione_auto: "#DB2777",
  commercialista: "#65A30D", altro: "#A1A1AA",
};

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

// "scade venerdì" se entro 6 giorni, altrimenti "scade 24 luglio"
function formatExpiry(dateStr) {
  if (!dateStr) return "";
  const d = parseISO(dateStr);
  const diffDays = Math.round((d - new Date()) / 86400000);
  return diffDays <= 6 ? format(d, "EEEE", { locale: it }) : format(d, "d MMMM", { locale: it });
}

function focusClientSentence(focus) {
  if (!focus) return null;
  if (focus.reason === "expiry_and_inactivity") {
    return `Visita prima ${focus.client_name}, perché non effettua ordini da ${focus.days_since_last_order} giorni e l'ultima offerta scade ${formatExpiry(focus.offer_expires_at)}.`;
  }
  if (focus.reason === "expiry_only") {
    return `Visita prima ${focus.client_name}: l'offerta "${focus.offer_title}" scade ${formatExpiry(focus.offer_expires_at)}.`;
  }
  if (focus.reason === "inactivity_only") {
    // days_since_last_visit è null quando il cliente non ha MAI avuto una
    // visita registrata (non solo "da tanti giorni") — vedi
    // dashboard_service.py, max_days == 9999 -> None.
    const daysPart = focus.days_since_last_visit != null
      ? `non lo senti da ${focus.days_since_last_visit} giorni`
      : "non hai ancora registrato nessuna visita con lui";
    return `Contatta ${focus.client_name}: ${daysPart}.`;
  }
  return null;
}

function projectionSentence(today) {
  const pct = today?.projected_pct_if_expiring_closed;
  const n = today?.offers_expiring || 0;
  if (pct == null || n === 0) return null;
  const offerteLabel = n === 1 ? "l'offerta in scadenza" : `le ${n} offerte in scadenza`;
  return `Se chiudi ${offerteLabel} raggiungeresti il ${pct}% dell'obiettivo mensile.`;
}

function TodayStat({ to, icon: Icon, value, label }) {
  return (
    <Link to={to} className="flex items-center gap-3 py-3 px-3 rounded-md hover:bg-[#F3F3F1] transition-colors">
      <div className="w-9 h-9 rounded-md bg-[#F3F3F1] flex items-center justify-center shrink-0">
        <Icon className="w-4 h-4 text-[#0A192F]" strokeWidth={1.75} />
      </div>
      <div className="min-w-0">
        <div className="font-cabinet font-black text-xl leading-none">{value}</div>
        <div className="text-[11px] text-[#52525B] mt-1 truncate">{label}</div>
      </div>
    </Link>
  );
}

function GoalRow({ label, current, target, pct, highlight }) {
  const safePct = pct ?? 0;
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {highlight && <Target className="w-4 h-4 text-[#FF5A00]" />}
          <span className="font-mono text-[10px] uppercase tracking-widest text-[#52525B]">{label}</span>
        </div>
        <div className="font-mono text-[12px] text-[#0A0A0A] font-semibold">{safePct}%</div>
      </div>
      <div className="flex items-end justify-between mb-2">
        <div className="font-cabinet font-black text-2xl">{current}</div>
        <div className="text-[12px] text-[#52525B]">target {target}</div>
      </div>
      <div className="h-2 bg-[#F3F3F1] rounded-full overflow-hidden">
        <div className="h-full bg-[#FF5A00] transition-all duration-500" style={{ width: `${Math.min(100, safePct)}%` }} />
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [today, setToday] = useState(null);
  const { activeMandante } = useMandante();
  const mandanteParam = activeMandante && activeMandante !== "all" ? activeMandante : undefined;

  useEffect(() => {
    api.get("/dashboard/stats", { params: { mandante_id: mandanteParam } }).then(({ data }) => setData(data));
  }, [mandanteParam]);
  useEffect(() => {
    api.get("/dashboard/today", { params: { mandante_id: mandanteParam } }).then(({ data }) => setToday(data)).catch(() => {});
  }, [mandanteParam]);

  if (!data) return <div className="p-8 font-mono text-sm text-[#A1A1AA]">caricamento dashboard…</div>;

  const { kpi, by_zone, monthly, upcoming_appointments, pipeline, by_sector, expenses_monthly, expenses_by_category } = data;
  const pipelineData = Object.entries(pipeline).map(([k, v]) => ({ name: k, value: v }));
  const sectorData = (by_sector || []).filter(s => s.sector !== "Non specificato");
  const expenseCatData = (expenses_by_category || []).map(e => ({ ...e, label: EXPENSE_CATEGORY_LABELS[e.category] || e.category }));
  const expenseCategoriesPresent = (expenses_by_category || []).map(e => e.category);
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
        <Link to="/app/ai" data-testid="dashboard-ai-cta" className="hidden md:flex items-center gap-2 px-4 py-2.5 bg-[#0A192F] hover:bg-[#172A45] text-white rounded-md text-[13px] font-medium transition-all">
          Apri assistente AI <ArrowUpRight className="w-4 h-4 text-[#FF5A00]" />
        </Link>
      </div>

      {/* Oggi — home operativa */}
      {today && (
        <div className="bg-white border border-[#E4E4E1] rounded-md fade-up">
          <div className="px-5 pt-5 flex items-center justify-between">
            <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00]">
              Oggi · {format(new Date(), "EEEE d MMMM", { locale: it })}
            </div>
          </div>
          <div className="px-2 md:px-3 py-2 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-1">
            <TodayStat to="/app/agenda" icon={Calendar} value={today.appointments_today} label={today.appointments_today === 1 ? "appuntamento" : "appuntamenti"} />
            <TodayStat to="/app/clienti" icon={PhoneCall} value={today.clients_to_call} label={today.clients_to_call === 1 ? "cliente da richiamare" : "clienti da richiamare"} />
            <TodayStat to="/app/offerte" icon={AlertTriangle} value={today.offers_expiring} label={today.offers_expiring === 1 ? "offerta in scadenza" : "offerte in scadenza"} />
            <TodayStat to="/app/provvigioni" icon={Banknote} value={today.payments_to_verify} label={today.payments_to_verify === 1 ? "pagamento da verificare" : "pagamenti da verificare"} />
            <TodayStat to="/app/mappa" icon={Navigation} value={today.km_today != null ? `${today.km_today} km` : "—"} label="km previsti" />
            <TodayStat to="/app/provvigioni" icon={Target} value={fmt(today.daily_goal)} label="obiettivo del giorno" />
          </div>
          {(focusClientSentence(today.focus_client) || projectionSentence(today)) && (
            <div className="mx-4 mb-4 mt-1 flex items-start gap-2.5 bg-[#FFF7ED] border border-[#FED7AA] rounded-md px-4 py-3">
              <Sparkles className="w-4 h-4 text-[#FF5A00] shrink-0 mt-0.5" />
              <div className="text-[13px] text-[#0A0A0A] leading-snug space-y-1">
                <span className="font-mono text-[10px] uppercase tracking-widest text-[#FF5A00] block mb-1">Suggerimento AI</span>
                {focusClientSentence(today.focus_client) && <div>{focusClientSentence(today.focus_client)}</div>}
                {projectionSentence(today) && <div>{projectionSentence(today)}</div>}
              </div>
              {today.focus_client?.client_id && (
                <Link to={`/app/clienti/${today.focus_client.client_id}`} className="ml-auto shrink-0 mt-0.5">
                  <ArrowRight className="w-4 h-4 text-[#FF5A00]" />
                </Link>
              )}
            </div>
          )}
        </div>
      )}

      {/* KPI grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard label="Fatturato vinto" value={fmt(kpi.revenue_won)} sublabel="Da inizio anno" icon={TrendingUp} accent="success" />
        <KPICard label="Pipeline aperta" value={fmt(kpi.revenue_pipeline)} sublabel={`${kpi.offers_count} offerte`} icon={FileText} />
        <KPICard label="Provvigioni" value={fmt(kpi.commissions_accrued + kpi.commissions_collected)} sublabel={`${fmt(kpi.commissions_collected)} incassate`} icon={Coins} />
        <KPICard label="Portafoglio" value={kpi.clients_count} sublabel={`${kpi.leads_count} lead in pipeline`} icon={Users} />
      </div>

      {/* Goal */}
      <div className="bg-white border border-[#E4E4E1] rounded-md p-5 space-y-5">
        <GoalRow
          label="Fatturato del mese"
          current={fmt(kpi.current_month_revenue)}
          target={fmt(kpi.monthly_goal)}
          pct={kpi.goal_pct}
          highlight
        />
        {kpi.commissions_goal != null && (
          <GoalRow
            label="Provvigioni del mese"
            current={fmt(kpi.commissions_month)}
            target={fmt(kpi.commissions_goal)}
            pct={kpi.commissions_goal_pct}
          />
        )}
        {kpi.new_clients_goal != null && (
          <GoalRow
            label="Nuovi clienti del mese"
            current={kpi.new_clients_month}
            target={kpi.new_clients_goal}
            pct={kpi.new_clients_goal_pct}
          />
        )}
        {kpi.visits_goal != null && (
          <GoalRow
            label="Visite del mese"
            current={kpi.visits_month}
            target={kpi.visits_goal}
            pct={kpi.visits_goal_pct}
          />
        )}
        {(kpi.commissions_goal == null || kpi.new_clients_goal == null || kpi.visits_goal == null) && (
          <Link to="/app/impostazioni" className="block text-[11px] text-[#A1A1AA] hover:text-[#FF5A00] font-mono">
            + Imposta altri obiettivi (provvigioni, nuovi clienti, visite) →
          </Link>
        )}
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
            <Link to="/app/agenda" className="font-mono text-[10px] uppercase tracking-widest text-[#FF5A00]">Vedi tutto</Link>
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

        {/* Grafico settori merceologici */}
        {sectorData.length > 0 && (
          <div className="bg-white border border-[#E4E4E1] rounded-md p-5">
            <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] mb-4">Clienti per settore</div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-center">
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={sectorData} dataKey="count" nameKey="sector" innerRadius={45} outerRadius={80} paddingAngle={2}>
                    {sectorData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={(v) => [`${v} clienti`]} />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-2">
                {sectorData.map((s, i) => (
                  <div key={s.sector} className="flex items-center justify-between text-[12px]">
                    <div className="flex items-center gap-2">
                      <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                      <span className="text-[#52525B]">{s.sector}</span>
                    </div>
                    <span className="font-cabinet font-bold">{s.count}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Spese: andamento mensile per categoria (barre impilate) */}
        <div className="bg-white border border-[#E4E4E1] rounded-md p-5">
          <div className="flex items-center justify-between mb-1">
            <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA]">Note spese</div>
            <div className="font-mono text-[11px] text-[#52525B]">questo mese: <span className="font-cabinet font-bold text-[#0A0A0A]">{fmt(kpi.current_month_expenses)}</span></div>
          </div>
          <div className="font-cabinet font-bold text-lg mb-3">Spese per mese, per categoria</div>
          <div className="h-56">
            <ResponsiveContainer>
              <BarChart data={expenses_monthly}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E1" />
                <XAxis dataKey="month" stroke="#A1A1AA" fontSize={11} />
                <YAxis stroke="#A1A1AA" fontSize={11} tickFormatter={(v) => `€${(v/1000).toFixed(1)}k`} />
                <Tooltip
                  contentStyle={{ background: "white", border: "1px solid #E4E4E1", borderRadius: "6px" }}
                  formatter={(v, name) => [fmt(v), EXPENSE_CATEGORY_LABELS[name] || name]}
                />
                {expenseCategoriesPresent.map((cat) => (
                  <Bar key={cat} dataKey={cat} stackId="spese" fill={EXPENSE_CATEGORY_COLORS[cat] || "#A1A1AA"} radius={[0, 0, 0, 0]} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-wrap gap-x-4 gap-y-1.5 mt-3">
            {expenseCategoriesPresent.map((cat) => (
              <div key={cat} className="flex items-center gap-1.5 text-[11px] text-[#52525B]">
                <span className="w-2 h-2 rounded-full shrink-0" style={{ background: EXPENSE_CATEGORY_COLORS[cat] || "#A1A1AA" }} />
                {EXPENSE_CATEGORY_LABELS[cat] || cat}
              </div>
            ))}
          </div>
        </div>

        {/* Spese per categoria */}
        {expenseCatData.length > 0 && (
          <div className="bg-white border border-[#E4E4E1] rounded-md p-5">
            <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] mb-4">Spese per categoria</div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-center">
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={expenseCatData} dataKey="amount" nameKey="label" innerRadius={45} outerRadius={80} paddingAngle={2}>
                    {expenseCatData.map((e) => <Cell key={e.category} fill={EXPENSE_CATEGORY_COLORS[e.category] || "#A1A1AA"} />)}
                  </Pie>
                  <Tooltip formatter={(v) => fmt(v)} />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-2">
                {expenseCatData.map((e) => (
                  <div key={e.category} className="flex items-center justify-between text-[12px]">
                    <div className="flex items-center gap-2">
                      <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: EXPENSE_CATEGORY_COLORS[e.category] || "#A1A1AA" }} />
                      <span className="text-[#52525B]">{e.label}</span>
                    </div>
                    <span className="font-cabinet font-bold">{fmt(e.amount)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

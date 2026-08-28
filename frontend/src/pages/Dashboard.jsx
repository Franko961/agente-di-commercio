import { useEffect, useState } from "react";
import { getDashboardStats, getDashboardToday } from "../api/dashboard";
import { TrendingUp, Coins, Users, FileText, ArrowUpRight } from "lucide-react";
import { Link } from "react-router-dom";
import { format } from "date-fns";
import { it } from "date-fns/locale";
import { useMandante } from "../contexts/MandanteContext";
import { useAuth } from "../contexts/AuthContext";
import { CORE_MODULE_KEYS, fmt, EXPENSE_CATEGORY_LABELS } from "../components/dashboard/constants";
import PresenzeWidget from "../components/dashboard/PresenzeWidget";
import ExtraModulesHome from "../components/dashboard/ExtraModulesHome";
import TodaySection from "../components/dashboard/TodaySection";
import GoalsSection from "../components/dashboard/GoalsSection";
import {
  KPICard, MonthlyRevenueChart, PipelineChart, ZoneChart, UpcomingAppointments,
  SectorChart, ExpensesMonthlyChart, ExpensesCategoryChart,
} from "../components/dashboard/Charts";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [today, setToday] = useState(null);
  const { activeMandante } = useMandante();
  const { user } = useAuth();
  const mandanteParam = activeMandante && activeMandante !== "all" ? activeMandante : undefined;

  const disabledModules = user?.disabled_modules || [];
  const enabledExtraModules = user?.enabled_extra_modules || [];
  const noCoreModules = CORE_MODULE_KEYS.every((m) => disabledModules.includes(m));

  useEffect(() => {
    if (noCoreModules) return;
    getDashboardStats(mandanteParam).then(setData);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mandanteParam, noCoreModules]);
  useEffect(() => {
    if (noCoreModules) return;
    getDashboardToday(mandanteParam).then(setToday).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mandanteParam, noCoreModules]);

  if (noCoreModules) return <ExtraModulesHome user={user} enabledExtraModules={enabledExtraModules} />;

  if (!data) return <div className="p-8 font-mono text-sm text-[#6B6B72]">caricamento dashboard…</div>;

  const { kpi, by_zone, monthly, upcoming_appointments, pipeline, by_sector, expenses_monthly, expenses_by_category } = data;
  const pipelineData = Object.entries(pipeline).map(([k, v]) => ({ name: k, value: v }));
  const sectorData = (by_sector || []).filter(s => s.sector !== "Non specificato");
  const expenseCatData = (expenses_by_category || []).map(e => ({ ...e, label: EXPENSE_CATEGORY_LABELS[e.category] || e.category }));
  const expenseCategoriesPresent = (expenses_by_category || []).map(e => e.category);

  return (
    <div className="p-4 md:p-8 space-y-6">
      {/* Header */}
      <div className="hidden md:flex items-end justify-between border-b border-[#E4E4E1] pb-6">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#B23E00] mb-2">Cruscotto · {format(new Date(), "EEEE d MMMM yyyy", { locale: it })}</div>
          <h1 className="font-cabinet font-black text-4xl tracking-tight">Buongiorno, agente.</h1>
          <p className="text-[14px] text-[#52525B] mt-2">Una panoramica viva del tuo portafoglio commerciale.</p>
        </div>
        <Link to="/app/ai" data-testid="dashboard-ai-cta" className="hidden md:flex items-center gap-2 px-4 py-2.5 bg-[#0A192F] hover:bg-[#172A45] text-white rounded-md text-[13px] font-medium transition-all">
          Apri assistente AI <ArrowUpRight className="w-4 h-4 text-[#B23E00]" />
        </Link>
      </div>

      {/* Oggi — home operativa */}
      {today && <TodaySection today={today} />}

      {/* Presenze oggi — solo per gli account con il modulo Personale attivo */}
      {enabledExtraModules.includes("personale") && <PresenzeWidget />}

      {/* KPI grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard label="Fatturato vinto" value={fmt(kpi.revenue_won)} sublabel="Da inizio anno" icon={TrendingUp} accent="success" />
        <KPICard label="Pipeline aperta" value={fmt(kpi.revenue_pipeline)} sublabel={`${kpi.offers_count} offerte`} icon={FileText} />
        <KPICard label="Provvigioni" value={fmt(kpi.commissions_accrued + kpi.commissions_collected)} sublabel={`${fmt(kpi.commissions_collected)} incassate`} icon={Coins} />
        <KPICard label="Portafoglio" value={kpi.clients_count} sublabel={`${kpi.leads_count} lead in pipeline`} icon={Users} />
      </div>

      <GoalsSection kpi={kpi} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <MonthlyRevenueChart monthly={monthly} />
        <PipelineChart pipelineData={pipelineData} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ZoneChart by_zone={by_zone} />
        <UpcomingAppointments upcoming_appointments={upcoming_appointments} />
        <SectorChart sectorData={sectorData} />
        <ExpensesMonthlyChart expenses_monthly={expenses_monthly} expenseCategoriesPresent={expenseCategoriesPresent} current_month_expenses={kpi.current_month_expenses} />
        <ExpensesCategoryChart expenseCatData={expenseCatData} />
      </div>
    </div>
  );
}

import { Link } from "react-router-dom";
import { format, parseISO } from "date-fns";
import { it } from "date-fns/locale";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  LineChart, Line, PieChart, Pie, Cell
} from "recharts";
import { Calendar } from "lucide-react";
import { fmt, EXPENSE_CATEGORY_LABELS, EXPENSE_CATEGORY_COLORS, PIE_COLORS } from "./constants";

export function KPICard({ label, value, sublabel, icon: Icon, accent }) {
  return (
    <div data-testid={`kpi-${label.toLowerCase().replace(/ /g, "-")}`} className="bg-white border border-[#E4E4E1] rounded-md p-5 fade-up">
      <div className="flex items-start justify-between mb-3">
        <div className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72]">{label}</div>
        <Icon className="w-4 h-4 text-[#6B6B72]" strokeWidth={1.5} />
      </div>
      <div className="font-cabinet font-black text-3xl text-[#0A0A0A] tracking-tight">{value}</div>
      {sublabel && <div className={`mt-2 text-[12px] ${accent === "success" ? "text-[#059669]" : "text-[#52525B]"}`}>{sublabel}</div>}
    </div>
  );
}

export function MonthlyRevenueChart({ monthly }) {
  return (
    <div className="lg:col-span-2 bg-white border border-[#E4E4E1] rounded-md p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72]">Andamento mensile</div>
          <div className="font-cabinet font-bold text-lg mt-1">Fatturato per mese</div>
        </div>
      </div>
      <div className="h-56">
        <ResponsiveContainer>
          <LineChart data={monthly}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E1" />
            <XAxis dataKey="month" stroke="#6B6B72" fontSize={11} />
            <YAxis stroke="#6B6B72" fontSize={11} tickFormatter={(v) => `€${(v/1000).toFixed(0)}k`} />
            <Tooltip contentStyle={{ background: "white", border: "1px solid #E4E4E1", borderRadius: "6px" }} formatter={(v) => fmt(v)} />
            <Line type="monotone" dataKey="revenue" stroke="#B23E00" strokeWidth={2.5} dot={{ fill: "#0A192F", r: 4 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function PipelineChart({ pipelineData }) {
  return (
    <div className="bg-white border border-[#E4E4E1] rounded-md p-5">
      <div className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72] mb-1">Lead pipeline</div>
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
  );
}

export function ZoneChart({ by_zone }) {
  return (
    <div className="bg-white border border-[#E4E4E1] rounded-md p-5">
      <div className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72] mb-1">Geografia</div>
      <div className="font-cabinet font-bold text-lg mb-3">Fatturato per zona</div>
      <div className="h-48">
        <ResponsiveContainer>
          <BarChart data={by_zone}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E1" />
            <XAxis dataKey="zone" stroke="#6B6B72" fontSize={11} />
            <YAxis stroke="#6B6B72" fontSize={11} tickFormatter={(v) => `€${(v/1000).toFixed(0)}k`} />
            <Tooltip contentStyle={{ background: "white", border: "1px solid #E4E4E1", borderRadius: "6px" }} formatter={(v) => fmt(v)} />
            <Bar dataKey="revenue" fill="#0A192F" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function UpcomingAppointments({ upcoming_appointments }) {
  return (
    <div className="bg-white border border-[#E4E4E1] rounded-md p-5">
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72]">Prossimi 7 giorni</div>
          <div className="font-cabinet font-bold text-lg mt-1">Visite in agenda</div>
        </div>
        <Link to="/app/agenda" className="font-mono text-[10px] uppercase tracking-widest text-[#B23E00]">Vedi tutto</Link>
      </div>
      <div className="space-y-2">
        {upcoming_appointments.length === 0 && <div className="text-[13px] text-[#6B6B72] py-6 text-center">Nessuna visita pianificata.</div>}
        {upcoming_appointments.map((a) => (
          <div key={a.id} data-testid={`upcoming-appt-${a.id}`} className="flex items-center gap-3 p-3 border border-[#E4E4E1] rounded-md hover:border-[#0A192F] transition-colors">
            <div className="w-12 text-center shrink-0">
              <div className="font-cabinet font-black text-lg leading-none">{format(parseISO(a.start), "d")}</div>
              <div className="font-mono text-[9px] uppercase tracking-widest text-[#6B6B72] mt-0.5">{format(parseISO(a.start), "MMM", { locale: it })}</div>
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-medium text-[13px] truncate">{a.title}</div>
              <div className="text-[11px] text-[#52525B] truncate flex items-center gap-1.5"><Calendar className="w-3 h-3" />{format(parseISO(a.start), "HH:mm")} · {a.location}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function SectorChart({ sectorData }) {
  if (sectorData.length === 0) return null;
  return (
    <div className="bg-white border border-[#E4E4E1] rounded-md p-5">
      <div className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72] mb-4">Clienti per settore</div>
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
  );
}

export function ExpensesMonthlyChart({ expenses_monthly, expenseCategoriesPresent, current_month_expenses }) {
  return (
    <div className="bg-white border border-[#E4E4E1] rounded-md p-5">
      <div className="flex items-center justify-between mb-1">
        <div className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72]">Note spese</div>
        <div className="font-mono text-[11px] text-[#52525B]">questo mese: <span className="font-cabinet font-bold text-[#0A0A0A]">{fmt(current_month_expenses)}</span></div>
      </div>
      <div className="font-cabinet font-bold text-lg mb-3">Spese per mese, per categoria</div>
      <div className="h-56">
        <ResponsiveContainer>
          <BarChart data={expenses_monthly}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E4E4E1" />
            <XAxis dataKey="month" stroke="#6B6B72" fontSize={11} />
            <YAxis stroke="#6B6B72" fontSize={11} tickFormatter={(v) => `€${(v/1000).toFixed(1)}k`} />
            <Tooltip
              contentStyle={{ background: "white", border: "1px solid #E4E4E1", borderRadius: "6px" }}
              formatter={(v, name) => [fmt(v), EXPENSE_CATEGORY_LABELS[name] || name]}
            />
            {expenseCategoriesPresent.map((cat) => (
              <Bar key={cat} dataKey={cat} stackId="spese" fill={EXPENSE_CATEGORY_COLORS[cat] || "#6B6B72"} radius={[0, 0, 0, 0]} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1.5 mt-3">
        {expenseCategoriesPresent.map((cat) => (
          <div key={cat} className="flex items-center gap-1.5 text-[11px] text-[#52525B]">
            <span className="w-2 h-2 rounded-full shrink-0" style={{ background: EXPENSE_CATEGORY_COLORS[cat] || "#6B6B72" }} />
            {EXPENSE_CATEGORY_LABELS[cat] || cat}
          </div>
        ))}
      </div>
    </div>
  );
}

export function ExpensesCategoryChart({ expenseCatData }) {
  if (expenseCatData.length === 0) return null;
  return (
    <div className="bg-white border border-[#E4E4E1] rounded-md p-5">
      <div className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72] mb-4">Spese per categoria</div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-center">
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie data={expenseCatData} dataKey="amount" nameKey="label" innerRadius={45} outerRadius={80} paddingAngle={2}>
              {expenseCatData.map((e) => <Cell key={e.category} fill={EXPENSE_CATEGORY_COLORS[e.category] || "#6B6B72"} />)}
            </Pie>
            <Tooltip formatter={(v) => fmt(v)} />
          </PieChart>
        </ResponsiveContainer>
        <div className="space-y-2">
          {expenseCatData.map((e) => (
            <div key={e.category} className="flex items-center justify-between text-[12px]">
              <div className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: EXPENSE_CATEGORY_COLORS[e.category] || "#6B6B72" }} />
                <span className="text-[#52525B]">{e.label}</span>
              </div>
              <span className="font-cabinet font-bold">{fmt(e.amount)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

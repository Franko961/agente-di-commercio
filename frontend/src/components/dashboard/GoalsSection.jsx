import { Link } from "react-router-dom";
import { Target } from "lucide-react";
import { fmt } from "./constants";

function GoalRow({ label, current, target, pct, highlight }) {
  const safePct = pct ?? 0;
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {highlight && <Target className="w-4 h-4 text-[#B23E00]" />}
          <span className="font-mono text-[10px] uppercase tracking-widest text-[#52525B]">{label}</span>
        </div>
        <div className="font-mono text-[12px] text-[#0A0A0A] font-semibold">{safePct}%</div>
      </div>
      <div className="flex items-end justify-between mb-2">
        <div className="font-cabinet font-black text-2xl">{current}</div>
        <div className="text-[12px] text-[#52525B]">target {target}</div>
      </div>
      <div className="h-2 bg-[#F3F3F1] rounded-full overflow-hidden">
        <div className="h-full bg-[#B23E00] transition-all duration-500" style={{ width: `${Math.min(100, safePct)}%` }} />
      </div>
    </div>
  );
}

export default function GoalsSection({ kpi }) {
  return (
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
          label="Provvigioni totali del mese"
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
        <Link to="/app/impostazioni" className="block text-[11px] text-[#6B6B72] hover:text-[#B23E00] font-mono">
          + Imposta altri obiettivi (provvigioni, nuovi clienti, visite) →
        </Link>
      )}
    </div>
  );
}

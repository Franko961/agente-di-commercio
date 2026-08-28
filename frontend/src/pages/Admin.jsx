import { useState } from "react";
import { TrendingUp, Activity, ShieldCheck, Star } from "lucide-react";
import BusinessTab from "../components/admin/BusinessTab";
import HealthTab from "../components/admin/HealthTab";
import AuditTab from "../components/admin/AuditTab";
import FeedbackTab from "../components/admin/FeedbackTab";

const TABS = [
  { key: "business", label: "Business", icon: TrendingUp },
  { key: "salute", label: "Salute applicativa", icon: Activity },
  { key: "audit", label: "Audit log", icon: ShieldCheck },
  { key: "feedback", label: "Feedback", icon: Star },
];

export default function Admin() {
  const [tab, setTab] = useState("business"); // business | salute | audit | feedback

  return (
    <div className="p-4 md:p-8">
      <div className="border-b border-[#E4E4E1] pb-4 mb-6 flex items-end justify-between flex-wrap gap-4">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#B23E00] mb-2">Pannello</div>
          <h1 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight">Admin Dashboard</h1>
        </div>
        <div className="flex gap-1 bg-[#F3F3F1] rounded-md p-1">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-[12px] font-medium transition-colors ${
                tab === t.key ? "bg-white text-[#0A192F] shadow-sm" : "text-[#52525B] hover:text-[#0A192F]"
              }`}
            >
              <t.icon className="w-3.5 h-3.5" /> {t.label}
            </button>
          ))}
        </div>
      </div>

      {tab === "business" && <BusinessTab />}
      {tab === "salute" && <HealthTab />}
      {tab === "audit" && <AuditTab />}
      {tab === "feedback" && <FeedbackTab />}
    </div>
  );
}

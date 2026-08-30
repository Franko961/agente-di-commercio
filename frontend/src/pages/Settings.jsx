import { useState } from "react";
import { Plug, Target, Home, History, ShieldCheck, Star, Percent } from "lucide-react";
import AiActionsLog from "../components/AiActionsLog";
import IntegrazioniTab from "../components/settings/IntegrazioniTab";
import ObiettiviTab from "../components/settings/ObiettiviTab";
import PercorsiTab from "../components/settings/PercorsiTab";
import FiscaleTab from "../components/settings/FiscaleTab";
import PrivacyTab from "../components/settings/PrivacyTab";
import FeedbackTab from "../components/settings/FeedbackTab";

const TABS = [
  ["integrazioni", "Integrazioni", Plug],
  ["obiettivi", "Obiettivi", Target],
  ["percorsi", "Punti di partenza", Home],
  ["fiscale", "Situazione fiscale", Percent],
  ["registro-ai", "Registro AI", History],
  ["privacy", "Privacy e dati", ShieldCheck],
  ["feedback", "Feedback", Star],
];

export default function Settings() {
  const [tab, setTab] = useState("integrazioni");

  return (
    <div className={tab === "registro-ai" ? "max-w-5xl" : "max-w-3xl"}>
      {/* overflow-x-auto: senza, i tab non ci stanno su una riga sotto una
      certa larghezza e si accavallano — stesso pattern già corretto in
      ClientDetail.jsx per lo stesso motivo. */}
      <div className="flex items-center gap-1 mb-6 border-b border-[#E4E4E1] overflow-x-auto">
        {TABS.map(([key, label, Icon]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-1.5 px-3 py-2.5 text-[13px] font-medium whitespace-nowrap border-b-2 -mb-px transition-colors ${
              tab === key ? "border-[#B23E00] text-[#0A192F]" : "border-transparent text-[#6B6B72] hover:text-[#52525B]"
            }`}
          >
            <Icon className="w-3.5 h-3.5" /> {label}
          </button>
        ))}
      </div>

      {tab === "integrazioni" && <IntegrazioniTab />}
      {tab === "obiettivi" && <ObiettiviTab />}
      {tab === "percorsi" && <PercorsiTab />}
      {tab === "fiscale" && <FiscaleTab />}
      {tab === "registro-ai" && <AiActionsLog />}
      {tab === "privacy" && <PrivacyTab />}
      {tab === "feedback" && <FeedbackTab />}
    </div>
  );
}

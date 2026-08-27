import { MiniStat } from "./AssenzeTab";

export default function KpiTab({ summary }) {
  if (!summary) return null;
  const { kpi } = summary;
  return (
    <div className="grid grid-cols-2 gap-2">
      <MiniStat label="Presenze stimate" value={kpi.presenze_stimate} />
      <MiniStat label="Assenze (gg)" value={kpi.assenze_giorni} />
      <MiniStat label="Ferie (gg)" value={kpi.ferie_giorni} />
      <MiniStat label="Permessi (h)" value={kpi.permessi_ore} />
      <MiniStat label="Malattie (gg)" value={kpi.malattie_giorni} />
    </div>
  );
}

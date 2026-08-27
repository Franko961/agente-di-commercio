import { MiniStat } from "./AssenzeTab";

export default function PermessiTab({ summary }) {
  if (!summary) return null;
  return (
    <div className="grid grid-cols-2 gap-2">
      <MiniStat label="Ore richieste" value={summary.permessi.ore_richieste} />
      <MiniStat label="Ore approvate" value={summary.permessi.ore_approvate} />
    </div>
  );
}

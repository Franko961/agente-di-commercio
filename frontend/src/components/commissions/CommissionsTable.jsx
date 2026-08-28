import { Coins, Trash2, Pencil, ChevronDown } from "lucide-react";
import { fmt } from "./constants";

// Tabella provvigioni, raggruppata per periodo — stesso principio del
// raggruppamento mensile in Spese.jsx: il periodo corrente resta aperto, i
// periodi passati partono chiusi mostrando solo il totale.
export default function CommissionsTable({
  periodGroups, expandedPeriods, togglePeriod, clients, mandanti,
  onToggleStatus, onDelete, onEditManual, onRemoveManual,
}) {
  return (
    <div className="space-y-3">
      {periodGroups.map((group) => {
        const isExpanded = expandedPeriods.has(group.key);
        return (
          <div key={group.key} className="bg-white border border-[#E4E4E1] rounded-md overflow-hidden">
            <button
              onClick={() => togglePeriod(group.key)}
              data-testid={`commission-period-${group.key}`}
              className="w-full flex items-center justify-between gap-3 px-4 py-3 bg-[#F3F3F1] hover:bg-[#EDEDEA] transition-colors text-left"
            >
              <span className="flex items-center gap-2 font-cabinet font-bold text-[14px]">
                <ChevronDown className={`w-4 h-4 text-[#6B6B72] shrink-0 transition-transform ${isExpanded ? "rotate-180" : ""}`} />
                {group.label}
              </span>
              <span className="font-mono text-[11px] uppercase tracking-widest text-[#52525B]">
                Totale: <span className="font-cabinet font-black text-[14px] text-[#0A0A0A]">{fmt(group.total)}</span>
              </span>
            </button>
            {isExpanded && (
              <div>
                <div className="hidden md:grid grid-cols-7 gap-2 px-4 py-3 border-b border-[#E4E4E1] font-mono text-[10px] uppercase tracking-widest text-[#52525B]">
                  <div>Periodo</div><div className="col-span-2">Cliente</div><div>Mandante</div><div>Aliquota</div><div className="text-right">Importo</div><div></div>
                </div>
                {group.items.map((c) => (
                  <CommissionRow key={c.id} c={c} clients={clients} mandanti={mandanti} onToggleStatus={onToggleStatus} onDelete={onDelete} />
                ))}
                {group.manualEntries.map((entry) => {
                  const manualClientName = clients.find((cl) => cl.id === entry.client_id)?.company_name;
                  const manualMandanteName = mandanti.find((m) => m.id === entry.mandante_id)?.name;
                  return (
                  <div key={entry.id} className="grid grid-cols-2 md:grid-cols-7 gap-2 px-4 py-3 border-b border-[#E4E4E1] items-center text-[13px] bg-[#FFF9F5]">
                    <div className="font-mono">{entry.period}</div>
                    <div className="col-span-2 font-medium text-[#52525B] flex flex-col gap-0.5">
                      <span className="flex items-center gap-1.5">
                        <Coins className="w-3.5 h-3.5 text-[#B23E00]" /> Inserita manualmente
                      </span>
                      {(manualClientName || entry.descrizione) && (
                        <span className="text-[11px] text-[#6B6B72] pl-5">
                          {[manualClientName, entry.descrizione].filter(Boolean).join(" · ")}
                        </span>
                      )}
                    </div>
                    <div className="text-[#6B6B72]">{manualMandanteName || "—"}</div>
                    <div className="font-mono text-[#6B6B72] capitalize">{entry.tipo || "ordinaria"}</div>
                    <div className="text-right">
                      <div className="font-cabinet font-bold">{fmt(entry.amount)}</div>
                      <div className="font-mono text-[10px] uppercase tracking-widest mt-1"
                        style={{ color: entry.stato === "incassato" ? "#059669" : "#B23E00" }}>
                        {entry.stato || "maturato"}
                      </div>
                    </div>
                    <div className="flex justify-end gap-1">
                      <button onClick={() => onEditManual(entry)}
                        className="p-1.5 text-[#6B6B72] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded transition-colors"
                        title="Modifica" aria-label="Modifica provvigione manuale">
                        <Pencil className="w-4 h-4" />
                      </button>
                      <button onClick={() => onRemoveManual(entry.id, entry.period)}
                        className="p-1.5 text-[#6B6B72] hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                        title="Rimuovi provvigione manuale" aria-label="Rimuovi provvigione manuale">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
      {periodGroups.length === 0 && (
        <div className="bg-white border border-[#E4E4E1] rounded-md p-8 text-center text-[#6B6B72] text-[13px]">Nessuna provvigione.</div>
      )}
    </div>
  );
}

function CommissionRow({ c, clients, mandanti, onToggleStatus, onDelete }) {
  const cli = clients.find((x) => x.id === c.client_id);
  const m = mandanti.find((x) => x.id === c.mandante_id);
  return (
    <div data-testid={`commission-${c.id}`} className="grid grid-cols-2 md:grid-cols-7 gap-2 px-4 py-3 border-b border-[#E4E4E1] items-center text-[13px]">
      <div className="font-mono">{c.period}</div>
      <div className="col-span-2 font-medium">{cli?.company_name || "—"}</div>
      <div className="text-[#52525B]">{m?.name || "—"}</div>
      <div className="font-mono">
        {c.rate}%
        {c.sale_type && <span className="text-[#6B6B72] ml-1">({c.sale_type})</span>}
      </div>
      <div className="text-right">
        <div className="font-cabinet font-bold">{fmt(c.amount)}</div>
        <button onClick={() => onToggleStatus(c.id, c.status === "maturato" ? "incassato" : "maturato")}
          className="font-mono text-[10px] uppercase tracking-widest mt-1"
          style={{ color: c.status === "incassato" ? "#059669" : "#B23E00" }}>
          {c.status} ↻
        </button>
      </div>
      <div className="flex justify-end">
        <button onClick={() => onDelete(c.id)}
          className="p-1.5 text-[#6B6B72] hover:text-red-500 hover:bg-red-50 rounded transition-colors"
          title="Elimina provvigione" aria-label="Elimina provvigione">
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

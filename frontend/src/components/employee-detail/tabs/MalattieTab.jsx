import { REQUEST_STATUS_LABELS, REQUEST_STATUS_COLORS } from "../constants";
import { MiniStat } from "./AssenzeTab";

export default function MalattieTab({ summary, onSetCertificate }) {
  if (!summary) return null;
  return (
    <div>
      <div className="mb-4"><MiniStat label="Giorni malattia (anno)" value={summary.malattie.giorni} /></div>
      <div className="text-[11px] text-[#6B6B72] mb-3">Nessun dato sanitario: solo date, giorni e conferma di ricezione del certificato.</div>
      <div className="space-y-2">
        {summary.malattie.richieste.map((r) => (
          <div key={r.id} className="bg-white border border-[#E4E4E1] rounded-md p-3 flex items-center justify-between gap-2 flex-wrap text-[13px]">
            <div>
              <div>{r.date_from} → {r.date_to} <span className="text-[#6B6B72]">({r.giorni} gg)</span></div>
              <span className="font-mono text-[10px] uppercase tracking-widest" style={{ color: REQUEST_STATUS_COLORS[r.status] }}>
                {REQUEST_STATUS_LABELS[r.status]}
              </span>
            </div>
            <button onClick={() => onSetCertificate(r.id, !r.certificate_received)}
              className={`px-2.5 py-1.5 rounded-md text-[12px] font-medium border ${
                r.certificate_received ? "bg-[#059669] text-white border-[#059669]" : "border-[#E4E4E1] text-[#52525B]"
              }`}>
              Certificato: {r.certificate_received ? "Sì" : "No"}
            </button>
          </div>
        ))}
        {summary.malattie.richieste.length === 0 && (
          <div className="bg-white border border-[#E4E4E1] rounded-md p-6 text-center text-[#6B6B72] text-[13px]">Nessuna richiesta di malattia quest'anno.</div>
        )}
      </div>
    </div>
  );
}

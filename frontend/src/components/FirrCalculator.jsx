import { useState } from "react";
import { Calculator } from "lucide-react";
import { formatEuro, parseItalianNumber } from "@/utils/fiscalCalc";

// Calcolatore client-side, nessuna chiamata al backend: applica gli
// scaglioni FIRR 2026 (AEC Commercio siglato il 4/6/2025, in vigore dal
// 1/1/2026 — verificati incrociando 3 fonti indipendenti, vedi articolo)
// alle provvigioni annue inserite. Con un mandato attivo per meno di 12
// mesi nell'anno, gli scaglioni si riducono in proporzione ai mesi di
// attività (stessa logica riportata dalle fonti consultate).
const SCAGLIONI = {
  plurimandatario: [12000, 18000],
  monomandatario: [24000, 36000],
};

function computeFirr(provvigioni, tipoMandato, mesi) {
  const p = Math.max(0, provvigioni || 0);
  // mesi=0 è un valore legittimo (mandato senza mesi di attività), non
  // "mancante": va vincolato al minimo di 1, non sostituito con 12 —
  // Number.isFinite distingue "0 digitato davvero" da "campo vuoto/non
  // numerico" (NaN), che invece ricade sul default di un anno intero.
  const mesiValid = Number.isFinite(mesi) ? mesi : 12;
  const factor = Math.min(12, Math.max(1, mesiValid)) / 12;
  const [soglia1Full, soglia2Full] = SCAGLIONI[tipoMandato];
  const soglia1 = soglia1Full * factor;
  const soglia2 = soglia2Full * factor;

  let firr;
  if (p <= soglia1) {
    firr = p * 0.04;
  } else if (p <= soglia2) {
    firr = soglia1 * 0.04 + (p - soglia1) * 0.02;
  } else {
    firr = soglia1 * 0.04 + (soglia2 - soglia1) * 0.02 + (p - soglia2) * 0.01;
  }
  return { firr, soglia1, soglia2 };
}

export default function FirrCalculator() {
  const [provvigioni, setProvvigioni] = useState("15000");
  const [tipoMandato, setTipoMandato] = useState("plurimandatario");
  const [mesi, setMesi] = useState("12");

  const provvigioniNum = parseItalianNumber(provvigioni);
  // parseInt("0", 10) è 0 (un mesi valido, non mancante): il fallback a 12
  // deve scattare solo su un campo vuoto/non numerico (NaN), non su uno
  // zero digitato davvero — vedi il commento su mesiValid in computeFirr.
  const mesiParsed = parseInt(mesi, 10);
  const mesiNum = Number.isNaN(mesiParsed) ? 12 : mesiParsed;
  const { firr, soglia1, soglia2 } = computeFirr(provvigioniNum, tipoMandato, mesiNum);

  return (
    <div className="my-8 bg-white border border-[#E4E4E1] rounded-xl p-6">
      <div className="flex items-center gap-2 mb-5">
        <Calculator className="w-4 h-4 text-[#B23E00]" />
        <div className="font-cabinet font-black text-[15px]">
          Calcolatore FIRR (accantonamento annuo)
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-[12px] font-medium text-[#52525B] mb-1">
            Provvigioni percepite nell'anno da questo mandante (€)
          </label>
          <input
            type="text"
            inputMode="decimal"
            value={provvigioni}
            onChange={(e) => setProvvigioni(e.target.value)}
            className="w-full border border-[#E4E4E1] rounded-md px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className="block text-[12px] font-medium text-[#52525B] mb-1">
            Tipo di mandato con questo mandante
          </label>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setTipoMandato("plurimandatario")}
              className={`flex-1 border rounded-md px-3 py-2 text-[13px] font-medium transition-colors ${
                tipoMandato === "plurimandatario"
                  ? "border-[#0A192F] bg-[#0A192F] text-white"
                  : "border-[#E4E4E1] text-[#52525B]"
              }`}
            >
              Plurimandatario (senza esclusiva)
            </button>
            <button
              type="button"
              onClick={() => setTipoMandato("monomandatario")}
              className={`flex-1 border rounded-md px-3 py-2 text-[13px] font-medium transition-colors ${
                tipoMandato === "monomandatario"
                  ? "border-[#0A192F] bg-[#0A192F] text-white"
                  : "border-[#E4E4E1] text-[#52525B]"
              }`}
            >
              Monomandatario (con esclusiva)
            </button>
          </div>
        </div>

        <div>
          <label className="block text-[12px] font-medium text-[#52525B] mb-1">
            Mesi di mandato attivo nell'anno
          </label>
          <input
            type="number" min="1" max="12" step="1"
            value={mesi}
            onChange={(e) => setMesi(e.target.value)}
            className="w-full border border-[#E4E4E1] rounded-md px-3 py-2 text-sm"
          />
          <p className="text-[11px] text-[#6B6B72] mt-1.5">
            12 se il mandato è durato l'intero anno solare — meno se iniziato o cessato a metà anno.
          </p>
        </div>
      </div>

      <div className="mt-5 pt-5 border-t border-[#E4E4E1] space-y-2.5">
        <div className="flex items-center justify-between text-[13px]">
          <span className="text-[#52525B]">Scaglioni applicati (proporzionati ai mesi)</span>
          <span className="font-mono font-medium text-[12px]">
            4% fino a {formatEuro(soglia1)} · 2% fino a {formatEuro(soglia2)} · 1% oltre
          </span>
        </div>
        <div className="flex items-center justify-between text-[15px] pt-2.5 border-t border-[#E4E4E1]">
          <span className="font-cabinet font-bold">FIRR accantonato per l'anno</span>
          <span className="font-mono font-black text-[#059669]">{formatEuro(firr)}</span>
        </div>
      </div>

      <p className="text-[11px] text-[#6B6B72] mt-4">
        Calcolo indicativo su un singolo anno e un singolo mandante, con gli scaglioni 2026: se hai
        anni di mandato precedenti al 2026, quella quota resta calcolata con i vecchi scaglioni
        (fino a €6.200/€9.300 plurimandatario, €12.400/€18.600 monomandatario) — non sommarla
        direttamente a questo risultato. Non sostituisce il conteggio ufficiale Fondazione ENASARCO.
      </p>
    </div>
  );
}

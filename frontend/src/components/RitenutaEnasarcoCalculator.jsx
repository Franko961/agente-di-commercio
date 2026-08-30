import { useState } from "react";
import { Calculator } from "lucide-react";
import { computeFiscalBreakdown, formatEuro } from "@/utils/fiscalCalc";

// Calcolatore client-side, nessuna chiamata al backend: un numero inserito
// a mano dal lettore, non dati reali dell'agente (per quelli vedi il
// riepilogo fiscale nella pagina Provvigioni dell'app). La formula vive in
// utils/fiscalCalc.js, condivisa con quel riepilogo — vedi il commento
// lì per aliquote e riferimenti normativi.

export default function RitenutaEnasarcoCalculator() {
  const [importo, setImporto] = useState("1000");
  const [regime, setRegime] = useState("forfettario");
  const [baseRitenuta, setBaseRitenuta] = useState("50");

  const lordoInput = parseFloat(importo.replace(",", ".")) || 0;
  const { lordo, ritenutaAcconto: ritenuta, contributoEnasarco: enasarco, netto } =
    computeFiscalBreakdown(lordoInput, regime, baseRitenuta);

  return (
    <div className="my-8 bg-white border border-[#E4E4E1] rounded-xl p-6">
      <div className="flex items-center gap-2 mb-5">
        <Calculator className="w-4 h-4 text-[#B23E00]" />
        <div className="font-cabinet font-black text-[15px]">
          Calcolatore ritenuta d'acconto e ENASARCO
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-[12px] font-medium text-[#52525B] mb-1">
            Provvigione lorda in fattura (€)
          </label>
          <input
            type="text"
            inputMode="decimal"
            value={importo}
            onChange={(e) => setImporto(e.target.value)}
            className="w-full border border-[#E4E4E1] rounded-md px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className="block text-[12px] font-medium text-[#52525B] mb-1">
            Regime fiscale
          </label>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setRegime("forfettario")}
              className={`flex-1 border rounded-md px-3 py-2 text-[13px] font-medium transition-colors ${
                regime === "forfettario"
                  ? "border-[#0A192F] bg-[#0A192F] text-white"
                  : "border-[#E4E4E1] text-[#52525B]"
              }`}
            >
              Forfettario
            </button>
            <button
              type="button"
              onClick={() => setRegime("ordinario")}
              className={`flex-1 border rounded-md px-3 py-2 text-[13px] font-medium transition-colors ${
                regime === "ordinario"
                  ? "border-[#0A192F] bg-[#0A192F] text-white"
                  : "border-[#E4E4E1] text-[#52525B]"
              }`}
            >
              Ordinario
            </button>
          </div>
        </div>

        {regime === "ordinario" && (
          <div>
            <label className="block text-[12px] font-medium text-[#52525B] mb-1">
              Base imponibile ritenuta
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setBaseRitenuta("50")}
                className={`flex-1 border rounded-md px-3 py-2 text-[13px] font-medium transition-colors ${
                  baseRitenuta === "50"
                    ? "border-[#0A192F] bg-[#0A192F] text-white"
                    : "border-[#E4E4E1] text-[#52525B]"
                }`}
              >
                Ordinaria (50%)
              </button>
              <button
                type="button"
                onClick={() => setBaseRitenuta("20")}
                className={`flex-1 border rounded-md px-3 py-2 text-[13px] font-medium transition-colors ${
                  baseRitenuta === "20"
                    ? "border-[#0A192F] bg-[#0A192F] text-white"
                    : "border-[#E4E4E1] text-[#52525B]"
                }`}
              >
                Ridotta (20%)
              </button>
            </div>
            <p className="text-[11px] text-[#6B6B72] mt-1.5">
              La base ridotta richiede una dichiarazione formale al mandante entro il 31 dicembre
              dell'anno precedente — non basta scegliere questa opzione.
            </p>
          </div>
        )}
      </div>

      <div className="mt-5 pt-5 border-t border-[#E4E4E1] space-y-2.5">
        <div className="flex items-center justify-between text-[13px]">
          <span className="text-[#52525B]">Provvigione lorda</span>
          <span className="font-mono font-medium">{formatEuro(lordo)}</span>
        </div>
        <div className="flex items-center justify-between text-[13px]">
          <span className="text-[#52525B]">
            Ritenuta d'acconto {regime === "forfettario" ? "(non dovuta)" : ""}
          </span>
          <span className="font-mono font-medium text-[#DC2626]">− {formatEuro(ritenuta)}</span>
        </div>
        <div className="flex items-center justify-between text-[13px]">
          <span className="text-[#52525B]">Contributo ENASARCO (quota agente, 8,5%)</span>
          <span className="font-mono font-medium text-[#DC2626]">− {formatEuro(enasarco)}</span>
        </div>
        <div className="flex items-center justify-between text-[15px] pt-2.5 border-t border-[#E4E4E1]">
          <span className="font-cabinet font-bold">Netto a saldo</span>
          <span className="font-mono font-black text-[#059669]">{formatEuro(netto)}</span>
        </div>
      </div>

      <p className="text-[11px] text-[#6B6B72] mt-4">
        Calcolo indicativo, non sostituisce il commercialista: non considera eventuali note di
        credito, storni, o il superamento del massimale provvigionale ENASARCO nell'anno (vedi
        l'articolo dedicato a minimali e massimali 2026).
      </p>
    </div>
  );
}

import { useState } from "react";
import { Calculator, AlertTriangle } from "lucide-react";
import {
  computeFiscalBreakdown,
  formatEuro,
  parseItalianNumber,
  ENASARCO_QUOTA_AGENTE,
  ENASARCO_SOGLIE,
} from "@/utils/fiscalCalc";

// Calcolatore client-side, nessuna chiamata al backend: un numero inserito
// a mano dal lettore, non dati reali dell'agente (per quelli vedi il
// riepilogo fiscale nella pagina Provvigioni dell'app, che dal 2026-09-12
// applica la stessa logica di massimale su dati reali — vedi
// computeEnasarcoConMassimale in utils/fiscalCalc.js). La ritenuta
// d'acconto usa ancora computeFiscalBreakdown (nessun massimale non si
// applica alla ritenuta). Il contributo ENASARCO invece è ricalcolato QUI
// con lo stesso schema, non tramite computeFiscalBreakdown: quella
// funzione applica sempre l'8,5% sull'intera provvigione, senza sapere
// quanto già maturato nell'anno — informazione che solo questo
// calcolatore chiede esplicitamente all'utente (il riepilogo reale
// dell'app invece la ricava dai dati già caricati).

export default function RitenutaEnasarcoCalculator() {
  const [importo, setImporto] = useState("1000");
  const [regime, setRegime] = useState("forfettario");
  const [baseRitenuta, setBaseRitenuta] = useState("50");
  const [tipoMandato, setTipoMandato] = useState("plurimandatario");
  const [cumulativoPrima, setCumulativoPrima] = useState("0");

  const lordoInput = parseItalianNumber(importo);
  const cumulativoPrimaNum = Math.max(0, parseItalianNumber(cumulativoPrima));
  const { lordo, ritenutaAcconto: ritenuta } = computeFiscalBreakdown(
    lordoInput,
    regime,
    baseRitenuta
  );

  const { massimale, minimale } = ENASARCO_SOGLIE[tipoMandato];
  // Solo la quota di QUESTA fattura che rientra ancora nel massimale (dato
  // quanto già maturato prima) è soggetta a contributo — non l'intero
  // importo, se il cumulato lo supera durante questa stessa fattura.
  const spazioResiduo = Math.max(0, massimale - cumulativoPrimaNum);
  const imponibileEnasarco = Math.min(lordo, spazioResiduo);
  const enasarco = imponibileEnasarco * ENASARCO_QUOTA_AGENTE;
  const netto = lordo - ritenuta - enasarco;

  const cumulativoDopo = cumulativoPrimaNum + lordo;
  const massimaleGiaSuperato = cumulativoPrimaNum >= massimale;
  const massimaleSuperatoOra = !massimaleGiaSuperato && cumulativoDopo > massimale;
  const sottoMinimale = cumulativoDopo < minimale;

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
              Plurimandatario
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
              Monomandatario
            </button>
          </div>
        </div>

        <div>
          <label className="block text-[12px] font-medium text-[#52525B] mb-1">
            Provvigioni già maturate quest'anno da questo mandante, prima di questa fattura (€)
          </label>
          <input
            type="text"
            inputMode="decimal"
            value={cumulativoPrima}
            onChange={(e) => setCumulativoPrima(e.target.value)}
            className="w-full border border-[#E4E4E1] rounded-md px-3 py-2 text-sm"
          />
          <p className="text-[11px] text-[#6B6B72] mt-1.5">
            0 se questa è la prima fattura dell'anno a questo mandante — serve a sapere quanto
            resta del massimale annuo su cui è dovuto il contributo ENASARCO.
          </p>
        </div>
      </div>

      {(massimaleGiaSuperato || massimaleSuperatoOra) && (
        <div className="mt-4 flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-md p-3 text-[12px] text-amber-800">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          {massimaleGiaSuperato ? (
            <span>
              Hai già superato il massimale annuo ({formatEuro(massimale)}) per questo mandante:
              su questa fattura non è dovuto altro contributo ENASARCO.
            </span>
          ) : (
            <span>
              Con questa fattura superi il massimale annuo ({formatEuro(massimale)}) per questo
              mandante: il contributo si applica solo sulla quota fino al tetto (
              {formatEuro(spazioResiduo)}), non sull'intero importo in fattura.
            </span>
          )}
        </div>
      )}
      {sottoMinimale && !massimaleGiaSuperato && !massimaleSuperatoOra && (
        <div className="mt-4 flex items-start gap-2 bg-[#F5F5F4] border border-[#E4E4E1] rounded-md p-3 text-[12px] text-[#52525B]">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>
            Il cumulato per questo mandante resta sotto il minimale contributivo annuo (
            {formatEuro(minimale)}): il mandante verserà comunque almeno il minimo dovuto a
            trimestre, indipendentemente da quanto hai fatturato finora.
          </span>
        </div>
      )}

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
        credito o storni successivi alla fattura.
      </p>
    </div>
  );
}

import { useState } from "react";
import { Calculator } from "lucide-react";
import { formatEuro, parseItalianNumber } from "@/utils/fiscalCalc";
import CalculatorCTA from "@/components/CalculatorCTA";

// Calcolatore client-side, pura aritmetica — nessun dato fiscale da
// verificare esternamente. Il punto centrale (spiegato anche nel testo
// sotto il risultato) è un fatto matematico spesso non intuitivo in
// trattativa: se la provvigione è una percentuale fissa sul fatturato,
// la percentuale di provvigione persa con uno sconto è ESATTAMENTE la
// stessa percentuale dello sconto concesso, indipendentemente
// dall'aliquota di provvigione — perché provvigione e fatturato scalano
// insieme in modo lineare. Non vale più se la provvigione è a scaglioni
// (scala premi): lì un ordine più piccolo per via dello sconto può far
// scendere sotto una soglia e perdere anche il premio aggiuntivo, non
// solo l'importo dello sconto — da qui il rimando all'articolo dedicato.
function computeScontoProvvigione(importoListino, aliquota, sconto) {
  const importo = Math.max(0, importoListino || 0);
  const aliquotaFrac = Math.max(0, aliquota || 0) / 100;
  const scontoFrac = Math.max(0, Math.min(100, sconto || 0)) / 100;

  const provvigionePiena = importo * aliquotaFrac;
  const importoScontato = importo * (1 - scontoFrac);
  const provvigioneScontata = importoScontato * aliquotaFrac;
  const provvigionePersa = provvigionePiena - provvigioneScontata;

  return { provvigionePiena, importoScontato, provvigioneScontata, provvigionePersa };
}

// Sconto massimo (%) concedibile per non scendere sotto una provvigione
// minima target — deriva direttamente dalla stessa linearità: essendo
// provvigioneScontata/provvigionePiena = 1 - sconto%, lo sconto massimo è
// semplicemente 1 meno il rapporto tra provvigione minima e provvigione
// piena.
function computeScontoMassimo(provvigionePiena, provvigioneMinima) {
  if (provvigionePiena <= 0) return 0;
  const rapporto = Math.max(0, provvigioneMinima || 0) / provvigionePiena;
  return Math.max(0, Math.min(100, (1 - rapporto) * 100));
}

export default function ScontoProvvigioneCalculator() {
  const [importoListino, setImportoListino] = useState("5000");
  const [aliquota, setAliquota] = useState("10");
  const [sconto, setSconto] = useState("10");
  const [provvigioneMinima, setProvvigioneMinima] = useState("400");

  const importoNum = parseItalianNumber(importoListino);
  const aliquotaNum = parseItalianNumber(aliquota);
  const scontoNum = parseItalianNumber(sconto);
  const provvigioneMinimaNum = parseItalianNumber(provvigioneMinima);

  const { provvigionePiena, importoScontato, provvigioneScontata, provvigionePersa } =
    computeScontoProvvigione(importoNum, aliquotaNum, scontoNum);
  const scontoMassimo = computeScontoMassimo(provvigionePiena, provvigioneMinimaNum);

  return (
    <div className="my-8 bg-white border border-[#E4E4E1] rounded-xl p-6">
      <div className="flex items-center gap-2 mb-5">
        <Calculator className="w-4 h-4 text-[#B23E00]" />
        <div className="font-cabinet font-black text-[15px]">
          Calcolatore sconto e provvigione
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-[12px] font-medium text-[#52525B] mb-1">
            Importo ordine a listino (€)
          </label>
          <input
            type="text"
            inputMode="decimal"
            value={importoListino}
            onChange={(e) => setImportoListino(e.target.value)}
            className="w-full border border-[#E4E4E1] rounded-md px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className="block text-[12px] font-medium text-[#52525B] mb-1">
            Aliquota di provvigione (%)
          </label>
          <input
            type="text"
            inputMode="decimal"
            value={aliquota}
            onChange={(e) => setAliquota(e.target.value)}
            className="w-full border border-[#E4E4E1] rounded-md px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className="block text-[12px] font-medium text-[#52525B] mb-1">
            Sconto che vuoi valutare (%)
          </label>
          <input
            type="text"
            inputMode="decimal"
            value={sconto}
            onChange={(e) => setSconto(e.target.value)}
            className="w-full border border-[#E4E4E1] rounded-md px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className="block text-[12px] font-medium text-[#52525B] mb-1">
            Provvigione minima che vuoi garantirti su questo ordine (€, facoltativo)
          </label>
          <input
            type="text"
            inputMode="decimal"
            value={provvigioneMinima}
            onChange={(e) => setProvvigioneMinima(e.target.value)}
            className="w-full border border-[#E4E4E1] rounded-md px-3 py-2 text-sm"
          />
        </div>
      </div>

      <div className="mt-5 pt-5 border-t border-[#E4E4E1] space-y-2.5">
        <div className="flex items-center justify-between text-[13px]">
          <span className="text-[#52525B]">Provvigione piena (senza sconto)</span>
          <span className="font-mono font-medium">{formatEuro(provvigionePiena)}</span>
        </div>
        <div className="flex items-center justify-between text-[13px]">
          <span className="text-[#52525B]">Importo ordine con lo sconto</span>
          <span className="font-mono font-medium">{formatEuro(importoScontato)}</span>
        </div>
        <div className="flex items-center justify-between text-[13px]">
          <span className="text-[#52525B]">Provvigione persa con lo sconto</span>
          <span className="font-mono font-medium text-[#DC2626]">
            − {formatEuro(provvigionePersa)}
          </span>
        </div>
        <div className="flex items-center justify-between text-[15px] pt-2.5 border-t border-[#E4E4E1]">
          <span className="font-cabinet font-bold">Provvigione con lo sconto applicato</span>
          <span className="font-mono font-black text-[#059669]">
            {formatEuro(provvigioneScontata)}
          </span>
        </div>
        {provvigioneMinimaNum > 0 && (
          <div className="flex items-center justify-between text-[13px] pt-2.5 border-t border-[#E4E4E1]">
            <span className="text-[#52525B]">
              Sconto massimo per non scendere sotto {formatEuro(provvigioneMinimaNum)} di
              provvigione
            </span>
            <span className="font-mono font-bold">{scontoMassimo.toFixed(1)}%</span>
          </div>
        )}
      </div>

      <CalculatorCTA location="sconto_provvigione_calculator" />

      <p className="text-[11px] text-[#6B6B72] mt-4">
        Se la provvigione è una percentuale fissa sul fatturato, la percentuale che perdi è sempre
        identica alla percentuale di sconto concesso, qualunque sia l'aliquota. Non vale più se la
        provvigione è a scaglioni (scala premi): un ordine più piccolo per via dello sconto può
        farti scendere sotto una soglia e perdere anche il premio aggiuntivo, non solo l'importo
        dello sconto — vedi l'articolo dedicato alle provvigioni scalari.
      </p>
    </div>
  );
}

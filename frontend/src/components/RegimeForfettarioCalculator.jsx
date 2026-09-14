import { useState } from "react";
import { Calculator, AlertTriangle } from "lucide-react";
import { formatEuro, parseItalianNumber } from "@/utils/fiscalCalc";
import CalculatorCTA from "@/components/CalculatorCTA";

// Calcolatore client-side, nessuna chiamata al backend. Dati verificati
// via ricerca (settembre 2026, incrociando più fonti fiscali indipendenti):
// - coefficiente di redditività 62% per intermediari di commercio (ATECO
//   46.1x, agenti e rappresentanti di commercio)
// - soglia ricavi 85.000€ per restare nel regime; tra 85.000€ e 100.000€
//   si resta nel forfettario per l'anno in corso ma si esce dal successivo;
//   oltre 100.000€ l'uscita è immediata nello stesso anno, con IVA dovuta
//   dall'operazione che ha causato il superamento
// - aliquota ordinaria 15%, ridotta al 5% per i primi 5 anni di una nuova
//   attività che rispetta requisiti specifici (nessuna attività simile nei
//   5 anni precedenti, tra gli altri) — NON verificati da questo
//   calcolatore, solo un'ipotesi che l'utente sceglie di simulare
const COEFFICIENTE_REDDITIVITA = 0.62;
const SOGLIA_RICAVI = 85000;
const SOGLIA_USCITA_IMMEDIATA = 100000;

function computeForfettario(ricavi, contributiPrevidenziali, aliquotaRidotta) {
  const r = Math.max(0, ricavi || 0);
  const contributi = Math.max(0, contributiPrevidenziali || 0);
  const redditoLordo = r * COEFFICIENTE_REDDITIVITA;
  const redditoNetto = Math.max(0, redditoLordo - contributi);
  const aliquota = aliquotaRidotta ? 0.05 : 0.15;
  const imposta = redditoNetto * aliquota;
  return { redditoLordo, redditoNetto, imposta, aliquota };
}

export default function RegimeForfettarioCalculator() {
  const [ricavi, setRicavi] = useState("40000");
  const [contributi, setContributi] = useState("0");
  const [aliquotaRidotta, setAliquotaRidotta] = useState(false);

  const ricaviNum = parseItalianNumber(ricavi);
  const contributiNum = parseItalianNumber(contributi);
  const { redditoLordo, redditoNetto, imposta, aliquota } = computeForfettario(
    ricaviNum,
    contributiNum,
    aliquotaRidotta
  );

  const superaSogliaUscitaImmediata = ricaviNum > SOGLIA_USCITA_IMMEDIATA;
  const superaSoglia = !superaSogliaUscitaImmediata && ricaviNum > SOGLIA_RICAVI;

  return (
    <div className="my-8 bg-white border border-[#E4E4E1] rounded-xl p-6">
      <div className="flex items-center gap-2 mb-5">
        <Calculator className="w-4 h-4 text-[#B23E00]" />
        <div className="font-cabinet font-black text-[15px]">
          Calcolatore regime forfettario
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-[12px] font-medium text-[#52525B] mb-1">
            Ricavi (provvigioni lorde) nell'anno (€)
          </label>
          <input
            type="text"
            inputMode="decimal"
            value={ricavi}
            onChange={(e) => setRicavi(e.target.value)}
            className="w-full border border-[#E4E4E1] rounded-md px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className="block text-[12px] font-medium text-[#52525B] mb-1">
            Contributi previdenziali versati nell'anno (€, facoltativo)
          </label>
          <input
            type="text"
            inputMode="decimal"
            value={contributi}
            onChange={(e) => setContributi(e.target.value)}
            className="w-full border border-[#E4E4E1] rounded-md px-3 py-2 text-sm"
          />
          <p className="text-[11px] text-[#6B6B72] mt-1.5">
            Riducono il reddito imponibile su cui si calcola l'imposta — es. contributo ENASARCO a
            proprio carico.
          </p>
        </div>

        <label className="flex items-start gap-2 text-[13px] text-[#3F3F46]">
          <input
            type="checkbox"
            checked={aliquotaRidotta}
            onChange={(e) => setAliquotaRidotta(e.target.checked)}
            className="mt-0.5"
          />
          <span>
            Nuova attività: simula l'aliquota ridotta al 5% (primi 5 anni, solo se rispetti i
            requisiti — vedi nota sotto)
          </span>
        </label>
      </div>

      {(superaSoglia || superaSogliaUscitaImmediata) && (
        <div className="mt-4 flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-md p-3 text-[12px] text-amber-800">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          {superaSogliaUscitaImmediata ? (
            <span>
              Oltre {formatEuro(SOGLIA_USCITA_IMMEDIATA)} l'uscita dal regime forfettario è
              immediata, nello stesso anno, con IVA dovuta dall'operazione che ha causato il
              superamento — il calcolo sotto non si applica più oltre questo punto.
            </span>
          ) : (
            <span>
              Tra {formatEuro(SOGLIA_RICAVI)} e {formatEuro(SOGLIA_USCITA_IMMEDIATA)} resti nel
              forfettario per l'anno in corso, ma perdi il diritto ad accedervi dall'anno
              successivo.
            </span>
          )}
        </div>
      )}

      <div className="mt-5 pt-5 border-t border-[#E4E4E1] space-y-2.5">
        <div className="flex items-center justify-between text-[13px]">
          <span className="text-[#52525B]">Reddito imponibile lordo (62% dei ricavi)</span>
          <span className="font-mono font-medium text-[13px]">{formatEuro(redditoLordo)}</span>
        </div>
        <div className="flex items-center justify-between text-[13px]">
          <span className="text-[#52525B]">Reddito imponibile netto (dopo i contributi)</span>
          <span className="font-mono font-medium text-[13px]">{formatEuro(redditoNetto)}</span>
        </div>
        <div className="flex items-center justify-between text-[15px] pt-2.5 border-t border-[#E4E4E1]">
          <span className="font-cabinet font-bold">
            Imposta sostitutiva ({(aliquota * 100).toFixed(0)}%)
          </span>
          <span className="font-mono font-black text-[#059669]">{formatEuro(imposta)}</span>
        </div>
      </div>

      <CalculatorCTA location="regime_forfettario_calculator" />

      <p className="text-[11px] text-[#6B6B72] mt-4">
        Coefficiente di redditività 62%, valido per gli intermediari di commercio (ATECO 46.1x —
        agenti e rappresentanti). L'aliquota ridotta al 5% richiede requisiti specifici (es.
        nessuna attività simile nei 5 anni precedenti) non verificati da questo calcolatore: se non
        li rispetti, si applica il 15%. Non considera eventuali altri redditi né l'accesso al
        regime stesso (es. limite di 35.000€ da lavoro dipendente nell'anno precedente). Calcolo
        indicativo, non sostituisce una consulenza con il proprio commercialista.
      </p>
    </div>
  );
}

import { useEffect, useState } from "react";
import { Loader2, RotateCcw } from "lucide-react";
import { toast } from "sonner";
import { getFiscalSettings, updateFiscalSettings } from "../../api/settings";

export default function FiscaleTab() {
  const [settings, setSettings] = useState(null); // null = caricamento
  const [busy, setBusy] = useState(false);
  // Distinto da "settings === null": senza questo, un caricamento fallito
  // (rete, 401 momentaneo) restava indistinguibile da "ancora in corso" —
  // lo spinner girava per sempre, senza un modo per riprovare.
  const [loadError, setLoadError] = useState(false);

  const load = async () => {
    setLoadError(false);
    try {
      setSettings(await getFiscalSettings());
    } catch {
      setLoadError(true);
      toast.error("Impossibile caricare la situazione fiscale");
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const save = async (next) => {
    setBusy(true);
    try {
      setSettings(await updateFiscalSettings(next));
      toast.success("Situazione fiscale aggiornata");
    } catch {
      toast.error("Errore nel salvataggio");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="mb-8">
        <div className="font-mono text-[11px] uppercase tracking-widest text-[#B23E00] mb-1">Impostazioni</div>
        <h1 className="font-cabinet text-3xl font-black">Situazione fiscale</h1>
        <p className="text-[#52525B] mt-1">
          Usata per calcolare ritenuta d'acconto e contributo ENASARCO nel riepilogo delle
          tue provvigioni (Provvigioni → Netto stimato). Non genera né modifica fatture: è
          solo un calcolo indicativo, non sostituisce il commercialista.
        </p>
      </div>

      {settings === null && loadError ? (
        <div className="flex items-center gap-3 text-[13px] text-[#6B6B72]">
          <span>Impossibile caricare la situazione fiscale.</span>
          <button
            type="button"
            onClick={load}
            className="flex items-center gap-1.5 text-[#B23E00] font-medium hover:underline"
          >
            <RotateCcw className="w-3.5 h-3.5" /> Riprova
          </button>
        </div>
      ) : settings === null ? (
        <div className="flex items-center gap-2 text-[13px] text-[#6B6B72]">
          <Loader2 className="w-4 h-4 animate-spin" /> Caricamento…
        </div>
      ) : (
        <div className="space-y-8">
          <div>
            <h2 className="font-cabinet text-xl font-black mb-3">Regime fiscale</h2>
            <div className="border border-[#E4E4E1] rounded-lg p-5 space-y-3">
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="radio" name="regime_fiscale" className="mt-1" disabled={busy}
                  checked={settings.regime_fiscale === "ordinario"}
                  onChange={() => save({ ...settings, regime_fiscale: "ordinario" })}
                />
                <span>
                  <span className="block text-[13px] font-semibold">Ordinario</span>
                  <span className="block text-[12px] text-[#6B6B72]">
                    Ritenuta d'acconto dovuta sulle provvigioni (art. 25-bis DPR 600/1973).
                  </span>
                </span>
              </label>
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="radio" name="regime_fiscale" className="mt-1" disabled={busy}
                  checked={settings.regime_fiscale === "forfettario"}
                  onChange={() => save({ ...settings, regime_fiscale: "forfettario" })}
                />
                <span>
                  <span className="block text-[13px] font-semibold">Forfettario</span>
                  <span className="block text-[12px] text-[#6B6B72]">
                    Esente da ritenuta d'acconto (L. 190/2014, c. 67) — a condizione che la
                    fattura riporti la dicitura corretta e sia comunicato al mandante.
                  </span>
                </span>
              </label>
            </div>
          </div>

          {settings.regime_fiscale === "ordinario" && (
            <div>
              <h2 className="font-cabinet text-xl font-black mb-3">Base imponibile ritenuta</h2>
              <div className="border border-[#E4E4E1] rounded-lg p-5 space-y-3">
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="radio" name="base_ritenuta" className="mt-1" disabled={busy}
                    checked={settings.base_ritenuta === "50"}
                    onChange={() => save({ ...settings, base_ritenuta: "50" })}
                  />
                  <span>
                    <span className="block text-[13px] font-semibold">Ordinaria (50%) — 11,5% effettivo</span>
                    <span className="block text-[12px] text-[#6B6B72]">Il caso standard, valido per default.</span>
                  </span>
                </label>
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="radio" name="base_ritenuta" className="mt-1" disabled={busy}
                    checked={settings.base_ritenuta === "20"}
                    onChange={() => save({ ...settings, base_ritenuta: "20" })}
                  />
                  <span>
                    <span className="block text-[13px] font-semibold">Ridotta (20%) — 4,6% effettivo</span>
                    <span className="block text-[12px] text-[#6B6B72]">
                      Solo se hai comunicato formalmente al mandante, entro il 31 dicembre
                      dell'anno precedente, di avvalerti in via continuativa di dipendenti o
                      collaboratori.
                    </span>
                  </span>
                </label>
              </div>
            </div>
          )}
        </div>
      )}
    </>
  );
}

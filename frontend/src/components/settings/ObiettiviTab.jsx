import { useEffect, useState } from "react";
import { Loader2, Save, Image } from "lucide-react";
import { toast } from "sonner";
import { getGoals, updateGoals, getLeaveSettings, updateLeaveSettings, getCompanySettings, updateCompanySettings } from "../../api/settings";
import { useAuth } from "../../contexts/AuthContext";
import { resizeImageToDataUrl } from "../../utils/image";

export default function ObiettiviTab() {
  const { user } = useAuth();
  const personaleEnabled = (user?.enabled_extra_modules || []).includes("personale");

  const [goals, setGoals] = useState(null); // null = caricamento
  const [goalsBusy, setGoalsBusy] = useState(false);

  const [leaveSettings, setLeaveSettings] = useState(null); // null = caricamento
  const [leaveSettingsBusy, setLeaveSettingsBusy] = useState(false);

  const [companyLogo, setCompanyLogo] = useState(null); // null = caricamento, "" = nessun logo impostato
  const [companyLogoBusy, setCompanyLogoBusy] = useState(false);
  const [vatNumber, setVatNumber] = useState(null); // null = caricamento, "" = non impostata
  const [vatNumberBusy, setVatNumberBusy] = useState(false);

  const loadGoals = async () => {
    try {
      setGoals(await getGoals());
    } catch {
      toast.error("Impossibile caricare gli obiettivi");
    }
  };

  const saveGoals = async (e) => {
    e.preventDefault();
    setGoalsBusy(true);
    try {
      const payload = {
        goal_revenue: goals.goal_revenue === "" ? null : Number(goals.goal_revenue),
        goal_commissions: goals.goal_commissions === "" ? null : Number(goals.goal_commissions),
        goal_new_clients: goals.goal_new_clients === "" ? null : Number(goals.goal_new_clients),
        goal_visits: goals.goal_visits === "" ? null : Number(goals.goal_visits),
      };
      setGoals(await updateGoals(payload));
      toast.success("Obiettivi aggiornati");
    } catch {
      toast.error("Errore nel salvataggio degli obiettivi");
    } finally {
      setGoalsBusy(false);
    }
  };

  const loadLeaveSettings = async () => {
    if (!personaleEnabled) return;
    try {
      setLeaveSettings(await getLeaveSettings());
    } catch {
      toast.error("Impossibile caricare le impostazioni ferie");
    }
  };

  const saveLeaveSettings = async (mode) => {
    setLeaveSettingsBusy(true);
    try {
      setLeaveSettings(await updateLeaveSettings({ ferie_count_mode: mode }));
      toast.success("Preferenza aggiornata");
    } catch {
      toast.error("Errore nel salvataggio");
    } finally {
      setLeaveSettingsBusy(false);
    }
  };

  // Non più condizionato a personaleEnabled come il solo logo (usato
  // finora solo nel cartellino presenze, quindi irrilevante senza il
  // modulo Personale): vat_number serve al report PDF provvigioni per
  // mandante, disponibile a chiunque abbia il modulo "provvigioni" — la
  // maggioranza degli account, non solo chi ha attivato Personale.
  const loadCompanySettings = async () => {
    try {
      const data = await getCompanySettings();
      setCompanyLogo(data.logo || "");
      setVatNumber(data.vat_number || "");
    } catch {
      toast.error("Impossibile caricare i dati aziendali");
    }
  };

  // Ridimensionato lato client con lo stesso helper già usato per la foto
  // dipendente (vedi utils/image.js e EmployeeDetailSheet.jsx) — mostrato
  // in testa al cartellino presenze esportato, vedi
  // services/attendance_xlsx_export.py.
  //
  // Un solo PUT /settings/company aggiorna entrambi i campi (logo e
  // vat_number) insieme — CompanySettingsIn non distingue "campo assente"
  // da "campo esplicitamente azzerato" (Optional[None]), quindi ogni save
  // deve sempre includere il valore CORRENTE dell'altro campo, altrimenti
  // lo azzererebbe per errore (es. cambiare il logo cancellerebbe la
  // Partita IVA già salvata).
  const saveCompanyLogo = async (file) => {
    setCompanyLogoBusy(true);
    try {
      const dataUrl = await resizeImageToDataUrl(file, 300);
      const data = await updateCompanySettings({ logo: dataUrl, vat_number: vatNumber || null });
      setCompanyLogo(data.logo || "");
      toast.success("Logo aggiornato");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Errore nel salvataggio del logo");
    } finally {
      setCompanyLogoBusy(false);
    }
  };

  const removeCompanyLogo = async () => {
    setCompanyLogoBusy(true);
    try {
      const data = await updateCompanySettings({ logo: null, vat_number: vatNumber || null });
      setCompanyLogo(data.logo || "");
      toast.success("Logo rimosso");
    } catch {
      toast.error("Errore nella rimozione del logo");
    } finally {
      setCompanyLogoBusy(false);
    }
  };

  const saveVatNumber = async (e) => {
    e.preventDefault();
    setVatNumberBusy(true);
    try {
      const data = await updateCompanySettings({
        logo: companyLogo || null,
        vat_number: vatNumber.trim() || null,
      });
      setVatNumber(data.vat_number || "");
      toast.success("Partita IVA aggiornata");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Errore nel salvataggio della Partita IVA");
    } finally {
      setVatNumberBusy(false);
    }
  };

  useEffect(() => {
    loadGoals();
    loadLeaveSettings();
    loadCompanySettings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <>
      <div className="mb-8">
        <div className="font-mono text-[11px] uppercase tracking-widest text-[#B23E00] mb-1">Impostazioni</div>
        <h1 className="font-cabinet text-3xl font-black">Obiettivi</h1>
        <p className="text-[#52525B] mt-1">
          Imposta i tuoi obiettivi mensili. Lascia vuoto un campo per non tracciare quella metrica.
        </p>
      </div>

      {goals === null ? (
        <div className="flex items-center gap-2 text-[13px] text-[#6B6B72]">
          <Loader2 className="w-4 h-4 animate-spin" /> Caricamento…
        </div>
      ) : (
        <form onSubmit={saveGoals} className="border border-[#E4E4E1] rounded-lg p-5 space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <div>
              <label className="block text-[12px] font-semibold text-[#52525B] mb-1.5">
                Obiettivo mensile fatturato (€)
              </label>
              <input
                type="number" min="0" step="1"
                value={goals.goal_revenue ?? ""}
                onChange={(e) => setGoals({ ...goals, goal_revenue: e.target.value })}
                className="w-full px-3 py-2 border border-[#E4E4E1] rounded-md text-[14px] focus:outline-none focus:border-[#B23E00]"
                placeholder="es. 10000"
              />
            </div>
            <div>
              <label className="block text-[12px] font-semibold text-[#52525B] mb-1.5">
                Obiettivo provvigioni totali (€)
              </label>
              <input
                type="number" min="0" step="1"
                value={goals.goal_commissions ?? ""}
                onChange={(e) => setGoals({ ...goals, goal_commissions: e.target.value })}
                className="w-full px-3 py-2 border border-[#E4E4E1] rounded-md text-[14px] focus:outline-none focus:border-[#B23E00]"
                placeholder="non impostato"
              />
              <p className="text-[11px] text-[#6B6B72] mt-1">Maturate + incassate, del mese corrente.</p>
            </div>
            <div>
              <label className="block text-[12px] font-semibold text-[#52525B] mb-1.5">
                Obiettivo nuovi clienti
              </label>
              <input
                type="number" min="0" step="1"
                value={goals.goal_new_clients ?? ""}
                onChange={(e) => setGoals({ ...goals, goal_new_clients: e.target.value })}
                className="w-full px-3 py-2 border border-[#E4E4E1] rounded-md text-[14px] focus:outline-none focus:border-[#B23E00]"
                placeholder="non impostato"
              />
            </div>
            <div>
              <label className="block text-[12px] font-semibold text-[#52525B] mb-1.5">
                Obiettivo visite
              </label>
              <input
                type="number" min="0" step="1"
                value={goals.goal_visits ?? ""}
                onChange={(e) => setGoals({ ...goals, goal_visits: e.target.value })}
                className="w-full px-3 py-2 border border-[#E4E4E1] rounded-md text-[14px] focus:outline-none focus:border-[#B23E00]"
                placeholder="non impostato"
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={goalsBusy}
            className="flex items-center gap-1.5 px-4 py-2 bg-[#B23E00] hover:bg-[#E04F00] text-white rounded-md text-[13px] font-medium transition-colors disabled:opacity-50"
          >
            <Save className="w-3.5 h-3.5" /> {goalsBusy ? "Salvataggio…" : "Salva obiettivi"}
          </button>
        </form>
      )}

      {/* Partita IVA: mostrata nell'intestazione del report PDF provvigioni
      per mandante (Provvigioni → Genera report PDF) — non condizionata a
      personaleEnabled come il logo qui sotto, perché la maggior parte
      degli account non ha attivato il modulo Personale ma ha comunque il
      modulo provvigioni, quindi può generare quel report. */}
      <div className="mt-8">
        <div className="mb-3">
          <h2 className="font-cabinet text-xl font-black">Dati aziendali</h2>
          <p className="text-[#52525B] mt-1 text-[13px]">
            Mostrata in testa al report PDF provvigioni che generi per un mandante (Provvigioni &rarr; Genera report PDF).
          </p>
        </div>
        {vatNumber === null ? (
          <div className="flex items-center gap-2 text-[13px] text-[#6B6B72]">
            <Loader2 className="w-4 h-4 animate-spin" /> Caricamento…
          </div>
        ) : (
          <form onSubmit={saveVatNumber} className="border border-[#E4E4E1] rounded-lg p-5 flex items-end gap-3">
            <div className="flex-1 max-w-xs">
              <label className="block text-[12px] font-semibold text-[#52525B] mb-1.5">Partita IVA</label>
              <input
                type="text"
                value={vatNumber}
                onChange={(e) => setVatNumber(e.target.value)}
                placeholder="es. 01234567890"
                maxLength={20}
                className="w-full px-3 py-2 border border-[#E4E4E1] rounded-md text-[14px] focus:outline-none focus:border-[#B23E00]"
              />
            </div>
            <button
              type="submit"
              disabled={vatNumberBusy}
              className="flex items-center gap-1.5 px-4 py-2 bg-[#B23E00] hover:bg-[#E04F00] text-white rounded-md text-[13px] font-medium transition-colors disabled:opacity-50"
            >
              <Save className="w-3.5 h-3.5" /> {vatNumberBusy ? "Salvataggio…" : "Salva"}
            </button>
          </form>
        )}
      </div>

      {personaleEnabled && (
        <div className="mt-8">
          <div className="mb-3">
            <h2 className="font-cabinet text-xl font-black">Logo aziendale</h2>
            <p className="text-[#52525B] mt-1 text-[13px]">
              Mostrato in testa al cartellino presenze esportato (Presenze &rarr; Esporta cartellino).
            </p>
          </div>
          {companyLogo === null ? (
            <div className="flex items-center gap-2 text-[13px] text-[#6B6B72]">
              <Loader2 className="w-4 h-4 animate-spin" /> Caricamento…
            </div>
          ) : (
            <div className="border border-[#E4E4E1] rounded-lg p-5 flex items-center gap-4">
              {companyLogo ? (
                <img src={companyLogo} alt="Logo aziendale" className="h-14 max-w-[200px] object-contain border border-[#E4E4E1] rounded-md p-1" />
              ) : (
                <div className="h-14 w-24 flex items-center justify-center border border-dashed border-[#E4E4E1] rounded-md text-[#6B6B72]">
                  <Image className="w-5 h-5" />
                </div>
              )}
              <div className="flex items-center gap-2">
                <label className="px-3 py-2 border border-[#E4E4E1] rounded-md text-[13px] font-medium cursor-pointer hover:border-[#0A192F]">
                  {companyLogo ? "Cambia logo" : "Carica logo"}
                  <input type="file" accept="image/*" className="hidden" disabled={companyLogoBusy}
                    onChange={(e) => { const f = e.target.files?.[0]; if (f) saveCompanyLogo(f); e.target.value = ""; }} />
                </label>
                {companyLogo && (
                  <button onClick={removeCompanyLogo} disabled={companyLogoBusy}
                    className="px-3 py-2 border border-[#E4E4E1] rounded-md text-[13px] font-medium text-red-600 hover:border-red-300 disabled:opacity-50">
                    Rimuovi
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {personaleEnabled && (
        <div className="mt-8">
          <div className="mb-3">
            <h2 className="font-cabinet text-xl font-black">Ferie</h2>
            <p className="text-[#52525B] mt-1 text-[13px]">
              Come contare i giorni di ferie godute/residue nella scheda dipendente.
            </p>
          </div>
          {leaveSettings === null ? (
            <div className="flex items-center gap-2 text-[13px] text-[#6B6B72]">
              <Loader2 className="w-4 h-4 animate-spin" /> Caricamento…
            </div>
          ) : (
            <div className="border border-[#E4E4E1] rounded-lg p-5 space-y-3">
              <label className="flex items-start gap-3 cursor-pointer">
                <input type="radio" name="ferie_count_mode" className="mt-1" disabled={leaveSettingsBusy}
                  checked={leaveSettings.ferie_count_mode === "calendario"}
                  onChange={() => saveLeaveSettings("calendario")} />
                <span>
                  <span className="block text-[13px] font-semibold">Giorni di calendario</span>
                  <span className="block text-[12px] text-[#6B6B72]">Conta ogni giorno dell'intervallo, weekend inclusi (es. venerdì-lunedì = 4 giorni).</span>
                </span>
              </label>
              <label className="flex items-start gap-3 cursor-pointer">
                <input type="radio" name="ferie_count_mode" className="mt-1" disabled={leaveSettingsBusy}
                  checked={leaveSettings.ferie_count_mode === "lavorativi"}
                  onChange={() => saveLeaveSettings("lavorativi")} />
                <span>
                  <span className="block text-[13px] font-semibold">Soli giorni lavorativi</span>
                  <span className="block text-[12px] text-[#6B6B72]">Esclude sabato e domenica (es. venerdì-lunedì = 2 giorni). Non esclude le festività infrasettimanali.</span>
                </span>
              </label>
              <label className="flex items-start gap-3 cursor-pointer">
                <input type="radio" name="ferie_count_mode" className="mt-1" disabled={leaveSettingsBusy}
                  checked={leaveSettings.ferie_count_mode === "festivita"}
                  onChange={() => saveLeaveSettings("festivita")} />
                <span>
                  <span className="block text-[13px] font-semibold">Esclude domenica e festività</span>
                  <span className="block text-[12px] text-[#6B6B72]">Sabato incluso, domenica e festività nazionali escluse (Capodanno, Pasquetta, Ferragosto, Natale, ecc.). Per chi lavora anche il sabato.</span>
                </span>
              </label>
              <p className="text-[11px] text-[#6B6B72] pt-1">Si applica solo alle Ferie: le Malattie restano sempre a giorni di calendario.</p>
            </div>
          )}
        </div>
      )}
    </>
  );
}

import { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import {
  CalendarDays, CheckCircle2, Loader2, RefreshCw, Unplug, Plug, History, Target, Save,
  ShieldCheck, Download, Trash2, AlertTriangle, Eye, EyeOff, Home, Building2, Cookie, Star, Image,
} from "lucide-react";
import { toast } from "sonner";
import api from "../api";
import AiActionsLog from "../components/AiActionsLog";
import LocationPicker from "../components/LocationPicker";
import { useAuth } from "../contexts/AuthContext";
import { useCookieConsent } from "../contexts/CookieConsentContext";
import { resizeImageToDataUrl } from "../utils/image";

export default function Settings() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const personaleEnabled = (user?.enabled_extra_modules || []).includes("personale");
  const { consent, openPreferences } = useCookieConsent();
  const [searchParams, setSearchParams] = useSearchParams();
  const [status, setStatus] = useState(null); // null = caricamento
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState("integrazioni"); // integrazioni | obiettivi | registro-ai | privacy

  const [goals, setGoals] = useState(null); // null = caricamento
  const [goalsBusy, setGoalsBusy] = useState(false);

  const [addresses, setAddresses] = useState(null); // null = caricamento
  const [addressesBusy, setAddressesBusy] = useState(false);

  const [leaveSettings, setLeaveSettings] = useState(null); // null = caricamento
  const [leaveSettingsBusy, setLeaveSettingsBusy] = useState(false);

  const [companyLogo, setCompanyLogo] = useState(null); // null = caricamento, "" = nessun logo impostato
  const [companyLogoBusy, setCompanyLogoBusy] = useState(false);

  const [fbRating, setFbRating] = useState(0);
  const [fbText, setFbText] = useState("");
  const [fbConsent, setFbConsent] = useState(false);
  const [fbBusy, setFbBusy] = useState(false);
  const [fbSent, setFbSent] = useState(false);

  const submitFeedback = async (e) => {
    e.preventDefault();
    if (!fbRating) { toast.error("Seleziona un voto da 1 a 5 stelle"); return; }
    setFbBusy(true);
    try {
      await api.post("/feedback", { rating: fbRating, text: fbText.trim(), publish_consent: fbConsent });
      setFbSent(true);
      setFbRating(0);
      setFbText("");
      setFbConsent(false);
      toast.success("Grazie per il tuo feedback!");
    } catch {
      toast.error("Invio non riuscito, riprova tra poco");
    } finally {
      setFbBusy(false);
    }
  };

  const [exporting, setExporting] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const [deletePasswordVisible, setDeletePasswordVisible] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [deleting, setDeleting] = useState(false);

  const loadGoals = async () => {
    try {
      const { data } = await api.get("/settings/goals");
      setGoals(data);
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
      const { data } = await api.put("/settings/goals", payload);
      setGoals(data);
      toast.success("Obiettivi aggiornati");
    } catch {
      toast.error("Errore nel salvataggio degli obiettivi");
    } finally {
      setGoalsBusy(false);
    }
  };

  const loadStatus = async () => {
    try {
      const res = await api.get("/integrations/google/status");
      setStatus(res.data);
    } catch (e) {
      setStatus({ connected: false });
    }
  };

  const loadAddresses = async () => {
    try {
      const { data } = await api.get("/settings/addresses");
      setAddresses(data);
    } catch {
      toast.error("Impossibile caricare gli indirizzi");
    }
  };

  const saveAddresses = async (e) => {
    e.preventDefault();
    setAddressesBusy(true);
    try {
      const { data } = await api.put("/settings/addresses", addresses);
      setAddresses(data);
      toast.success("Indirizzi aggiornati");
    } catch {
      toast.error("Errore nel salvataggio degli indirizzi");
    } finally {
      setAddressesBusy(false);
    }
  };

  const loadLeaveSettings = async () => {
    if (!personaleEnabled) return;
    try {
      const { data } = await api.get("/settings/leave");
      setLeaveSettings(data);
    } catch {
      toast.error("Impossibile caricare le impostazioni ferie");
    }
  };

  const saveLeaveSettings = async (mode) => {
    setLeaveSettingsBusy(true);
    try {
      const { data } = await api.put("/settings/leave", { ferie_count_mode: mode });
      setLeaveSettings(data);
      toast.success("Preferenza aggiornata");
    } catch {
      toast.error("Errore nel salvataggio");
    } finally {
      setLeaveSettingsBusy(false);
    }
  };

  const loadCompanySettings = async () => {
    if (!personaleEnabled) return;
    try {
      const { data } = await api.get("/settings/company");
      setCompanyLogo(data.logo || "");
    } catch {
      toast.error("Impossibile caricare il logo aziendale");
    }
  };

  // Ridimensionato lato client con lo stesso helper già usato per la foto
  // dipendente (vedi utils/image.js e EmployeeDetailSheet.jsx) — mostrato
  // in testa al cartellino presenze esportato, vedi
  // services/attendance_xlsx_export.py.
  const saveCompanyLogo = async (file) => {
    setCompanyLogoBusy(true);
    try {
      const dataUrl = await resizeImageToDataUrl(file, 300);
      const { data } = await api.put("/settings/company", { logo: dataUrl });
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
      const { data } = await api.put("/settings/company", { logo: null });
      setCompanyLogo(data.logo || "");
      toast.success("Logo rimosso");
    } catch {
      toast.error("Errore nella rimozione del logo");
    } finally {
      setCompanyLogoBusy(false);
    }
  };

  useEffect(() => {
    loadStatus();
    loadGoals();
    loadAddresses();
    loadLeaveSettings();
    loadCompanySettings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const gcal = searchParams.get("gcal");
    if (gcal === "connected") {
      toast.success("Google Calendar collegato con successo");
      loadStatus();
      searchParams.delete("gcal");
      setSearchParams(searchParams, { replace: true });
    } else if (gcal === "error") {
      toast.error("Collegamento a Google Calendar non riuscito. Riprova.");
      searchParams.delete("gcal");
      searchParams.delete("reason");
      setSearchParams(searchParams, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const connect = async () => {
    setBusy(true);
    try {
      const res = await api.get("/integrations/google/connect");
      window.location.href = res.data.auth_url;
    } catch (e) {
      toast.error("Impossibile avviare il collegamento a Google");
      setBusy(false);
    }
  };

  const disconnect = async () => {
    setBusy(true);
    try {
      await api.post("/integrations/google/disconnect");
      toast.success("Google Calendar scollegato");
      await loadStatus();
    } catch (e) {
      toast.error("Errore durante lo scollegamento");
    } finally {
      setBusy(false);
    }
  };

  const syncNow = async () => {
    setBusy(true);
    try {
      await api.post("/integrations/google/sync");
      toast.success("Sincronizzazione avviata");
    } catch (e) {
      toast.error("Errore durante la sincronizzazione");
    } finally {
      setBusy(false);
    }
  };

  const exportMyData = async () => {
    setExporting(true);
    try {
      const res = await api.get("/privacy/export", { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = "i-miei-dati-salesfly.zip";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success("Download avviato");
    } catch {
      toast.error("Errore durante l'esportazione dei dati");
    } finally {
      setExporting(false);
    }
  };

  const deleteMyAccount = async () => {
    setDeleting(true);
    try {
      await api.post("/privacy/delete-account", { password: deletePassword });
      toast.success("Account eliminato definitivamente");
      await logout();
      navigate("/");
    } catch (err) {
      const msg = err?.response?.data?.detail || "Password non corretta, o errore durante l'eliminazione";
      toast.error(msg);
      setDeleting(false);
    }
  };

  return (
    <div className={tab === "registro-ai" ? "max-w-5xl" : "max-w-3xl"}>
      {/* overflow-x-auto: senza, i 5 tab non ci stanno su una riga sotto una
      certa larghezza e si accavallano — stesso pattern già corretto in
      ClientDetail.jsx per lo stesso motivo. */}
      <div className="flex items-center gap-1 mb-6 border-b border-[#E4E4E1] overflow-x-auto">
        <button
          onClick={() => setTab("integrazioni")}
          className={`flex items-center gap-1.5 px-3 py-2.5 text-[13px] font-medium whitespace-nowrap border-b-2 -mb-px transition-colors ${
            tab === "integrazioni" ? "border-[#B23E00] text-[#0A192F]" : "border-transparent text-[#6B6B72] hover:text-[#52525B]"
          }`}
        >
          <Plug className="w-3.5 h-3.5" /> Integrazioni
        </button>
        <button
          onClick={() => setTab("obiettivi")}
          className={`flex items-center gap-1.5 px-3 py-2.5 text-[13px] font-medium whitespace-nowrap border-b-2 -mb-px transition-colors ${
            tab === "obiettivi" ? "border-[#B23E00] text-[#0A192F]" : "border-transparent text-[#6B6B72] hover:text-[#52525B]"
          }`}
        >
          <Target className="w-3.5 h-3.5" /> Obiettivi
        </button>
        <button
          onClick={() => setTab("percorsi")}
          className={`flex items-center gap-1.5 px-3 py-2.5 text-[13px] font-medium whitespace-nowrap border-b-2 -mb-px transition-colors ${
            tab === "percorsi" ? "border-[#B23E00] text-[#0A192F]" : "border-transparent text-[#6B6B72] hover:text-[#52525B]"
          }`}
        >
          <Home className="w-3.5 h-3.5" /> Punti di partenza
        </button>
        <button
          onClick={() => setTab("registro-ai")}
          className={`flex items-center gap-1.5 px-3 py-2.5 text-[13px] font-medium whitespace-nowrap border-b-2 -mb-px transition-colors ${
            tab === "registro-ai" ? "border-[#B23E00] text-[#0A192F]" : "border-transparent text-[#6B6B72] hover:text-[#52525B]"
          }`}
        >
          <History className="w-3.5 h-3.5" /> Registro AI
        </button>
        <button
          onClick={() => setTab("privacy")}
          className={`flex items-center gap-1.5 px-3 py-2.5 text-[13px] font-medium whitespace-nowrap border-b-2 -mb-px transition-colors ${
            tab === "privacy" ? "border-[#B23E00] text-[#0A192F]" : "border-transparent text-[#6B6B72] hover:text-[#52525B]"
          }`}
        >
          <ShieldCheck className="w-3.5 h-3.5" /> Privacy e dati
        </button>
        <button
          onClick={() => setTab("feedback")}
          className={`flex items-center gap-1.5 px-3 py-2.5 text-[13px] font-medium whitespace-nowrap border-b-2 -mb-px transition-colors ${
            tab === "feedback" ? "border-[#B23E00] text-[#0A192F]" : "border-transparent text-[#6B6B72] hover:text-[#52525B]"
          }`}
        >
          <Star className="w-3.5 h-3.5" /> Feedback
        </button>
      </div>

      {tab === "registro-ai" ? (
        <AiActionsLog />
      ) : tab === "percorsi" ? (
        <>
          <div className="mb-8">
            <div className="font-mono text-[11px] uppercase tracking-widest text-[#B23E00] mb-1">Impostazioni</div>
            <h1 className="font-cabinet text-3xl font-black">Punti di partenza</h1>
            <p className="text-[#52525B] mt-1">
              Imposta l'indirizzo di casa e/o ufficio per poterli scegliere come punto di partenza nel pianificatore del giro visite (Mappa clienti).
            </p>
          </div>

          {addresses === null ? (
            <div className="flex items-center gap-2 text-[13px] text-[#6B6B72]">
              <Loader2 className="w-4 h-4 animate-spin" /> Caricamento…
            </div>
          ) : (
            <form onSubmit={saveAddresses} className="space-y-5">
              <div className="border border-[#E4E4E1] rounded-lg p-5">
                <div className="flex items-center gap-2 mb-3">
                  <Home className="w-4 h-4 text-[#B23E00]" />
                  <div className="font-semibold text-[15px]">Casa</div>
                </div>
                <input
                  value={addresses.home_address || ""}
                  onChange={(e) => setAddresses({ ...addresses, home_address: e.target.value })}
                  placeholder="Etichetta o indirizzo (es. Via Roma 10, Bologna)"
                  className="w-full mb-3 px-3 py-2 border border-[#E4E4E1] rounded-md text-[13px]"
                />
                <LocationPicker
                  address={addresses.home_address} city="" province=""
                  lat={addresses.home_lat} lng={addresses.home_lng}
                  onChange={(lat, lng) => setAddresses((prev) => ({ ...prev, home_lat: lat, home_lng: lng }))}
                />
              </div>

              <div className="border border-[#E4E4E1] rounded-lg p-5">
                <div className="flex items-center gap-2 mb-3">
                  <Building2 className="w-4 h-4 text-[#B23E00]" />
                  <div className="font-semibold text-[15px]">Ufficio</div>
                </div>
                <input
                  value={addresses.office_address || ""}
                  onChange={(e) => setAddresses({ ...addresses, office_address: e.target.value })}
                  placeholder="Etichetta o indirizzo (es. Via Milano 5, Bologna)"
                  className="w-full mb-3 px-3 py-2 border border-[#E4E4E1] rounded-md text-[13px]"
                />
                <LocationPicker
                  address={addresses.office_address} city="" province=""
                  lat={addresses.office_lat} lng={addresses.office_lng}
                  onChange={(lat, lng) => setAddresses((prev) => ({ ...prev, office_lat: lat, office_lng: lng }))}
                />
              </div>

              <button
                type="submit"
                disabled={addressesBusy}
                className="flex items-center gap-1.5 px-4 py-2 bg-[#B23E00] hover:bg-[#E04F00] text-white rounded-md text-[13px] font-medium transition-colors disabled:opacity-50"
              >
                <Save className="w-3.5 h-3.5" /> {addressesBusy ? "Salvataggio…" : "Salva indirizzi"}
              </button>
            </form>
          )}
        </>
      ) : tab === "privacy" ? (
        <>
          <div className="mb-8">
            <div className="font-mono text-[11px] uppercase tracking-widest text-[#B23E00] mb-1">Impostazioni</div>
            <h1 className="font-cabinet text-3xl font-black">Privacy e dati</h1>
            <p className="text-[#52525B] mt-1">
              Gestisci i tuoi dati personali secondo il GDPR: puoi scaricarne una copia completa o richiederne la cancellazione definitiva.
            </p>
          </div>

          <div className="border border-[#E4E4E1] rounded-lg p-5 mb-5">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-md bg-[#F3F3F1] flex items-center justify-center shrink-0">
                <Download className="w-5 h-5 text-[#0A192F]" />
              </div>
              <div className="flex-1">
                <div className="font-semibold text-[15px]">Scarica i tuoi dati</div>
                <div className="text-[13px] text-[#52525B] mt-0.5">
                  Un file .zip con tutti i tuoi dati (clienti, offerte, ordini, provvigioni, documenti, conversazioni con l'assistente AI e altro) in formato leggibile — il tuo diritto alla portabilità dei dati (art. 20 GDPR).
                </div>
                <button
                  onClick={exportMyData}
                  disabled={exporting}
                  className="mt-3 flex items-center gap-1.5 px-4 py-2 bg-[#0A192F] hover:bg-[#172A45] text-white rounded-md text-[13px] font-medium transition-colors disabled:opacity-50"
                >
                  {exporting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                  {exporting ? "Preparazione in corso…" : "Scarica i miei dati"}
                </button>
              </div>
            </div>
          </div>

          <div className="border border-[#E4E4E1] rounded-lg p-5 mb-5">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-md bg-[#F3F3F1] flex items-center justify-center shrink-0">
                <Cookie className="w-5 h-5 text-[#0A192F]" />
              </div>
              <div className="flex-1">
                <div className="font-semibold text-[15px]">Preferenze cookie</div>
                <div className="text-[13px] text-[#52525B] mt-0.5">
                  {consent?.analytics
                    ? "Hai acconsentito ai cookie di analisi (Google Analytics, PostHog). Non vengono comunque mai usati per registrare le sessioni qui nel gestionale."
                    : "Al momento sono attivi solo i cookie tecnici necessari: hai rifiutato (o non ancora scelto) i cookie di analisi."}
                </div>
                <button
                  onClick={openPreferences}
                  className="mt-3 flex items-center gap-1.5 px-4 py-2 border border-[#E4E4E1] hover:bg-[#F9F9F8] rounded-md text-[13px] font-medium transition-colors"
                >
                  <Cookie className="w-3.5 h-3.5" /> Cambia preferenze
                </button>
              </div>
            </div>
          </div>

          <div className="border border-[#DC2626]/30 bg-[#FEF2F2] rounded-lg p-5">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-md bg-white flex items-center justify-center shrink-0">
                <Trash2 className="w-5 h-5 text-[#DC2626]" />
              </div>
              <div className="flex-1">
                <div className="font-semibold text-[15px] text-[#DC2626]">Elimina definitivamente il tuo account</div>
                <div className="text-[13px] text-[#52525B] mt-0.5">
                  Cancella in modo permanente e irreversibile il tuo account e tutti i dati collegati (clienti, offerte, documenti, provvigioni, conversazioni AI) — il tuo diritto all'oblio (art. 17 GDPR).
                  Se hai un abbonamento attivo, verrà disdetto automaticamente. <strong>Questa azione non può essere annullata.</strong>
                </div>
                {!deleteOpen ? (
                  <button
                    onClick={() => setDeleteOpen(true)}
                    className="mt-3 flex items-center gap-1.5 px-4 py-2 border-2 border-[#DC2626] text-[#DC2626] hover:bg-[#DC2626] hover:text-white rounded-md text-[13px] font-medium transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" /> Elimina il mio account
                  </button>
                ) : (
                  <div className="mt-4 bg-white border border-[#E4E4E1] rounded-md p-4 space-y-3">
                    <div className="flex items-start gap-2 text-[12px] text-[#B45309]">
                      <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                      Per confermare, inserisci la tua password e scrivi <strong>ELIMINA</strong> nel campo qui sotto.
                    </div>
                    <div className="relative">
                      <input
                        type={deletePasswordVisible ? "text" : "password"}
                        value={deletePassword}
                        onChange={(e) => setDeletePassword(e.target.value)}
                        placeholder="La tua password attuale"
                        className="w-full border border-[#E4E4E1] rounded-md px-3 py-2 pr-9 text-[13px]"
                      />
                      <button
                        type="button"
                        onClick={() => setDeletePasswordVisible((v) => !v)}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-[#6B6B72]"
                      >
                        {deletePasswordVisible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                    <input
                      value={deleteConfirmText}
                      onChange={(e) => setDeleteConfirmText(e.target.value)}
                      placeholder='Scrivi "ELIMINA" per confermare'
                      className="w-full border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]"
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={deleteMyAccount}
                        disabled={deleting || deleteConfirmText !== "ELIMINA" || !deletePassword}
                        className="flex items-center gap-1.5 px-4 py-2 bg-[#DC2626] hover:bg-[#B91C1C] text-white rounded-md text-[13px] font-medium disabled:opacity-40 transition-colors"
                      >
                        {deleting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                        {deleting ? "Eliminazione in corso…" : "Conferma eliminazione definitiva"}
                      </button>
                      <button
                        onClick={() => { setDeleteOpen(false); setDeletePassword(""); setDeleteConfirmText(""); }}
                        disabled={deleting}
                        className="px-4 py-2 border border-[#E4E4E1] rounded-md text-[13px] font-medium text-[#52525B]"
                      >
                        Annulla
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </>
      ) : tab === "obiettivi" ? (
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

          {personaleEnabled && (
            <div className="mt-8">
              <div className="mb-3">
                <h2 className="font-cabinet text-xl font-black">Azienda</h2>
                <p className="text-[#52525B] mt-1 text-[13px]">
                  Logo mostrato in testa al cartellino presenze esportato (Presenze &rarr; Esporta cartellino).
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
      ) : tab === "feedback" ? (
        <>
          <div className="mb-8">
            <div className="font-mono text-[11px] uppercase tracking-widest text-[#B23E00] mb-1">Impostazioni</div>
            <h1 className="font-cabinet text-3xl font-black">Feedback</h1>
            <p className="text-[#52525B] mt-1">
              Raccontaci come va con SALESFLY — ci aiuta a migliorare, e con il tuo consenso può comparire come recensione sul sito.
            </p>
          </div>

          {fbSent ? (
            <div className="border border-[#E4E4E1] rounded-lg p-6 text-center">
              <CheckCircle2 className="w-8 h-8 text-[#16A34A] mx-auto mb-3" />
              <div className="font-cabinet font-bold text-[16px] mb-1">Grazie per il tuo feedback!</div>
              <p className="text-[13px] text-[#52525B]">L'abbiamo ricevuto. Puoi inviarne un altro quando vuoi.</p>
              <button
                onClick={() => setFbSent(false)}
                className="mt-4 text-[13px] font-medium text-[#0A192F] underline underline-offset-4"
              >
                Invia un altro feedback
              </button>
            </div>
          ) : (
            <form onSubmit={submitFeedback} className="border border-[#E4E4E1] rounded-lg p-5 space-y-5">
              <div>
                <label className="block text-[12px] font-semibold text-[#52525B] mb-2">Voto</label>
                <div className="flex items-center gap-1">
                  {[1, 2, 3, 4, 5].map((n) => (
                    <button
                      key={n}
                      type="button"
                      data-testid={`feedback-star-${n}`}
                      onClick={() => setFbRating(n)}
                      className="p-0.5"
                      aria-label={`${n} stelle`}
                    >
                      <Star
                        className={`w-7 h-7 transition-colors ${n <= fbRating ? "fill-[#B23E00] text-[#B23E00]" : "text-[#E4E4E1]"}`}
                      />
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-[12px] font-semibold text-[#52525B] mb-1.5">Il tuo commento (opzionale)</label>
                <textarea
                  data-testid="feedback-text-input"
                  value={fbText}
                  onChange={(e) => setFbText(e.target.value)}
                  rows={4}
                  placeholder="Cosa ti piace? Cosa cambieresti?"
                  className="w-full px-3 py-2 border border-[#E4E4E1] rounded-md text-[14px] focus:outline-none focus:border-[#B23E00]"
                />
              </div>
              <label className="flex items-start gap-2 text-[13px] text-[#52525B]">
                <input
                  type="checkbox"
                  data-testid="feedback-publish-consent"
                  checked={fbConsent}
                  onChange={(e) => setFbConsent(e.target.checked)}
                  className="mt-0.5"
                />
                <span>Autorizzo la pubblicazione di questa recensione sul sito, anche con il mio nome. Verrà comunque controllata prima di essere pubblicata.</span>
              </label>
              <button
                type="submit"
                disabled={fbBusy}
                data-testid="feedback-submit-button"
                className="flex items-center gap-1.5 px-4 py-2 bg-[#B23E00] hover:bg-[#E04F00] text-white rounded-md text-[13px] font-medium transition-colors disabled:opacity-50"
              >
                <Save className="w-3.5 h-3.5" /> {fbBusy ? "Invio…" : "Invia feedback"}
              </button>
            </form>
          )}
        </>
      ) : (
        <>
          <div className="mb-8">
            <div className="font-mono text-[11px] uppercase tracking-widest text-[#B23E00] mb-1">Impostazioni</div>
            <h1 className="font-cabinet text-3xl font-black">Integrazioni</h1>
            <p className="text-[#52525B] mt-1">Collega servizi esterni per far lavorare Salesfly insieme ai tuoi strumenti.</p>
          </div>

          <div className="border border-[#E4E4E1] rounded-lg p-5">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-md bg-[#F3F3F1] flex items-center justify-center shrink-0">
                  <CalendarDays className="w-5 h-5 text-[#0A192F]" />
                </div>
                <div>
                  <div className="font-semibold text-[15px]">Google Calendar</div>
                  <div className="text-[13px] text-[#52525B] mt-0.5">
                    Sincronizza automaticamente gli appuntamenti dell'Agenda con Google Calendar, in entrambe le direzioni.
                  </div>
                  {status?.connected && (
                    <div className="flex items-center gap-1.5 mt-2 text-[12px] text-[#16A34A] font-medium">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Collegato come {status.google_email}
                    </div>
                  )}
                  {status?.connected && status.needs_reauth && (
                    <div className="flex items-center gap-1.5 mt-2 text-[12px] text-[#DC2626] font-medium">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      L'autorizzazione non è più valida: riconnetti per riprendere la sincronizzazione
                    </div>
                  )}
                </div>
              </div>

              {status === null ? (
                <Loader2 className="w-4 h-4 animate-spin text-[#6B6B72]" />
              ) : status.connected ? (
                <div className="flex items-center gap-2 shrink-0">
                  {status.needs_reauth && (
                    <button
                      data-testid="gcal-reconnect-button"
                      onClick={connect}
                      disabled={busy}
                      className="flex items-center gap-1.5 px-3 py-2 bg-[#B23E00] hover:bg-[#E04F00] text-white rounded-md text-[12px] font-medium transition-colors disabled:opacity-50"
                    >
                      <Plug className="w-3.5 h-3.5" /> Riconnetti
                    </button>
                  )}
                  <button
                    data-testid="gcal-sync-button"
                    onClick={syncNow}
                    disabled={busy}
                    className="flex items-center gap-1.5 px-3 py-2 border border-[#E4E4E1] hover:border-[#0A192F] rounded-md text-[12px] font-medium transition-colors disabled:opacity-50"
                  >
                    <RefreshCw className="w-3.5 h-3.5" /> Sincronizza ora
                  </button>
                  <button
                    data-testid="gcal-disconnect-button"
                    onClick={disconnect}
                    disabled={busy}
                    className="flex items-center gap-1.5 px-3 py-2 border border-[#E4E4E1] hover:border-[#DC2626] hover:text-[#DC2626] rounded-md text-[12px] font-medium transition-colors disabled:opacity-50"
                  >
                    <Unplug className="w-3.5 h-3.5" /> Scollega
                  </button>
                </div>
              ) : (
                <button
                  data-testid="gcal-connect-button"
                  onClick={connect}
                  disabled={busy}
                  className="shrink-0 px-4 py-2 bg-[#B23E00] hover:bg-[#E04F00] text-white rounded-md text-[13px] font-medium transition-colors disabled:opacity-50"
                >
                  {busy ? "Attendere…" : "Connetti"}
                </button>
              )}
            </div>
          </div>

          <p className="text-[11px] text-[#6B6B72] font-mono mt-4">
            La sincronizzazione con Google avviene automaticamente ogni pochi minuti, oltre che subito dopo ogni modifica fatta qui in Salesfly.
          </p>
        </>
      )}
    </div>
  );
}

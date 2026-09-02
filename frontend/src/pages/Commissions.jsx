import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Download } from "lucide-react";
import { toast } from "sonner";
import { exportCommissions } from "../utils/export";
import { useMandante } from "../contexts/MandanteContext";
import { listClients } from "../api/clients";
import { listMandanti } from "../api/mandanti";
import { getFiscalSettings } from "../api/settings";
import { computeFiscalBreakdown } from "../utils/fiscalCalc";
import {
  listCommissions, getBonusSummary, updateCommissionStatus, deleteCommission as deleteCommissionApi,
  listManualCommissions, createManualCommission, updateManualCommission, deleteManualCommission,
} from "../api/commissions";
import { fmt, currentPeriod, emptyManualForm, groupByPeriod, periodLabel } from "../components/commissions/constants";
import ManualCommissionForm from "../components/commissions/ManualCommissionForm";
import BonusTierCards from "../components/commissions/BonusTierCards";
import CommissionsTable from "../components/commissions/CommissionsTable";

export default function Commissions() {
  const { activeMandante } = useMandante();
  const mandanteParam = activeMandante && activeMandante !== "all" ? activeMandante : undefined;
  const [commissions, setCommissions] = useState([]);
  const [clients, setClients] = useState([]);
  const [mandanti, setMandanti] = useState([]);
  const [bonusSummary, setBonusSummary] = useState([]);
  const [filter, setFilter] = useState("all");
  const [clientFilter, setClientFilter] = useState("all");
  const [manualCommissions, setManualCommissions] = useState([]);
  const [fiscalSettings, setFiscalSettings] = useState(null); // null finché non caricata
  const [manualForm, setManualForm] = useState(emptyManualForm);
  const [editingManualId, setEditingManualId] = useState(null);
  const [savingManual, setSavingManual] = useState(false);
  const [expandedPeriods, setExpandedPeriods] = useState(() => new Set([currentPeriod()]));
  const togglePeriod = (key) => setExpandedPeriods((prev) => {
    const next = new Set(prev);
    if (next.has(key)) next.delete(key); else next.add(key);
    return next;
  });

  const load = async () => {
    const [c, cl, m, bs, mc] = await Promise.all([
      listCommissions({ mandante_id: mandanteParam }),
      listClients(),
      listMandanti(),
      getBonusSummary().catch(() => []),
      listManualCommissions().catch(() => []),
    ]);
    setCommissions(c);
    setClients(cl);
    setMandanti(m);
    setBonusSummary(bs);
    setManualCommissions(mc);
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [mandanteParam]);
  // Impostazione indipendente dal mandante/filtro selezionato, quindi
  // caricata una sola volta e non dentro load() (che invece va rieseguita
  // a ogni cambio di mandanteParam).
  useEffect(() => {
    getFiscalSettings().then(setFiscalSettings).catch(() => {});
  }, []);

  const startNewManualEntry = () => {
    setEditingManualId(null);
    setManualForm(emptyManualForm());
  };

  // Più righe manuali possono coesistere sullo stesso periodo, quindi non
  // c'è più un pre-fill automatico legato al mese scelto: si modifica
  // un'entrata esplicitamente cliccando "Modifica" sulla sua riga.
  const startEditManualEntry = (entry) => {
    setEditingManualId(entry.id);
    setManualForm({
      period: entry.period,
      amount: String(entry.amount),
      mandante_id: entry.mandante_id || "",
      client_id: entry.client_id || "",
      descrizione: entry.descrizione || "",
      stato: entry.stato || "maturato",
      note: entry.note || "",
      tipo: entry.tipo || "ordinaria",
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const byClient = clientFilter === "all" ? commissions : commissions.filter(c => c.client_id === clientFilter);
  const filtered = filter === "all" ? byClient : byClient.filter(c => c.status === filter);
  const accrued = byClient.filter(c => c.status === "maturato").reduce((s, c) => s + c.amount, 0);
  const collected = byClient.filter(c => c.status === "incassato").reduce((s, c) => s + c.amount, 0);
  const fatturatoClienteSelezionato = clientFilter === "all" ? null : byClient.reduce((s, c) => s + (c.base_amount ?? (c.rate ? c.amount / (c.rate / 100) : 0)), 0);
  // Una provvigione manuale senza mandante_id (o senza client_id) non è
  // attribuibile a nessun mandante/cliente specifico: quando è attivo il
  // filtro corrispondente va esclusa dai totali di quel filtro, altrimenti si
  // sommerebbero importi non riconducibili alla selezione corrente. In vista
  // "Tutti i mandanti"/"Tutti i clienti" restano invece tutte visibili,
  // taggate o no — stessa logica applicata sia lato mandante che cliente.
  const visibleManualCommissions = useMemo(() => {
    let list = mandanteParam ? manualCommissions.filter((m) => m.mandante_id === mandanteParam) : manualCommissions;
    if (clientFilter !== "all") list = list.filter((m) => m.client_id === clientFilter);
    return list;
  }, [manualCommissions, mandanteParam, clientFilter]);
  const manualAccrued = useMemo(() => visibleManualCommissions.filter((m) => (m.stato || "maturato") === "maturato").reduce((s, m) => s + (m.amount || 0), 0), [visibleManualCommissions]);
  const manualCollected = useMemo(() => visibleManualCommissions.filter((m) => m.stato === "incassato").reduce((s, m) => s + (m.amount || 0), 0), [visibleManualCommissions]);
  // Somma di TUTTI i mesi inseriti manualmente visibili nel filtro
  // mandante/cliente corrente: si aggiunge al totale calcolato dagli ordini,
  // per provvigioni concluse fuori dal flusso ordini del CRM.
  const manualTotal = manualAccrued + manualCollected;
  // Ritenuta/ENASARCO si applicano alla provvigione lorda una volta
  // incassata, non a quella ancora solo maturata (che il mandante deve
  // ancora versare) — coerente con come funziona nella realtà: il
  // mandante trattiene ritenuta ed ENASARCO al momento del pagamento, non
  // prima. Stessa formula del calcolatore dell'articolo del blog, vedi
  // utils/fiscalCalc.js.
  const fiscalBreakdown = fiscalSettings
    ? computeFiscalBreakdown(
        collected + manualCollected,
        fiscalSettings.regime_fiscale,
        fiscalSettings.base_ritenuta
      )
    : null;
  const manualEntriesByPeriod = useMemo(() => {
    const map = {};
    for (const m of visibleManualCommissions) {
      (map[m.period] ||= []).push(m);
    }
    return map;
  }, [visibleManualCommissions]);
  const periodGroups = useMemo(
    () => groupByPeriod(filtered, manualEntriesByPeriod),
    [filtered, manualEntriesByPeriod]
  );

  const setStatus = async (id, status) => {
    await updateCommissionStatus(id, status);
    toast.success("Stato aggiornato");
    load();
  };

  const saveManualCommission = async () => {
    const amount = parseFloat(manualForm.amount);
    if (Number.isNaN(amount) || amount <= 0) {
      toast.error("Inserisci un importo maggiore di zero");
      return;
    }
    if (!manualForm.period) {
      toast.error("Seleziona un mese");
      return;
    }
    setSavingManual(true);
    try {
      const payload = {
        period: manualForm.period,
        amount,
        mandante_id: manualForm.mandante_id || null,
        client_id: manualForm.client_id || null,
        descrizione: manualForm.descrizione || null,
        stato: manualForm.stato,
        note: manualForm.note || null,
        tipo: manualForm.tipo,
      };
      if (editingManualId) {
        await updateManualCommission(editingManualId, payload);
        toast.success("Provvigione manuale aggiornata");
      } else {
        await createManualCommission(payload);
        toast.success("Provvigione manuale aggiunta");
      }
      setExpandedPeriods((prev) => new Set(prev).add(manualForm.period));
      startNewManualEntry();
      load();
    } catch {
      toast.error("Errore salvataggio provvigione manuale");
    } finally {
      setSavingManual(false);
    }
  };

  const removeManualCommission = async (id, period) => {
    if (!window.confirm(`Rimuovere questa provvigione manuale di ${periodLabel(period)}?`)) return;
    await deleteManualCommission(id);
    if (editingManualId === id) startNewManualEntry();
    toast.success("Provvigione manuale rimossa");
    load();
  };

  const deleteCommission = async (id) => {
    if (!window.confirm("Eliminare questa provvigione?")) return;
    await deleteCommissionApi(id);
    toast.success("Provvigione eliminata");
    load();
  };

  return (
    <div className="p-4 md:p-8">
      <div className="border-b border-[#E4E4E1] pb-6 mb-6 flex items-end justify-between">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#B23E00] mb-2">Guadagni</div>
          <h1 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight">Provvigioni</h1>
        </div>
        <button
          data-testid="export-commissions-button"
          onClick={() => exportCommissions().then(() => toast.success("Export scaricato")).catch(() => toast.error("Errore export"))}
          className="flex items-center gap-2 px-4 py-2.5 border border-[#E4E4E1] hover:border-[#0A192F] rounded-md text-[13px] font-medium"
        >
          <Download className="w-4 h-4" /> Esporta CSV
        </button>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        <div className="bg-white border border-[#E4E4E1] rounded-md p-5">
          <div className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72] mb-2">Maturato</div>
          <div className="font-cabinet font-black text-3xl">{fmt(accrued + manualAccrued)}</div>
          <div className="text-[11px] text-[#52525B] mt-2">In attesa di incasso</div>
        </div>
        <div className="bg-white border border-[#E4E4E1] rounded-md p-5">
          <div className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72] mb-2">Incassato</div>
          <div className="font-cabinet font-black text-3xl text-[#059669]">{fmt(collected + manualCollected)}</div>
          <div className="text-[11px] text-[#52525B] mt-2">Già ricevuto</div>
        </div>
        <div className="bg-[#0A192F] text-white rounded-md p-5 col-span-2 lg:col-span-1">
          <div className="font-mono text-[10px] uppercase tracking-widest text-[#B23E00] mb-2">Totale generato</div>
          <div className="font-cabinet font-black text-3xl">{fmt(accrued + collected + manualTotal)}</div>
          <div className="text-[11px] text-white/60 mt-2">
            {commissions.length} provvigioni totali
            {manualTotal > 0 && <> · di cui {fmt(manualTotal)} inserite manualmente</>}
          </div>
        </div>
      </div>

      {fiscalBreakdown && (collected + manualCollected) > 0 && (
        <div className="bg-white border border-[#E4E4E1] rounded-md p-5 mb-6">
          <div className="flex items-center justify-between mb-3">
            <div className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72]">
              Netto stimato sull'incassato
            </div>
            <Link to="/app/impostazioni?tab=fiscale" className="text-[11px] text-[#B23E00] font-medium hover:underline">
              {fiscalSettings.regime_fiscale === "forfettario" ? "Regime forfettario" : "Regime ordinario"} · Modifica
            </Link>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-[13px]">
            <div>
              <div className="text-[#6B6B72] mb-1">Lordo incassato</div>
              <div className="font-mono font-semibold">{fmt(fiscalBreakdown.lordo)}</div>
            </div>
            <div>
              <div className="text-[#6B6B72] mb-1">Ritenuta d'acconto</div>
              <div className="font-mono font-semibold text-[#DC2626]">− {fmt(fiscalBreakdown.ritenutaAcconto)}</div>
            </div>
            <div>
              <div className="text-[#6B6B72] mb-1">ENASARCO (quota agente)</div>
              <div className="font-mono font-semibold text-[#DC2626]">− {fmt(fiscalBreakdown.contributoEnasarco)}</div>
            </div>
            <div>
              <div className="text-[#6B6B72] mb-1">Netto stimato</div>
              <div className="font-mono font-black text-[#059669]">{fmt(fiscalBreakdown.netto)}</div>
            </div>
          </div>
          <p className="text-[11px] text-[#6B6B72] mt-3">
            Calcolo indicativo in base alla situazione fiscale impostata, non sostituisce il commercialista.
          </p>
        </div>
      )}

      <ManualCommissionForm
        manualForm={manualForm} setManualForm={setManualForm} editingManualId={editingManualId}
        startNewManualEntry={startNewManualEntry} saveManualCommission={saveManualCommission} savingManual={savingManual}
        mandanti={mandanti} clients={clients}
      />

      <BonusTierCards bonusSummary={bonusSummary} />

      {/* Filtri */}
      <div className="flex gap-2 mb-4">
        {["all", "maturato", "incassato"].map(s => (
          <button key={s} onClick={() => setFilter(s)} data-testid={`filter-${s}`}
            className={`px-4 py-2 rounded-md text-[12px] font-medium ${filter === s ? "bg-[#0A192F] text-white" : "bg-white border border-[#E4E4E1]"}`}>
            {s === "all" ? "Tutte" : s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>
      {/* Filtro cliente */}
      <div className="flex items-center gap-2 mb-4">
        <select
          value={clientFilter}
          onChange={(e) => setClientFilter(e.target.value)}
          className="px-3 py-2 rounded-md text-[12px] font-medium bg-white border border-[#E4E4E1]"
        >
          <option value="all">Tutti i clienti</option>
          {[...clients].sort((a, b) => (a.company_name || "").localeCompare(b.company_name || "")).map(cl => (
            <option key={cl.id} value={cl.id}>{cl.company_name}</option>
          ))}
        </select>
        {clientFilter !== "all" && fatturatoClienteSelezionato !== null && (
          <span className="font-mono text-[11px] text-[#52525B]">
            Fatturato generato: <span className="font-bold text-[#0A192F]">{fmt(fatturatoClienteSelezionato)}</span>
          </span>
        )}
      </div>

      <CommissionsTable
        periodGroups={periodGroups} expandedPeriods={expandedPeriods} togglePeriod={togglePeriod}
        clients={clients} mandanti={mandanti}
        onToggleStatus={setStatus} onDelete={deleteCommission}
        onEditManual={startEditManualEntry} onRemoveManual={removeManualCommission}
      />
    </div>
  );
}

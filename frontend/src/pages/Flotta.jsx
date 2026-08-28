import { useEffect, useState } from "react";
import { Truck, CalendarClock, Coins, Package } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "../contexts/AuthContext";
import { listClients } from "../api/clients";
import { listOrders } from "../api/orders";
import { listEmployees } from "../api/employees";
import { listAutomations, createAutomation, updateAutomation } from "../api/automations";
import useVehicles from "../hooks/useVehicles";
import useVehicleDeadlines from "../hooks/useVehicleDeadlines";
import useVehicleCosts from "../hooks/useVehicleCosts";
import useCargoLoads from "../hooks/useCargoLoads";
import { EMPTY_VEHICLE, EMPTY_DEADLINE, EMPTY_COST, EMPTY_LOAD, REMINDER_DAY_OPTIONS, daysUntil } from "../components/flotta/constants";
import MezziTab from "../components/flotta/MezziTab";
import ScadenzeTab from "../components/flotta/ScadenzeTab";
import CostiTab from "../components/flotta/CostiTab";
import CaricoTab from "../components/flotta/CaricoTab";

export default function Flotta() {
  const { user } = useAuth();
  const disabledModules = user?.disabled_modules || [];
  const automazioniEnabled = !disabledModules.includes("automazioni");
  const clientiEnabled = !disabledModules.includes("clienti");
  const ordiniEnabled = !disabledModules.includes("ordini");
  const enabledExtraModules = user?.enabled_extra_modules || [];
  const personaleEnabled = enabledExtraModules.includes("personale");

  const [tab, setTab] = useState("mezzi"); // mezzi | scadenze | costi | carico
  const {
    vehicles, create: createVehicleApi, update: updateVehicleApi,
    setActive: setVehicleActiveApi, remove: removeVehicleApi,
  } = useVehicles();
  const {
    deadlines, create: createDeadlineApi, update: updateDeadlineApi, remove: removeDeadlineApi,
  } = useVehicleDeadlines();
  const {
    costs, create: createCostApi, update: updateCostApi, remove: removeCostApi,
  } = useVehicleCosts();
  const {
    loads, create: createLoadApi, update: updateLoadApi, sign: signLoadApi, remove: removeLoadApi,
  } = useCargoLoads();
  const [clients, setClients] = useState([]);
  const [orders, setOrders] = useState([]);
  const [employees, setEmployees] = useState([]);

  const [vehicleOpen, setVehicleOpen] = useState(false);
  const [vehicleEditTarget, setVehicleEditTarget] = useState(null);
  const [vehicleSearch, setVehicleSearch] = useState("");
  const [vehicleFilter, setVehicleFilter] = useState("all"); // all | active | inactive
  const [deadlineOpen, setDeadlineOpen] = useState(false);
  const [deadlineEditTarget, setDeadlineEditTarget] = useState(null);
  const [costOpen, setCostOpen] = useState(false);
  const [costEditTarget, setCostEditTarget] = useState(null);
  const [loadOpen, setLoadOpen] = useState(false);
  const [loadEditTarget, setLoadEditTarget] = useState(null);
  const [signTarget, setSignTarget] = useState(null);

  const [reminderAutomation, setReminderAutomation] = useState(null);
  const [reminderDays, setReminderDays] = useState(REMINDER_DAY_OPTIONS);

  const loadClients = async () => { if (!clientiEnabled) return; setClients(await listClients()); };
  const loadOrders = async () => { if (!ordiniEnabled) return; setOrders(await listOrders()); };
  const loadEmployees = async () => { if (!personaleEnabled) return; setEmployees(await listEmployees()); };
  const loadReminderAutomation = async () => {
    if (!automazioniEnabled) return;
    const data = await listAutomations();
    const existing = data.find((a) => a.trigger === "vehicle_deadline");
    if (existing) {
      setReminderAutomation(existing);
      setReminderDays(existing.config?.reminder_days || REMINDER_DAY_OPTIONS);
    }
  };

  useEffect(() => {
    loadClients(); loadOrders(); loadEmployees(); loadReminderAutomation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const activeVehicles = vehicles.filter((v) => v.active);
  const filteredVehicles = vehicles.filter((v) => {
    if (vehicleFilter === "active" && !v.active) return false;
    if (vehicleFilter === "inactive" && v.active) return false;
    if (!vehicleSearch.trim()) return true;
    const q = vehicleSearch.trim().toLowerCase();
    return v.plate.toLowerCase().includes(q) || (v.model || "").toLowerCase().includes(q);
  });
  const overdueCount = deadlines.filter((d) => daysUntil(d.due_date) < 0).length;
  const upcomingCount = deadlines.filter((d) => { const days = daysUntil(d.due_date); return days >= 0 && days <= 30; }).length;
  const totalCosts = costs.reduce((sum, c) => sum + c.amount, 0);

  // ---------- promemoria scadenze (Automazioni) ----------
  const toggleReminderDay = async (day) => {
    const next = reminderDays.includes(day)
      ? reminderDays.filter((d) => d !== day)
      : [...reminderDays, day].sort((a, b) => a - b);
    setReminderDays(next);
    const payload = {
      name: "Scadenze mezzi Flotta", trigger: "vehicle_deadline", action: "send_reminder",
      enabled: true, config: { reminder_days: next },
    };
    if (reminderAutomation) {
      await updateAutomation(reminderAutomation.id, payload);
    } else {
      const data = await createAutomation(payload);
      setReminderAutomation(data);
    }
    toast.success("Promemoria aggiornati");
  };

  // ---------- firma consegna ----------
  const signLoad = async (signature, signerName) => {
    await signLoadApi(signTarget.id, { signature, signer_name: signerName });
    toast.success("Consegna firmata");
    setSignTarget(null);
  };

  // ---------- mezzi ----------
  const saveVehicle = async (f) => {
    if (vehicleEditTarget) {
      await updateVehicleApi(vehicleEditTarget.id, f);
      toast.success("Mezzo aggiornato");
      setVehicleEditTarget(null);
    } else {
      await createVehicleApi(f);
      toast.success("Mezzo aggiunto");
      setVehicleOpen(false);
    }
  };
  const toggleVehicleActive = async (v) => {
    await setVehicleActiveApi(v.id, !v.active);
    toast.success(v.active ? "Mezzo disattivato" : "Mezzo riattivato");
  };
  const deleteVehicle = async (v) => {
    if (!window.confirm(`Eliminare "${v.plate}"? Scadenze, costi e carichi già registrati restano nello storico. Se vuoi solo toglierlo dalla flotta attiva, puoi disattivarlo invece.`)) return;
    await removeVehicleApi(v.id);
    toast.success("Mezzo eliminato");
  };

  // ---------- scadenze ----------
  const saveDeadline = async (f) => {
    const payload = { ...f };
    if (deadlineEditTarget) {
      await updateDeadlineApi(deadlineEditTarget.id, payload);
      toast.success("Scadenza aggiornata");
      setDeadlineEditTarget(null);
    } else {
      await createDeadlineApi(payload);
      toast.success("Scadenza aggiunta");
      setDeadlineOpen(false);
    }
  };
  const deleteDeadline = async (id) => {
    if (!window.confirm("Eliminare questa scadenza?")) return;
    await removeDeadlineApi(id);
    toast.success("Scadenza eliminata");
  };

  // ---------- costi ----------
  const saveCost = async (f) => {
    const payload = { ...f, amount: parseFloat(f.amount) };
    if (costEditTarget) {
      await updateCostApi(costEditTarget.id, payload);
      toast.success("Costo aggiornato");
      setCostEditTarget(null);
    } else {
      await createCostApi(payload);
      toast.success("Costo aggiunto");
      setCostOpen(false);
    }
  };
  const deleteCost = async (id) => {
    if (!window.confirm("Eliminare questo costo?")) return;
    await removeCostApi(id);
    toast.success("Costo eliminato");
  };

  // ---------- carico ----------
  const saveLoad = async (f) => {
    const payload = {
      ...f,
      client_id: f.client_id || null,
      order_id: f.order_id || null,
      quantity: f.quantity ? parseFloat(f.quantity) : null,
      colli: f.colli ? parseInt(f.colli, 10) : null,
      peso: f.peso ? parseFloat(f.peso) : null,
    };
    if (loadEditTarget) {
      await updateLoadApi(loadEditTarget.id, payload);
      toast.success("Carico aggiornato");
      setLoadEditTarget(null);
    } else {
      await createLoadApi(payload);
      toast.success("Carico aggiunto");
      setLoadOpen(false);
    }
  };
  const deleteLoad = async (id) => {
    if (!window.confirm("Eliminare questo carico?")) return;
    await removeLoadApi(id);
    toast.success("Carico eliminato");
  };

  return (
    <div className="p-4 md:p-8">
      <div className="flex items-end justify-between border-b border-[#E4E4E1] pb-6 mb-6 flex-wrap gap-3">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#B23E00] mb-2">Gestione Flotta</div>
          <h1 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight">Flotta</h1>
        </div>
      </div>

      <div className="flex items-center gap-1 mb-6 border-b border-[#E4E4E1] overflow-x-auto">
        {[
          ["mezzi", "Mezzi", Truck, 0],
          ["scadenze", "Scadenze", CalendarClock, overdueCount + upcomingCount],
          ["costi", "Costi", Coins, 0],
          ["carico", "Carico merce", Package, 0],
        ].map(([key, label, Icon, badge]) => (
          <button key={key} onClick={() => setTab(key)}
            className={`flex items-center gap-1.5 px-3 py-2.5 text-[13px] font-medium whitespace-nowrap border-b-2 -mb-px transition-colors ${
              tab === key ? "border-[#B23E00] text-[#0A192F]" : "border-transparent text-[#6B6B72] hover:text-[#52525B]"
            }`}>
            <Icon className="w-3.5 h-3.5" /> {label}
            {badge > 0 && <span className="ml-1 px-1.5 py-0.5 rounded-full bg-[#B23E00] text-white text-[10px] font-bold">{badge}</span>}
          </button>
        ))}
      </div>

      {tab === "mezzi" && (
        <MezziTab
          vehicles={vehicles} filteredVehicles={filteredVehicles} employees={employees}
          vehicleSearch={vehicleSearch} setVehicleSearch={setVehicleSearch}
          vehicleFilter={vehicleFilter} setVehicleFilter={setVehicleFilter}
          vehicleOpen={vehicleOpen} setVehicleOpen={setVehicleOpen}
          vehicleEditTarget={vehicleEditTarget} setVehicleEditTarget={setVehicleEditTarget}
          saveVehicle={saveVehicle} toggleVehicleActive={toggleVehicleActive} deleteVehicle={deleteVehicle}
          emptyVehicle={EMPTY_VEHICLE}
        />
      )}

      {tab === "scadenze" && (
        <ScadenzeTab
          deadlines={deadlines} activeVehicles={activeVehicles} automazioniEnabled={automazioniEnabled}
          reminderDays={reminderDays} toggleReminderDay={toggleReminderDay}
          deadlineOpen={deadlineOpen} setDeadlineOpen={setDeadlineOpen}
          deadlineEditTarget={deadlineEditTarget} setDeadlineEditTarget={setDeadlineEditTarget}
          saveDeadline={saveDeadline} deleteDeadline={deleteDeadline}
          emptyDeadline={EMPTY_DEADLINE}
        />
      )}

      {tab === "costi" && (
        <CostiTab
          costs={costs} activeVehicles={activeVehicles} totalCosts={totalCosts}
          costOpen={costOpen} setCostOpen={setCostOpen}
          costEditTarget={costEditTarget} setCostEditTarget={setCostEditTarget}
          saveCost={saveCost} deleteCost={deleteCost}
          emptyCost={EMPTY_COST}
        />
      )}

      {tab === "carico" && (
        <CaricoTab
          loads={loads} activeVehicles={activeVehicles} clients={clients} orders={orders}
          loadOpen={loadOpen} setLoadOpen={setLoadOpen}
          loadEditTarget={loadEditTarget} setLoadEditTarget={setLoadEditTarget}
          signTarget={signTarget} setSignTarget={setSignTarget}
          saveLoad={saveLoad} deleteLoad={deleteLoad} signLoad={signLoad}
          emptyLoad={EMPTY_LOAD}
        />
      )}
    </div>
  );
}

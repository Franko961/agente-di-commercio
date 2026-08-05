import { useEffect, useState } from "react";
import {
  Plus, Trash2, Pencil, Truck, CalendarClock, Coins, Package,
  Power, PowerOff, AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";
import api from "../api";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../components/ui/dialog";

const VEHICLE_TYPE_LABELS = { furgone: "Furgone", camion: "Camion", auto: "Auto", altro: "Altro" };
const DEADLINE_TYPE_LABELS = { assicurazione: "Assicurazione", revisione: "Revisione", bollo: "Bollo", altro: "Altro" };
const COST_CATEGORY_LABELS = { carburante: "Carburante", manutenzione: "Manutenzione", riparazione: "Riparazione", altro: "Altro" };

const EMPTY_VEHICLE = { plate: "", model: "", type: "furgone", assigned_driver: "", notes: "" };
const EMPTY_DEADLINE = { vehicle_id: "", type: "assicurazione", due_date: "", note: "" };
const EMPTY_COST = { vehicle_id: "", category: "carburante", amount: "", date: "", description: "" };
const EMPTY_LOAD = { vehicle_id: "", date: "", description: "", destination: "", notes: "" };

const fmtEuro = (n) => new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(n || 0);

function daysUntil(dateStr) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(dateStr);
  return Math.round((target - today) / (1000 * 60 * 60 * 24));
}

function deadlineUrgency(days) {
  if (days < 0) return { color: "#DC2626", label: `Scaduta da ${Math.abs(days)} giorni` };
  if (days === 0) return { color: "#DC2626", label: "Scade oggi" };
  if (days <= 30) return { color: "#FF5A00", label: `Scade tra ${days} giorni` };
  return { color: "#52525B", label: `Scade tra ${days} giorni` };
}

export default function Flotta() {
  const [tab, setTab] = useState("mezzi"); // mezzi | scadenze | costi | carico
  const [vehicles, setVehicles] = useState([]);
  const [deadlines, setDeadlines] = useState([]);
  const [costs, setCosts] = useState([]);
  const [loads, setLoads] = useState([]);

  const [vehicleOpen, setVehicleOpen] = useState(false);
  const [vehicleEditTarget, setVehicleEditTarget] = useState(null);
  const [deadlineOpen, setDeadlineOpen] = useState(false);
  const [deadlineEditTarget, setDeadlineEditTarget] = useState(null);
  const [costOpen, setCostOpen] = useState(false);
  const [costEditTarget, setCostEditTarget] = useState(null);
  const [loadOpen, setLoadOpen] = useState(false);
  const [loadEditTarget, setLoadEditTarget] = useState(null);

  const loadVehicles = async () => { const { data } = await api.get("/vehicles"); setVehicles(data); };
  const loadDeadlines = async () => { const { data } = await api.get("/vehicle-deadlines"); setDeadlines(data); };
  const loadCosts = async () => { const { data } = await api.get("/vehicle-costs"); setCosts(data); };
  const loadLoads = async () => { const { data } = await api.get("/cargo-loads"); setLoads(data); };

  useEffect(() => { loadVehicles(); loadDeadlines(); loadCosts(); loadLoads(); }, []);

  const activeVehicles = vehicles.filter((v) => v.active);
  const overdueCount = deadlines.filter((d) => daysUntil(d.due_date) < 0).length;
  const upcomingCount = deadlines.filter((d) => { const days = daysUntil(d.due_date); return days >= 0 && days <= 30; }).length;
  const totalCosts = costs.reduce((sum, c) => sum + c.amount, 0);

  // ---------- mezzi ----------
  const saveVehicle = async (f) => {
    if (vehicleEditTarget) {
      await api.put(`/vehicles/${vehicleEditTarget.id}`, f);
      toast.success("Mezzo aggiornato");
      setVehicleEditTarget(null);
    } else {
      await api.post("/vehicles", f);
      toast.success("Mezzo aggiunto");
      setVehicleOpen(false);
    }
    loadVehicles();
  };
  const toggleVehicleActive = async (v) => {
    await api.patch(`/vehicles/${v.id}/active`, { active: !v.active });
    toast.success(v.active ? "Mezzo disattivato" : "Mezzo riattivato");
    loadVehicles();
  };
  const deleteVehicle = async (v) => {
    if (!window.confirm(`Eliminare "${v.plate}"? Scadenze, costi e carichi già registrati restano nello storico. Se vuoi solo toglierlo dalla flotta attiva, puoi disattivarlo invece.`)) return;
    await api.delete(`/vehicles/${v.id}`);
    toast.success("Mezzo eliminato");
    loadVehicles();
  };

  // ---------- scadenze ----------
  const saveDeadline = async (f) => {
    const payload = { ...f };
    if (deadlineEditTarget) {
      await api.put(`/vehicle-deadlines/${deadlineEditTarget.id}`, payload);
      toast.success("Scadenza aggiornata");
      setDeadlineEditTarget(null);
    } else {
      await api.post("/vehicle-deadlines", payload);
      toast.success("Scadenza aggiunta");
      setDeadlineOpen(false);
    }
    loadDeadlines();
  };
  const deleteDeadline = async (id) => {
    if (!window.confirm("Eliminare questa scadenza?")) return;
    await api.delete(`/vehicle-deadlines/${id}`);
    toast.success("Scadenza eliminata");
    loadDeadlines();
  };

  // ---------- costi ----------
  const saveCost = async (f) => {
    const payload = { ...f, amount: parseFloat(f.amount) };
    if (costEditTarget) {
      await api.put(`/vehicle-costs/${costEditTarget.id}`, payload);
      toast.success("Costo aggiornato");
      setCostEditTarget(null);
    } else {
      await api.post("/vehicle-costs", payload);
      toast.success("Costo aggiunto");
      setCostOpen(false);
    }
    loadCosts();
  };
  const deleteCost = async (id) => {
    if (!window.confirm("Eliminare questo costo?")) return;
    await api.delete(`/vehicle-costs/${id}`);
    toast.success("Costo eliminato");
    loadCosts();
  };

  // ---------- carico ----------
  const saveLoad = async (f) => {
    if (loadEditTarget) {
      await api.put(`/cargo-loads/${loadEditTarget.id}`, f);
      toast.success("Carico aggiornato");
      setLoadEditTarget(null);
    } else {
      await api.post("/cargo-loads", f);
      toast.success("Carico aggiunto");
      setLoadOpen(false);
    }
    loadLoads();
  };
  const deleteLoad = async (id) => {
    if (!window.confirm("Eliminare questo carico?")) return;
    await api.delete(`/cargo-loads/${id}`);
    toast.success("Carico eliminato");
    loadLoads();
  };

  return (
    <div className="p-4 md:p-8">
      <div className="flex items-end justify-between border-b border-[#E4E4E1] pb-6 mb-6 flex-wrap gap-3">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00] mb-2">Gestione Flotta</div>
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
              tab === key ? "border-[#FF5A00] text-[#0A192F]" : "border-transparent text-[#A1A1AA] hover:text-[#52525B]"
            }`}>
            <Icon className="w-3.5 h-3.5" /> {label}
            {badge > 0 && <span className="ml-1 px-1.5 py-0.5 rounded-full bg-[#FF5A00] text-white text-[10px] font-bold">{badge}</span>}
          </button>
        ))}
      </div>

      {tab === "mezzi" && (
        <div>
          <div className="flex justify-end mb-4">
            <Dialog open={vehicleOpen} onOpenChange={setVehicleOpen}>
              <DialogTrigger asChild>
                <button className="flex items-center gap-2 px-4 py-2.5 bg-[#0A192F] text-white rounded-md text-[13px] font-medium">
                  <Plus className="w-4 h-4" /> Nuovo mezzo
                </button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader><DialogTitle>Nuovo mezzo</DialogTitle></DialogHeader>
                <VehicleForm initial={EMPTY_VEHICLE} onSave={saveVehicle} />
              </DialogContent>
            </Dialog>
          </div>
          <Dialog open={!!vehicleEditTarget} onOpenChange={(v) => !v && setVehicleEditTarget(null)}>
            <DialogContent>
              <DialogHeader><DialogTitle>Modifica mezzo</DialogTitle></DialogHeader>
              {vehicleEditTarget && <VehicleForm initial={vehicleEditTarget} onSave={saveVehicle} submitLabel="Aggiorna" />}
            </DialogContent>
          </Dialog>

          <div className="space-y-2">
            {vehicles.map((v) => (
              <div key={v.id} className="bg-white border border-[#E4E4E1] rounded-md p-4 flex items-center justify-between gap-3 flex-wrap">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-cabinet font-bold text-[14px]">{v.plate}</span>
                    <span className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA]">{VEHICLE_TYPE_LABELS[v.type]}</span>
                    {!v.active && (
                      <span className="font-mono text-[10px] uppercase tracking-widest px-1.5 py-0.5 rounded-full bg-[#F3F3F1] text-[#A1A1AA]">Disattivato</span>
                    )}
                  </div>
                  <div className="text-[12px] text-[#52525B]">{v.model || "—"}{v.assigned_driver ? ` · Assegnato a ${v.assigned_driver}` : ""}</div>
                  {v.notes && <div className="text-[12px] text-[#A1A1AA] mt-0.5 italic">{v.notes}</div>}
                </div>
                <div className="flex gap-1">
                  <button onClick={() => toggleVehicleActive(v)} title={v.active ? "Disattiva" : "Riattiva"} aria-label={v.active ? "Disattiva mezzo" : "Riattiva mezzo"}
                    className="p-1.5 text-[#A1A1AA] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded">
                    {v.active ? <Power className="w-4 h-4" /> : <PowerOff className="w-4 h-4" />}
                  </button>
                  <button onClick={() => setVehicleEditTarget(v)} title="Modifica" aria-label="Modifica mezzo"
                    className="p-1.5 text-[#A1A1AA] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded"><Pencil className="w-4 h-4" /></button>
                  <button onClick={() => deleteVehicle(v)} title="Elimina" aria-label="Elimina mezzo"
                    className="p-1.5 text-[#A1A1AA] hover:text-red-500 hover:bg-red-50 rounded"><Trash2 className="w-4 h-4" /></button>
                </div>
              </div>
            ))}
            {vehicles.length === 0 && (
              <div className="bg-white border border-[#E4E4E1] rounded-md p-8 text-center text-[#A1A1AA] text-[13px]">Nessun mezzo ancora registrato.</div>
            )}
          </div>
        </div>
      )}

      {tab === "scadenze" && (
        <div>
          <div className="flex justify-end mb-4">
            <Dialog open={deadlineOpen} onOpenChange={setDeadlineOpen}>
              <DialogTrigger asChild>
                <button className="flex items-center gap-2 px-4 py-2.5 bg-[#0A192F] text-white rounded-md text-[13px] font-medium">
                  <Plus className="w-4 h-4" /> Nuova scadenza
                </button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader><DialogTitle>Nuova scadenza</DialogTitle></DialogHeader>
                <DeadlineForm initial={EMPTY_DEADLINE} vehicles={activeVehicles} onSave={saveDeadline} />
              </DialogContent>
            </Dialog>
          </div>
          <Dialog open={!!deadlineEditTarget} onOpenChange={(v) => !v && setDeadlineEditTarget(null)}>
            <DialogContent>
              <DialogHeader><DialogTitle>Modifica scadenza</DialogTitle></DialogHeader>
              {deadlineEditTarget && <DeadlineForm initial={deadlineEditTarget} vehicles={activeVehicles} onSave={saveDeadline} submitLabel="Aggiorna" />}
            </DialogContent>
          </Dialog>

          <div className="space-y-2">
            {deadlines.map((d) => {
              const days = daysUntil(d.due_date);
              const urgency = deadlineUrgency(days);
              return (
                <div key={d.id} className="bg-white border border-[#E4E4E1] rounded-md p-4 flex items-center justify-between gap-3 flex-wrap">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-cabinet font-bold text-[14px]">{d.vehicle_plate}</span>
                      <span className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA]">{DEADLINE_TYPE_LABELS[d.type]}</span>
                    </div>
                    <div className="text-[12px] text-[#52525B] mt-1">{d.due_date}</div>
                    {d.note && <div className="text-[12px] text-[#52525B] mt-1 italic">"{d.note}"</div>}
                    <div className="flex items-center gap-1.5 mt-1.5 text-[12px] font-medium" style={{ color: urgency.color }}>
                      {days < 0 && <AlertTriangle className="w-3.5 h-3.5 shrink-0" />}
                      {urgency.label}
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <button onClick={() => setDeadlineEditTarget(d)} title="Modifica" aria-label="Modifica scadenza"
                      className="p-1.5 text-[#A1A1AA] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded"><Pencil className="w-4 h-4" /></button>
                    <button onClick={() => deleteDeadline(d.id)} title="Elimina" aria-label="Elimina scadenza"
                      className="p-1.5 text-[#A1A1AA] hover:text-red-500 hover:bg-red-50 rounded"><Trash2 className="w-4 h-4" /></button>
                  </div>
                </div>
              );
            })}
            {deadlines.length === 0 && (
              <div className="bg-white border border-[#E4E4E1] rounded-md p-8 text-center text-[#A1A1AA] text-[13px]">Nessuna scadenza registrata.</div>
            )}
          </div>
        </div>
      )}

      {tab === "costi" && (
        <div>
          <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
            <div className="text-[13px] text-[#52525B]">Totale: <span className="font-cabinet font-bold text-[15px] text-[#0A192F]">{fmtEuro(totalCosts)}</span></div>
            <Dialog open={costOpen} onOpenChange={setCostOpen}>
              <DialogTrigger asChild>
                <button className="flex items-center gap-2 px-4 py-2.5 bg-[#0A192F] text-white rounded-md text-[13px] font-medium">
                  <Plus className="w-4 h-4" /> Nuovo costo
                </button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader><DialogTitle>Nuovo costo</DialogTitle></DialogHeader>
                <CostForm initial={EMPTY_COST} vehicles={activeVehicles} onSave={saveCost} />
              </DialogContent>
            </Dialog>
          </div>
          <Dialog open={!!costEditTarget} onOpenChange={(v) => !v && setCostEditTarget(null)}>
            <DialogContent>
              <DialogHeader><DialogTitle>Modifica costo</DialogTitle></DialogHeader>
              {costEditTarget && <CostForm initial={{ ...costEditTarget, amount: String(costEditTarget.amount) }} vehicles={activeVehicles} onSave={saveCost} submitLabel="Aggiorna" />}
            </DialogContent>
          </Dialog>

          <div className="space-y-2">
            {costs.map((c) => (
              <div key={c.id} className="bg-white border border-[#E4E4E1] rounded-md p-4 flex items-center justify-between gap-3 flex-wrap">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-cabinet font-bold text-[14px]">{c.vehicle_plate}</span>
                    <span className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA]">{COST_CATEGORY_LABELS[c.category]}</span>
                  </div>
                  <div className="text-[12px] text-[#52525B] mt-1">{c.date}{c.description ? ` · ${c.description}` : ""}</div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="font-cabinet font-bold text-[15px]">{fmtEuro(c.amount)}</span>
                  <div className="flex gap-1">
                    <button onClick={() => setCostEditTarget(c)} title="Modifica" aria-label="Modifica costo"
                      className="p-1.5 text-[#A1A1AA] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded"><Pencil className="w-4 h-4" /></button>
                    <button onClick={() => deleteCost(c.id)} title="Elimina" aria-label="Elimina costo"
                      className="p-1.5 text-[#A1A1AA] hover:text-red-500 hover:bg-red-50 rounded"><Trash2 className="w-4 h-4" /></button>
                  </div>
                </div>
              </div>
            ))}
            {costs.length === 0 && (
              <div className="bg-white border border-[#E4E4E1] rounded-md p-8 text-center text-[#A1A1AA] text-[13px]">Nessun costo ancora registrato.</div>
            )}
          </div>
        </div>
      )}

      {tab === "carico" && (
        <div>
          <div className="flex justify-end mb-4">
            <Dialog open={loadOpen} onOpenChange={setLoadOpen}>
              <DialogTrigger asChild>
                <button className="flex items-center gap-2 px-4 py-2.5 bg-[#0A192F] text-white rounded-md text-[13px] font-medium">
                  <Plus className="w-4 h-4" /> Nuovo carico
                </button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader><DialogTitle>Nuovo carico</DialogTitle></DialogHeader>
                <LoadForm initial={EMPTY_LOAD} vehicles={activeVehicles} onSave={saveLoad} />
              </DialogContent>
            </Dialog>
          </div>
          <Dialog open={!!loadEditTarget} onOpenChange={(v) => !v && setLoadEditTarget(null)}>
            <DialogContent>
              <DialogHeader><DialogTitle>Modifica carico</DialogTitle></DialogHeader>
              {loadEditTarget && <LoadForm initial={loadEditTarget} vehicles={activeVehicles} onSave={saveLoad} submitLabel="Aggiorna" />}
            </DialogContent>
          </Dialog>

          <div className="space-y-2">
            {loads.map((l) => (
              <div key={l.id} className="bg-white border border-[#E4E4E1] rounded-md p-4 flex items-center justify-between gap-3 flex-wrap">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-cabinet font-bold text-[14px]">{l.vehicle_plate}</span>
                    <span className="text-[12px] text-[#52525B]">{l.date}</span>
                  </div>
                  <div className="text-[13px] mt-1">{l.description}</div>
                  {l.destination && <div className="text-[12px] text-[#52525B] mt-0.5">Destinazione: {l.destination}</div>}
                  {l.notes && <div className="text-[12px] text-[#A1A1AA] mt-0.5 italic">{l.notes}</div>}
                </div>
                <div className="flex gap-1">
                  <button onClick={() => setLoadEditTarget(l)} title="Modifica" aria-label="Modifica carico"
                    className="p-1.5 text-[#A1A1AA] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded"><Pencil className="w-4 h-4" /></button>
                  <button onClick={() => deleteLoad(l.id)} title="Elimina" aria-label="Elimina carico"
                    className="p-1.5 text-[#A1A1AA] hover:text-red-500 hover:bg-red-50 rounded"><Trash2 className="w-4 h-4" /></button>
                </div>
              </div>
            ))}
            {loads.length === 0 && (
              <div className="bg-white border border-[#E4E4E1] rounded-md p-8 text-center text-[#A1A1AA] text-[13px]">Nessun carico ancora registrato.</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function VehicleForm({ initial, onSave, submitLabel = "Salva" }) {
  const [f, setF] = useState({
    plate: initial.plate, model: initial.model || "", type: initial.type || "furgone",
    assigned_driver: initial.assigned_driver || "", notes: initial.notes || "",
  });
  return (
    <form onSubmit={async (e) => { e.preventDefault(); await onSave(f); }} className="space-y-3">
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Targa *</label>
        <input required value={f.plate} onChange={(e) => setF({ ...f, plate: e.target.value.toUpperCase() })}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Modello</label>
        <input value={f.model} onChange={(e) => setF({ ...f, model: e.target.value })}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Tipo</label>
        <select value={f.type} onChange={(e) => setF({ ...f, type: e.target.value })}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
          {Object.entries(VEHICLE_TYPE_LABELS).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
        </select>
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Assegnato a (opzionale)</label>
        <input value={f.assigned_driver} onChange={(e) => setF({ ...f, assigned_driver: e.target.value })}
          placeholder="Nome del dipendente/autista"
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Note</label>
        <textarea value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} rows={2}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      </div>
      <button type="submit" className="w-full bg-[#0A192F] text-white py-2.5 rounded-md text-[13px] font-medium">{submitLabel}</button>
    </form>
  );
}

function DeadlineForm({ initial, vehicles, onSave, submitLabel = "Salva" }) {
  const [f, setF] = useState({
    vehicle_id: initial.vehicle_id || (vehicles[0]?.id || ""), type: initial.type || "assicurazione",
    due_date: initial.due_date || "", note: initial.note || "",
  });
  return (
    <form onSubmit={async (e) => { e.preventDefault(); await onSave(f); }} className="space-y-3">
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Mezzo *</label>
        <select required value={f.vehicle_id} onChange={(e) => setF({ ...f, vehicle_id: e.target.value })}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
          <option value="" disabled>Seleziona un mezzo</option>
          {vehicles.map((v) => <option key={v.id} value={v.id}>{v.plate}{v.model ? ` — ${v.model}` : ""}</option>)}
        </select>
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Tipo *</label>
        <select value={f.type} onChange={(e) => setF({ ...f, type: e.target.value })}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
          {Object.entries(DEADLINE_TYPE_LABELS).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
        </select>
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Scadenza *</label>
        <input required type="date" value={f.due_date} onChange={(e) => setF({ ...f, due_date: e.target.value })}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Note</label>
        <textarea value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} rows={2}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      </div>
      <button type="submit" className="w-full bg-[#0A192F] text-white py-2.5 rounded-md text-[13px] font-medium">{submitLabel}</button>
    </form>
  );
}

function CostForm({ initial, vehicles, onSave, submitLabel = "Salva" }) {
  const [f, setF] = useState({
    vehicle_id: initial.vehicle_id || (vehicles[0]?.id || ""), category: initial.category || "carburante",
    amount: initial.amount || "", date: initial.date || "", description: initial.description || "",
  });
  return (
    <form onSubmit={async (e) => { e.preventDefault(); await onSave(f); }} className="space-y-3">
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Mezzo *</label>
        <select required value={f.vehicle_id} onChange={(e) => setF({ ...f, vehicle_id: e.target.value })}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
          <option value="" disabled>Seleziona un mezzo</option>
          {vehicles.map((v) => <option key={v.id} value={v.id}>{v.plate}{v.model ? ` — ${v.model}` : ""}</option>)}
        </select>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Categoria *</label>
          <select value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })}
            className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
            {Object.entries(COST_CATEGORY_LABELS).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
          </select>
        </div>
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Importo (€) *</label>
          <input required type="number" step="0.01" min="0.01" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })}
            className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
        </div>
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Data *</label>
        <input required type="date" value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Descrizione</label>
        <textarea value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} rows={2}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      </div>
      <button type="submit" className="w-full bg-[#0A192F] text-white py-2.5 rounded-md text-[13px] font-medium">{submitLabel}</button>
    </form>
  );
}

function LoadForm({ initial, vehicles, onSave, submitLabel = "Salva" }) {
  const [f, setF] = useState({
    vehicle_id: initial.vehicle_id || (vehicles[0]?.id || ""), date: initial.date || "",
    description: initial.description || "", destination: initial.destination || "", notes: initial.notes || "",
  });
  return (
    <form onSubmit={async (e) => { e.preventDefault(); await onSave(f); }} className="space-y-3">
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Mezzo *</label>
        <select required value={f.vehicle_id} onChange={(e) => setF({ ...f, vehicle_id: e.target.value })}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
          <option value="" disabled>Seleziona un mezzo</option>
          {vehicles.map((v) => <option key={v.id} value={v.id}>{v.plate}{v.model ? ` — ${v.model}` : ""}</option>)}
        </select>
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Data *</label>
        <input required type="date" value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Descrizione carico *</label>
        <input required value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })}
          placeholder="Cosa viene trasportato"
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Destinazione</label>
        <input value={f.destination} onChange={(e) => setF({ ...f, destination: e.target.value })}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Note</label>
        <textarea value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} rows={2}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      </div>
      <button type="submit" className="w-full bg-[#0A192F] text-white py-2.5 rounded-md text-[13px] font-medium">{submitLabel}</button>
    </form>
  );
}

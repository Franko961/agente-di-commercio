import { useState } from "react";
import { Plus, Trash2, Pencil, Search, Power, PowerOff } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../ui/dialog";
import { VEHICLE_TYPE_LABELS, assignedLabel } from "./constants";

export default function MezziTab({
  vehicles, filteredVehicles, employees,
  vehicleSearch, setVehicleSearch, vehicleFilter, setVehicleFilter,
  vehicleOpen, setVehicleOpen, vehicleEditTarget, setVehicleEditTarget,
  saveVehicle, toggleVehicleActive, deleteVehicle, emptyVehicle,
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <div className="relative">
            <Search className="w-4 h-4 text-[#6B6B72] absolute left-3 top-1/2 -translate-y-1/2" />
            <input value={vehicleSearch} onChange={(e) => setVehicleSearch(e.target.value)}
              placeholder="Cerca per targa o modello"
              className="pl-9 pr-3 py-2.5 border border-[#E4E4E1] rounded-md text-[13px] w-56 focus:outline-none focus:border-[#0A192F]" />
          </div>
          <select value={vehicleFilter} onChange={(e) => setVehicleFilter(e.target.value)}
            className="px-3 py-2.5 border border-[#E4E4E1] rounded-md text-[13px]">
            <option value="all">Tutti i mezzi</option>
            <option value="active">Solo attivi</option>
            <option value="inactive">Solo disattivati</option>
          </select>
        </div>
        <Dialog open={vehicleOpen} onOpenChange={setVehicleOpen}>
          <DialogTrigger asChild>
            <button className="flex items-center gap-2 px-4 py-2.5 bg-[#0A192F] text-white rounded-md text-[13px] font-medium">
              <Plus className="w-4 h-4" /> Nuovo mezzo
            </button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Nuovo mezzo</DialogTitle></DialogHeader>
            <VehicleForm initial={emptyVehicle} employees={employees} onSave={saveVehicle} />
          </DialogContent>
        </Dialog>
      </div>
      <Dialog open={!!vehicleEditTarget} onOpenChange={(v) => !v && setVehicleEditTarget(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Modifica mezzo</DialogTitle></DialogHeader>
          {vehicleEditTarget && <VehicleForm initial={vehicleEditTarget} employees={employees} onSave={saveVehicle} submitLabel="Aggiorna" />}
        </DialogContent>
      </Dialog>

      <div className="space-y-2">
        {filteredVehicles.map((v) => (
          <div key={v.id} className="bg-white border border-[#E4E4E1] rounded-md p-4 flex items-center justify-between gap-3 flex-wrap">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-cabinet font-bold text-[14px]">{v.plate}</span>
                <span className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72]">{VEHICLE_TYPE_LABELS[v.type]}</span>
                {!v.active && (
                  <span className="font-mono text-[10px] uppercase tracking-widest px-1.5 py-0.5 rounded-full bg-[#F3F3F1] text-[#6B6B72]">Disattivato</span>
                )}
              </div>
              <div className="text-[12px] text-[#52525B]">{v.model || "—"}{assignedLabel(v, employees) ? ` · Assegnato a ${assignedLabel(v, employees)}` : ""}</div>
              {v.notes && <div className="text-[12px] text-[#6B6B72] mt-0.5 italic">{v.notes}</div>}
            </div>
            <div className="flex gap-1">
              <button onClick={() => toggleVehicleActive(v)} title={v.active ? "Disattiva" : "Riattiva"} aria-label={v.active ? "Disattiva mezzo" : "Riattiva mezzo"}
                className="p-1.5 text-[#6B6B72] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded">
                {v.active ? <Power className="w-4 h-4" /> : <PowerOff className="w-4 h-4" />}
              </button>
              <button onClick={() => setVehicleEditTarget(v)} title="Modifica" aria-label="Modifica mezzo"
                className="p-1.5 text-[#6B6B72] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded"><Pencil className="w-4 h-4" /></button>
              <button onClick={() => deleteVehicle(v)} title="Elimina" aria-label="Elimina mezzo"
                className="p-1.5 text-[#6B6B72] hover:text-red-500 hover:bg-red-50 rounded"><Trash2 className="w-4 h-4" /></button>
            </div>
          </div>
        ))}
        {filteredVehicles.length === 0 && (
          <div className="bg-white border border-[#E4E4E1] rounded-md p-8 text-center text-[#6B6B72] text-[13px]">
            {vehicles.length === 0 ? "Nessun mezzo ancora registrato." : "Nessun mezzo corrisponde alla ricerca."}
          </div>
        )}
      </div>
    </div>
  );
}

function VehicleForm({ initial, employees, onSave, submitLabel = "Salva" }) {
  const [f, setF] = useState({
    plate: initial.plate, model: initial.model || "", type: initial.type || "furgone",
    assigned_driver: initial.assigned_driver || "", assigned_employee_id: initial.assigned_employee_id || "",
    notes: initial.notes || "",
  });
  // La tendina (dipendenti reali, modulo Personale) sostituisce il campo di
  // testo libero quando ci sono dipendenti tra cui scegliere — altrimenti
  // (Personale disattivo, o nessun dipendente ancora censito) resta il
  // testo libero di sempre, così Flotta funziona anche da sola.
  const hasEmployees = employees && employees.length > 0;
  return (
    <form onSubmit={async (e) => { e.preventDefault(); await onSave({ ...f, assigned_employee_id: f.assigned_employee_id || null }); }} className="space-y-3">
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
        {hasEmployees ? (
          <select value={f.assigned_employee_id}
            onChange={(e) => setF({ ...f, assigned_employee_id: e.target.value, assigned_driver: "" })}
            className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
            <option value="">Nessuno</option>
            {employees.map((emp) => (
              <option key={emp.id} value={emp.id}>{`${emp.name} ${emp.surname || ""}`.trim()}</option>
            ))}
          </select>
        ) : (
          <input value={f.assigned_driver} onChange={(e) => setF({ ...f, assigned_driver: e.target.value })}
            placeholder="Nome del dipendente/autista"
            className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
        )}
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

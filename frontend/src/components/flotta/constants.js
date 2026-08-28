export const VEHICLE_TYPE_LABELS = { furgone: "Furgone", camion: "Camion", auto: "Auto", altro: "Altro" };
export const DEADLINE_TYPE_LABELS = { assicurazione: "Assicurazione", revisione: "Revisione", bollo: "Bollo", altro: "Altro" };
export const COST_CATEGORY_LABELS = { carburante: "Carburante", manutenzione: "Manutenzione", riparazione: "Riparazione", altro: "Altro" };
export const CARGO_STATUS_LABELS = { programmato: "Programmato", in_transito: "In transito", consegnato: "Consegnato", non_consegnato: "Non consegnato" };
export const CARGO_STATUS_COLORS = { programmato: "#52525B", in_transito: "#B23E00", consegnato: "#059669", non_consegnato: "#DC2626" };
export const REMINDER_DAY_OPTIONS = [7, 15, 30];

export const EMPTY_VEHICLE = { plate: "", model: "", type: "furgone", assigned_driver: "", notes: "" };
export const EMPTY_DEADLINE = { vehicle_id: "", type: "assicurazione", due_date: "", note: "" };
export const EMPTY_COST = { vehicle_id: "", category: "carburante", amount: "", date: "", description: "" };
export const EMPTY_LOAD = {
  vehicle_id: "", date: "", description: "", destination: "", notes: "",
  client_id: "", order_id: "", quantity: "", colli: "", peso: "", status: "programmato",
};

export const fmtEuro = (n) => new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(n || 0);

// Se il mezzo è collegato a un dipendente vero (modulo Personale), mostra il
// suo nome invece del testo libero assigned_driver — i due sono alternativi,
// non sommati (vedi VehicleForm: la tendina sostituisce il campo testo
// libero quando ci sono dipendenti disponibili).
export function assignedLabel(vehicle, employees) {
  if (vehicle.assigned_employee_id) {
    const emp = employees.find((e) => e.id === vehicle.assigned_employee_id);
    if (emp) return `${emp.name} ${emp.surname || ""}`.trim();
  }
  return vehicle.assigned_driver || "";
}

export function daysUntil(dateStr) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(dateStr);
  return Math.round((target - today) / (1000 * 60 * 60 * 24));
}

export function deadlineUrgency(days) {
  if (days < 0) return { color: "#DC2626", label: `Scaduta da ${Math.abs(days)} giorni` };
  if (days === 0) return { color: "#DC2626", label: "Scade oggi" };
  if (days <= 30) return { color: "#B23E00", label: `Scade tra ${days} giorni` };
  return { color: "#52525B", label: `Scade tra ${days} giorni` };
}

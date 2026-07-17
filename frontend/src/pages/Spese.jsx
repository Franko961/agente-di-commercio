import { useEffect, useMemo, useState } from "react";
import api from "../api";
import { Plus, Trash2, Pencil, Fuel, UtensilsCrossed, BedDouble, ParkingCircle, Package, Receipt, Landmark, PiggyBank, Car, Calculator } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../components/ui/dialog";
import { toast } from "sonner";

const fmt = (n) => new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(n || 0);
const todayIso = () => new Date().toISOString().slice(0, 10);

const CATEGORIES = [
  { value: "carburante", label: "Carburante", icon: Fuel },
  { value: "vitto", label: "Vitto", icon: UtensilsCrossed },
  { value: "alloggio", label: "Alloggio", icon: BedDouble },
  { value: "pedaggio_parcheggio", label: "Pedaggio/Parcheggio", icon: ParkingCircle },
  { value: "materiali", label: "Materiali", icon: Package },
  { value: "inps", label: "INPS", icon: Landmark },
  { value: "enasarco", label: "ENASARCO", icon: PiggyBank },
  { value: "assicurazione_auto", label: "Assicurazione auto", icon: Car },
  { value: "commercialista", label: "Commercialista", icon: Calculator },
  { value: "altro", label: "Altro", icon: Receipt },
];
const catMeta = (value) => CATEGORIES.find((c) => c.value === value) || CATEGORIES[CATEGORIES.length - 1];

const EMPTY = { date: todayIso(), category: "carburante", description: "", amount: 0, notes: "" };

export default function Spese() {
  const [expenses, setExpenses] = useState([]);
  const [open, setOpen] = useState(false);
  const [editTarget, setEditTarget] = useState(null);
  const [filter, setFilter] = useState("");

  const load = async () => {
    const { data } = await api.get("/expenses", { params: filter ? { category: filter } : {} });
    setExpenses(data);
  };
  useEffect(() => { load(); }, [filter]);

  const deleteExpense = async (id, desc) => {
    if (!window.confirm(`Eliminare la spesa "${desc || "senza descrizione"}"?`)) return;
    await api.delete(`/expenses/${id}`);
    toast.success("Spesa eliminata");
    load();
  };

  const total = useMemo(() => expenses.reduce((sum, e) => sum + (e.amount || 0), 0), [expenses]);

  return (
    <div className="p-4 md:p-8">
      <div className="flex items-end justify-between border-b border-[#E4E4E1] pb-6 mb-6">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00] mb-2">Note spese</div>
          <h1 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight">Spese</h1>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <button data-testid="new-expense-button" className="flex items-center gap-2 px-4 py-2.5 bg-[#0A192F] text-white rounded-md text-[13px] font-medium">
              <Plus className="w-4 h-4" /> Nuova spesa
            </button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Nuova spesa</DialogTitle></DialogHeader>
            <ExpenseForm initial={EMPTY} onSave={async (f) => { await api.post("/expenses", f); load(); toast.success("Spesa registrata"); setOpen(false); }} />
          </DialogContent>
        </Dialog>
      </div>

      {/* Dialog modifica */}
      <Dialog open={!!editTarget} onOpenChange={(v) => !v && setEditTarget(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Modifica spesa</DialogTitle></DialogHeader>
          {editTarget && (
            <ExpenseForm initial={editTarget} submitLabel="Aggiorna" onSave={async (f) => {
              await api.put(`/expenses/${editTarget.id}`, f);
              load(); toast.success("Spesa aggiornata"); setEditTarget(null);
            }} />
          )}
        </DialogContent>
      </Dialog>

      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="flex gap-2 overflow-x-auto">
          <button onClick={() => setFilter("")} className={`px-3 py-1.5 rounded-md text-[12px] font-medium whitespace-nowrap ${filter === "" ? "bg-[#0A192F] text-white" : "bg-white border border-[#E4E4E1]"}`}>Tutte</button>
          {CATEGORIES.map((c) => (
            <button key={c.value} onClick={() => setFilter(c.value)} className={`px-3 py-1.5 rounded-md text-[12px] font-medium whitespace-nowrap flex items-center gap-1.5 ${filter === c.value ? "bg-[#0A192F] text-white" : "bg-white border border-[#E4E4E1]"}`}>
              <c.icon className="w-3.5 h-3.5" />{c.label}
            </button>
          ))}
        </div>
        <div className="font-mono text-[11px] uppercase tracking-widest text-[#52525B]">
          Totale: <span className="font-cabinet font-black text-[15px] text-[#0A0A0A]">{fmt(total)}</span>
        </div>
      </div>

      <div className="bg-white border border-[#E4E4E1] rounded-md overflow-hidden">
        <div className="hidden md:grid grid-cols-7 gap-2 px-4 py-3 bg-[#F3F3F1] border-b border-[#E4E4E1] font-mono text-[10px] uppercase tracking-widest text-[#52525B]">
          <div>Data</div><div>Categoria</div><div className="col-span-2">Descrizione</div><div className="text-right">Importo</div><div className="col-span-2"></div>
        </div>
        {expenses.map((e) => {
          const meta = catMeta(e.category);
          return (
            <div key={e.id} data-testid={`expense-${e.id}`} className="grid grid-cols-2 md:grid-cols-7 gap-2 px-4 py-3 border-b border-[#E4E4E1] items-center text-[13px]">
              <div className="font-mono text-[12px]">{e.date}</div>
              <div className="text-[#52525B] flex items-center gap-1.5">
                <meta.icon className="w-3.5 h-3.5 text-[#A1A1AA]" />{meta.label}
              </div>
              <div className="col-span-2 truncate">{e.description || "—"}</div>
              <div className="text-right font-cabinet font-bold">{fmt(e.amount)}</div>
              <div className="col-span-2 flex justify-end gap-1">
                <button onClick={() => setEditTarget(e)} className="p-1.5 text-[#A1A1AA] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded transition-colors" title="Modifica">
                  <Pencil className="w-4 h-4" />
                </button>
                <button onClick={() => deleteExpense(e.id, e.description)} className="p-1.5 text-[#A1A1AA] hover:text-red-500 hover:bg-red-50 rounded transition-colors" title="Elimina">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          );
        })}
        {expenses.length === 0 && <div className="p-8 text-center text-[#A1A1AA] text-[13px]">Nessuna spesa registrata.</div>}
      </div>
    </div>
  );
}

function ExpenseForm({ initial, onSave, submitLabel = "Salva" }) {
  const [f, setF] = useState(initial);
  useEffect(() => { setF(initial); }, [initial]);
  return (
    <form onSubmit={async (e) => { e.preventDefault(); await onSave(f); }} className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <Field label="Data *" v={f.date} on={(v) => setF({ ...f, date: v })} type="date" required />
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Categoria *</label>
          <select required value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })}
            className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
            {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
        </div>
      </div>
      <Field label="Descrizione" v={f.description} on={(v) => setF({ ...f, description: v })} />
      <Field label="Importo (€) *" v={f.amount} on={(v) => setF({ ...f, amount: parseFloat(v) || 0 })} type="number" required />
      <Field label="Note" v={f.notes} on={(v) => setF({ ...f, notes: v })} />
      <button data-testid="save-expense-button" type="submit" className="w-full bg-[#0A192F] text-white py-2.5 rounded-md text-[13px] font-medium">{submitLabel}</button>
    </form>
  );
}

function Field({ label, v, on, type = "text", required }) {
  return (
    <div>
      <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">{label}</label>
      <input type={type} required={required} value={v ?? ""} onChange={(e) => on(e.target.value)}
        className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" step={type === "number" ? "0.01" : undefined} />
    </div>
  );
}

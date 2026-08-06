import { useEffect, useMemo, useState, useRef } from "react";
import api from "../api";
import { Plus, Trash2, Pencil, Fuel, UtensilsCrossed, BedDouble, ParkingCircle, Package, Receipt, Landmark, PiggyBank, Car, Calculator, Paperclip, Upload, X, Loader2, ChevronDown } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../components/ui/dialog";
import { toast } from "sonner";

const fmt = (n) => new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(n || 0);
// Data di calendario locale, non new Date().toISOString().slice(0,10): quel
// metodo legge anno/mese/giorno in UTC, che nell'ultima/prima ora o due del
// giorno locale (a seconda del fuso) può differire dalla data dell'utente —
// usato solo per default di UI (data nuova spesa, mese aperto di default),
// mai per salvare timestamp.
const todayIso = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
};
const FILE_BASE = process.env.REACT_APP_BACKEND_URL;

async function downloadReceipt(documentId, label) {
  try {
    const res = await fetch(`${FILE_BASE}/api/documents/${documentId}/download`, { credentials: "include" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    window.open(url, "_blank");
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  } catch (e) {
    toast.error("Errore apertura scontrino");
  }
}

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

const emptyExpense = () => ({ date: todayIso(), category: "carburante", description: "", amount: 0, notes: "", receipt_document_id: null, receipt_filename: null });

// Raggruppa le spese per mese ("YYYY-MM" da e.date, già in quel formato):
// il mese in corso resta aperto di default (si sta ancora costruendo), i
// mesi passati partono chiusi mostrando solo il totale — l'elenco intero
// di ogni mese si apre cliccandoci sopra, invece di restare tutto
// visibile insieme man mano che passano i mesi.
const monthKey = (dateStr) => (dateStr || "").slice(0, 7);

function monthLabel(key) {
  const [y, m] = key.split("-").map(Number);
  const label = new Intl.DateTimeFormat("it-IT", { month: "long", year: "numeric" }).format(new Date(y, m - 1, 1));
  return label.charAt(0).toUpperCase() + label.slice(1);
}

function groupByMonth(list) {
  const byKey = new Map();
  for (const e of list) {
    const key = monthKey(e.date);
    if (!byKey.has(key)) byKey.set(key, []);
    byKey.get(key).push(e);
  }
  return [...byKey.entries()]
    .sort((a, b) => (a[0] < b[0] ? 1 : -1))
    .map(([key, items]) => ({
      key,
      label: monthLabel(key),
      items,
      total: items.reduce((sum, e) => sum + (e.amount || 0), 0),
    }));
}

// Aprire la fotocamera nativa da mobile manda l'app in background: su molti
// telefoni il sistema operativo libera memoria "uccidendo" la scheda del
// browser, così al ritorno dalla fotocamera la pagina si ricarica da zero e
// il form "Nuova spesa" aperto (con l'eventuale scontrino già allegato) va
// perso. Salviamo quindi una bozza in sessionStorage ad ogni modifica del
// form, e la ripristiniamo automaticamente se la pagina si ricarica mentre
// un dialog è aperto.
const DRAFT_KEY = "salesfly:expense-draft";
function loadDraft() {
  try {
    const raw = sessionStorage.getItem(DRAFT_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}
function saveDraft(draft) {
  try {
    sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
  } catch {}
}
function clearDraft() {
  try {
    sessionStorage.removeItem(DRAFT_KEY);
  } catch {}
}

export default function Spese() {
  const [expenses, setExpenses] = useState([]);
  const [open, setOpen] = useState(false);
  const [newExpenseInitial, setNewExpenseInitial] = useState(emptyExpense());
  const [editTarget, setEditTarget] = useState(null);
  const [filter, setFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [expandedMonths, setExpandedMonths] = useState(() => new Set([monthKey(todayIso())]));
  const toggleMonth = (key) => setExpandedMonths((prev) => {
    const next = new Set(prev);
    if (next.has(key)) next.delete(key); else next.add(key);
    return next;
  });

  useEffect(() => {
    const draft = loadDraft();
    if (!draft) return;
    if (draft.type === "new") {
      setNewExpenseInitial(draft.form);
      setOpen(true);
    } else if (draft.type === "edit") {
      setEditTarget(draft.form);
    }
    toast.info("Bozza della spesa ripristinata");
  }, []);

  const load = async () => {
    const params = {};
    if (filter) params.category = filter;
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    const { data } = await api.get("/expenses", { params });
    setExpenses(data);
  };
  useEffect(() => { load(); }, [filter, dateFrom, dateTo]);

  const deleteExpense = async (id, desc) => {
    if (!window.confirm(`Eliminare la spesa "${desc || "senza descrizione"}"?`)) return;
    await api.delete(`/expenses/${id}`);
    toast.success("Spesa eliminata");
    load();
  };

  const total = useMemo(() => expenses.reduce((sum, e) => sum + (e.amount || 0), 0), [expenses]);
  const monthGroups = useMemo(() => groupByMonth(expenses), [expenses]);

  // Con un filtro data attivo l'utente vuole vedere subito i risultati,
  // non doverli scovare aprendo un mese alla volta come nella vista
  // normale (dove solo il mese corrente parte aperto).
  useEffect(() => {
    if (dateFrom || dateTo) setExpandedMonths(new Set(monthGroups.map((g) => g.key)));
  }, [dateFrom, dateTo, monthGroups]);

  return (
    <div className="p-4 md:p-8">
      <div className="flex items-end justify-between border-b border-[#E4E4E1] pb-6 mb-6">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00] mb-2">Note spese</div>
          <h1 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight">Spese</h1>
        </div>
        <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) clearDraft(); }}>
          <DialogTrigger asChild>
            <button data-testid="new-expense-button" onClick={() => setNewExpenseInitial(emptyExpense())} className="flex items-center gap-2 px-4 py-2.5 bg-[#0A192F] text-white rounded-md text-[13px] font-medium">
              <Plus className="w-4 h-4" /> Nuova spesa
            </button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Nuova spesa</DialogTitle></DialogHeader>
            <ExpenseForm
              initial={newExpenseInitial}
              onDraftChange={(f) => saveDraft({ type: "new", form: f })}
              onSave={async (f) => { await api.post("/expenses", f); clearDraft(); load(); toast.success("Spesa registrata"); setOpen(false); }}
            />
          </DialogContent>
        </Dialog>
      </div>

      {/* Dialog modifica */}
      <Dialog open={!!editTarget} onOpenChange={(v) => { if (!v) { setEditTarget(null); clearDraft(); } }}>
        <DialogContent>
          <DialogHeader><DialogTitle>Modifica spesa</DialogTitle></DialogHeader>
          {editTarget && (
            <ExpenseForm
              initial={editTarget}
              submitLabel="Aggiorna"
              onDraftChange={(f) => saveDraft({ type: "edit", form: f })}
              onSave={async (f) => {
                await api.put(`/expenses/${editTarget.id}`, f);
                clearDraft();
                load(); toast.success("Spesa aggiornata"); setEditTarget(null);
              }}
            />
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

      <div className="flex flex-wrap items-center gap-2 mb-4">
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B]">Dal</label>
        <input
          type="date"
          data-testid="expense-date-from"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
          className="bg-white border border-[#E4E4E1] rounded-md px-2.5 py-1.5 text-[12px]"
        />
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B]">Al</label>
        <input
          type="date"
          data-testid="expense-date-to"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          className="bg-white border border-[#E4E4E1] rounded-md px-2.5 py-1.5 text-[12px]"
        />
        {(dateFrom || dateTo) && (
          <button
            onClick={() => { setDateFrom(""); setDateTo(""); }}
            className="text-[12px] text-[#52525B] hover:text-[#0A192F] underline underline-offset-4"
          >
            Cancella filtro date
          </button>
        )}
      </div>

      <div className="space-y-3">
        {monthGroups.map((group) => {
          const isExpanded = expandedMonths.has(group.key);
          return (
            <div key={group.key} className="bg-white border border-[#E4E4E1] rounded-md overflow-hidden">
              <button
                onClick={() => toggleMonth(group.key)}
                data-testid={`expense-month-${group.key}`}
                className="w-full flex items-center justify-between gap-3 px-4 py-3 bg-[#F3F3F1] hover:bg-[#EDEDEA] transition-colors text-left"
              >
                <span className="flex items-center gap-2 font-cabinet font-bold text-[14px]">
                  <ChevronDown className={`w-4 h-4 text-[#A1A1AA] shrink-0 transition-transform ${isExpanded ? "rotate-180" : ""}`} />
                  {group.label}
                </span>
                <span className="font-mono text-[11px] uppercase tracking-widest text-[#52525B]">
                  Totale: <span className="font-cabinet font-black text-[14px] text-[#0A0A0A]">{fmt(group.total)}</span>
                </span>
              </button>
              {isExpanded && (
                <div>
                  <div className="hidden md:grid grid-cols-7 gap-2 px-4 py-3 border-b border-[#E4E4E1] font-mono text-[10px] uppercase tracking-widest text-[#52525B]">
                    <div>Data</div><div>Categoria</div><div className="col-span-2">Descrizione</div><div className="text-right">Importo</div><div className="col-span-2"></div>
                  </div>
                  {group.items.map((e) => (
                    <ExpenseRow key={e.id} e={e} onEdit={setEditTarget} onDelete={deleteExpense} />
                  ))}
                </div>
              )}
            </div>
          );
        })}
        {monthGroups.length === 0 && (
          <div className="bg-white border border-[#E4E4E1] rounded-md p-8 text-center text-[#A1A1AA] text-[13px]">Nessuna spesa registrata.</div>
        )}
      </div>
    </div>
  );
}

const READONLY_SOURCE_LABELS = { flotta: "Flotta", personale: "Personale" };

function ExpenseRow({ e, onEdit, onDelete }) {
  const meta = catMeta(e.category);
  // Spesa generata automaticamente da un costo Flotta o da un compenso
  // dipendente (vedi vehicle_cost_service.py / employee_compensation_service.py):
  // sola lettura qui, va modificata/eliminata dal modulo che l'ha generata,
  // che tiene le due copie sincronizzate.
  const readonlySource = READONLY_SOURCE_LABELS[e.source];
  return (
    <div data-testid={`expense-${e.id}`} className="grid grid-cols-2 md:grid-cols-7 gap-2 px-4 py-3 border-b border-[#E4E4E1] items-center text-[13px]">
      <div className="font-mono text-[12px]">{e.date}</div>
      <div className="text-[#52525B] flex items-center gap-1.5">
        <meta.icon className="w-3.5 h-3.5 text-[#A1A1AA]" />{meta.label}
      </div>
      <div className="col-span-2 truncate flex items-center gap-1.5">
        <span className="truncate">{e.description || "—"}</span>
        {readonlySource && (
          <span title={`Generata automaticamente dal modulo ${readonlySource}`} className="shrink-0 font-mono text-[9px] uppercase tracking-widest px-1.5 py-0.5 rounded-full bg-[#F3F3F1] text-[#A1A1AA]">{readonlySource}</span>
        )}
        {e.receipt_document_id && (
          <button onClick={() => downloadReceipt(e.receipt_document_id, e.description)} title="Vedi scontrino" aria-label="Vedi scontrino"
            className="shrink-0 p-1 text-[#A1A1AA] hover:text-[#FF5A00] hover:bg-[#F3F3F1] rounded transition-colors">
            <Paperclip className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
      <div className="text-right font-cabinet font-bold">{fmt(e.amount)}</div>
      <div className="col-span-2 flex justify-end gap-1">
        {readonlySource ? (
          <span className="text-[11px] text-[#A1A1AA] italic px-1.5" title={`Modificala dal modulo ${readonlySource}`}>Da {readonlySource}</span>
        ) : (
          <>
            <button onClick={() => onEdit(e)} className="p-1.5 text-[#A1A1AA] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded transition-colors" title="Modifica" aria-label="Modifica spesa">
              <Pencil className="w-4 h-4" />
            </button>
            <button onClick={() => onDelete(e.id, e.description)} className="p-1.5 text-[#A1A1AA] hover:text-red-500 hover:bg-red-50 rounded transition-colors" title="Elimina" aria-label="Elimina spesa">
              <Trash2 className="w-4 h-4" />
            </button>
          </>
        )}
      </div>
    </div>
  );
}

function ExpenseForm({ initial, onSave, onDraftChange, submitLabel = "Salva" }) {
  const [f, setF] = useState(initial);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);
  useEffect(() => { setF(initial); }, [initial]);
  useEffect(() => { onDraftChange?.(f); }, [f]);

  const handleFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("name", `Scontrino ${f.date || todayIso()}`);
      fd.append("category", "scontrino");
      fd.append("notes", "");
      fd.append("tags", "spese");
      const { data } = await api.post("/documents/upload", fd);
      setF((prev) => ({ ...prev, receipt_document_id: data.id, receipt_filename: data.original_filename || file.name }));
      toast.success("Scontrino allegato");
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Errore caricamento scontrino");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

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

      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Scontrino</label>
        {f.receipt_document_id ? (
          <div className="flex items-center justify-between gap-2 border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
            <span className="flex items-center gap-1.5 truncate text-[#059669]">
              <Paperclip className="w-3.5 h-3.5 shrink-0" /> <span className="truncate">{f.receipt_filename || "Allegato caricato"}</span>
            </span>
            <button type="button" onClick={() => setF({ ...f, receipt_document_id: null, receipt_filename: null })}
              className="shrink-0 p-1 text-[#A1A1AA] hover:text-red-500 rounded">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <label className="flex items-center justify-center gap-2 border border-dashed border-[#E4E4E1] rounded-md px-3 py-3 text-[13px] text-[#52525B] cursor-pointer hover:border-[#0A192F] transition-colors">
            {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
            {uploading ? "Caricamento..." : "Carica foto o PDF dello scontrino"}
            <input ref={fileInputRef} type="file" accept="image/*,.pdf" className="hidden" onChange={handleFile} disabled={uploading} />
          </label>
        )}
      </div>

      <button data-testid="save-expense-button" type="submit" disabled={uploading} className="w-full bg-[#0A192F] text-white py-2.5 rounded-md text-[13px] font-medium disabled:opacity-50">{submitLabel}</button>
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

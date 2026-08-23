import { useEffect, useState } from "react";
import api from "../api";
import { Plus, Trash2, Download, Pencil, PhoneCall, Clock, CalendarClock, Search, ChevronDown } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../components/ui/dialog";
import { toast } from "sonner";
import { exportLeads } from "../utils/export";
import { formatDistanceToNow, parseISO, format } from "date-fns";
import { it } from "date-fns/locale";

const COLUMNS = [
  { id: "nuovo", label: "Nuovo", color: "#52525B" },
  { id: "contattato", label: "Contattato", color: "#0A192F" },
  { id: "qualificato", label: "Qualificato", color: "#172A45" },
  { id: "trattativa", label: "Trattativa", color: "#B23E00" },
  { id: "vinto", label: "Vinto", color: "#059669" },
  { id: "perso", label: "Perso", color: "#DC2626" },
];

// Schede visibili per colonna al primo caricamento: con molti lead in uno
// stesso stato, una colonna senza limite si allunga all'infinito (l'intera
// board diventa una pagina lunghissima da scorrere). "Mostra altri" rivela
// il resto a richiesta, invece di renderizzarlo e scrollarlo tutto subito.
const PAGE_SIZE = 10;

const fmt = (n) => new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(n || 0);

export default function Leads() {
  const [leads, setLeads] = useState([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [loggingContact, setLoggingContact] = useState(null);
  const [drag, setDrag] = useState(null);
  const [search, setSearch] = useState("");
  // Quante schede mostrare per colonna, per id colonna — sale di PAGE_SIZE
  // alla volta cliccando "Mostra altri", non tocca le altre colonne.
  const [visibleCounts, setVisibleCounts] = useState({});
  const showMore = (colId) => setVisibleCounts((prev) => ({ ...prev, [colId]: (prev[colId] || PAGE_SIZE) + PAGE_SIZE }));

  const load = async () => { const { data } = await api.get("/leads"); setLeads(data); };
  useEffect(() => { load(); }, []);

  const q = search.trim().toLowerCase();
  // Con una ricerca attiva si mostrano TUTTI i risultati che corrispondono,
  // ignorando il limite per colonna: lo scopo della ricerca è trovare
  // subito un lead preciso, non scorrere una lista già filtrata.
  const visibleLeads = q
    ? leads.filter((l) => (l.company_name || "").toLowerCase().includes(q) || (l.contact_name || "").toLowerCase().includes(q))
    : leads;

  // Estratto da onDrop così lo stesso spostamento è raggiungibile anche
  // senza drag-and-drop (vedi il menu a tendina sulla card): l'API HTML5
  // drag-and-drop non genera eventi su dispositivi touch (iOS Safari,
  // Chrome Android) — senza un'alternativa, uno stato non sarebbe MAI
  // cambiabile da mobile, dato che il form di modifica del lead non
  // espone nemmeno il campo stato.
  const moveLead = async (id, status) => {
    await api.patch(`/leads/${id}/status`, { status });
    setLeads((prev) => prev.map(l => l.id === id ? { ...l, status } : l));
    toast.success(`Lead spostato in "${status}"`);
  };

  const onDrop = async (status) => {
    if (!drag) return;
    await moveLead(drag.id, status);
    setDrag(null);
  };

  return (
    <div className="p-4 md:p-8">
      <div className="flex items-end justify-between border-b border-[#E4E4E1] pb-6 mb-6 gap-2">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#B23E00] mb-2">Pipeline</div>
          <h1 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight">Lead & Prospect</h1>
        </div>
        {/* Nuovo lead + CSV raggruppati (prima erano fratelli diretti del
        flex justify-between, con l'export nascosto sotto sm): raggruppare
        li tiene vicini invece di spargerli sui tre "slot" del flex, e
        rende l'export raggiungibile anche da mobile. */}
        <div className="flex items-center gap-2">
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <button data-testid="new-lead-button" className="flex items-center gap-2 px-4 py-2.5 bg-[#0A192F] text-white rounded-md text-[13px] font-medium">
                <Plus className="w-4 h-4" /> Nuovo lead
              </button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader><DialogTitle>Nuovo lead</DialogTitle></DialogHeader>
              <LeadForm onSave={async (f) => { await api.post("/leads", f); load(); toast.success("Lead creato"); setOpen(false); }} />
            </DialogContent>
          </Dialog>
          <button
            data-testid="export-leads-button"
            onClick={() => exportLeads().then(() => toast.success("Export scaricato")).catch(() => toast.error("Errore export"))}
            className="flex items-center gap-2 px-4 py-2.5 border border-[#E4E4E1] hover:border-[#0A192F] rounded-md text-[13px] font-medium"
          >
            <Download className="w-4 h-4" /> CSV
          </button>
        </div>
      </div>

      <div className="relative mb-4 max-w-sm">
        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#6B6B72]" />
        <input
          data-testid="lead-search-input"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Cerca per ragione sociale, referente…"
          className="w-full bg-white border border-[#E4E4E1] rounded-md pl-9 pr-3 py-2 text-[13px] focus:outline-none focus:border-[#0A192F]"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-3 overflow-x-auto">
        {COLUMNS.map((col) => {
          const items = visibleLeads.filter(l => l.status === col.id);
          const visibleCount = q ? items.length : (visibleCounts[col.id] || PAGE_SIZE);
          const shownItems = items.slice(0, visibleCount);
          const remaining = items.length - shownItems.length;
          const total = items.reduce((s, l) => s + (l.estimated_value || 0), 0);
          return (
            <div key={col.id} data-testid={`kanban-col-${col.id}`}
                 onDragOver={(e) => e.preventDefault()} onDrop={() => onDrop(col.id)}
                 className="bg-[#F3F3F1] border border-[#E4E4E1] rounded-md p-3 min-h-[200px]">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full" style={{ background: col.color }} />
                  <span className="font-cabinet font-bold text-[13px]">{col.label}</span>
                </div>
                <span className="font-mono text-[10px] text-[#6B6B72]">{items.length}</span>
              </div>
              <div className="font-mono text-[10px] text-[#52525B] mb-3">{fmt(total)} valore stimato</div>
              {/* Altezza massima + scroll interno: una colonna con molti
              lead scorre su se stessa invece di allungare tutta la pagina
              (vedi PAGE_SIZE sopra per il perché anche del "Mostra altri"). */}
              <div className="space-y-2 max-h-[60vh] overflow-y-auto pr-0.5">
                {shownItems.map((l) => (
                  <div key={l.id} draggable onDragStart={() => setDrag(l)} data-testid={`lead-card-${l.id}`}
                       className="bg-white border border-[#E4E4E1] rounded-md p-3 cursor-grab active:cursor-grabbing">
                    <div className="flex items-start justify-between gap-2">
                      <div className="font-medium text-[13px] flex-1">{l.company_name}</div>
                      <div className="flex items-center gap-1 shrink-0">
                        <button onClick={() => setLoggingContact(l)} data-testid={`log-contact-${l.id}`} title="Registra contatto" aria-label="Registra contatto" className="text-[#6B6B72] hover:text-[#059669]">
                          <PhoneCall className="w-3.5 h-3.5" />
                        </button>
                        <button onClick={() => setEditing(l)} data-testid={`edit-lead-${l.id}`} title="Modifica" aria-label="Modifica lead" className="text-[#6B6B72] hover:text-[#0A192F]">
                          <Pencil className="w-3.5 h-3.5" />
                        </button>
                        <button onClick={async () => { await api.delete(`/leads/${l.id}`); load(); }} title="Elimina" aria-label="Elimina lead" className="text-[#6B6B72] hover:text-[#DC2626]">
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                    {l.contact_name && <div className="text-[11px] text-[#52525B] mt-0.5">{l.contact_name}</div>}
                    <div className="flex items-center justify-between mt-2">
                      <span className="font-mono text-[10px] text-[#6B6B72] uppercase tracking-widest">{l.source || "—"}</span>
                      <span className="font-mono text-[11px] font-bold text-[#B23E00]">{fmt(l.estimated_value)}</span>
                    </div>
                    {(l.last_interaction_at || l.next_follow_up_at) && (
                      <div className="mt-2 pt-2 border-t border-[#F3F3F1] space-y-0.5">
                        {l.last_interaction_at && (
                          <div className="flex items-center gap-1 text-[10px] text-[#52525B]">
                            <Clock className="w-3 h-3 shrink-0" />
                            ultimo contatto {formatDistanceToNow(parseISO(l.last_interaction_at), { addSuffix: true, locale: it })}
                          </div>
                        )}
                        {l.next_follow_up_at && (
                          <div className="flex items-center gap-1 text-[10px] text-[#B23E00] font-medium">
                            <CalendarClock className="w-3 h-3 shrink-0" />
                            prossimo follow-up: {format(parseISO(l.next_follow_up_at), "d MMM", { locale: it })}
                          </div>
                        )}
                      </div>
                    )}
                    {/* Alternativa al drag-and-drop (che su touch non
                    genera alcun evento): sposta lo stato dello stesso lead
                    da qualunque dispositivo. */}
                    <div className="mt-2 pt-2 border-t border-[#F3F3F1]">
                      <select
                        value={l.status}
                        onChange={(e) => moveLead(l.id, e.target.value)}
                        onClick={(e) => e.stopPropagation()}
                        data-testid={`lead-status-select-${l.id}`}
                        className="w-full bg-white border border-[#E4E4E1] rounded-md px-2 py-1.5 text-[11px] font-mono uppercase tracking-widest"
                      >
                        {COLUMNS.map((c) => (
                          <option key={c.id} value={c.id}>{c.label}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                ))}
              </div>
              {remaining > 0 && (
                <button
                  onClick={() => showMore(col.id)}
                  data-testid={`show-more-${col.id}`}
                  className="w-full mt-2 flex items-center justify-center gap-1 text-[11px] font-mono uppercase tracking-widest text-[#52525B] hover:text-[#0A192F] py-1.5"
                >
                  Mostra altri {remaining}
                  <ChevronDown className="w-3 h-3" />
                </button>
              )}
            </div>
          );
        })}
      </div>

      {editing && (
        <Dialog open onOpenChange={(v) => !v && setEditing(null)}>
          <DialogContent>
            <DialogHeader><DialogTitle>Modifica lead</DialogTitle></DialogHeader>
            <LeadForm
              initial={editing}
              onSave={async (f) => {
                await api.put(`/leads/${editing.id}`, f);
                load();
                toast.success("Lead aggiornato");
                setEditing(null);
              }}
            />
          </DialogContent>
        </Dialog>
      )}

      {loggingContact && (
        <LogContactDialog
          lead={loggingContact}
          onClose={() => setLoggingContact(null)}
          onSaved={() => { load(); setLoggingContact(null); }}
        />
      )}
    </div>
  );
}

function LogContactDialog({ lead, onClose, onSaved }) {
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post(`/leads/${lead.id}/log-contact`, { note });
      toast.success("Contatto registrato");
      onSaved();
    } catch {
      toast.error("Errore nella registrazione del contatto");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open onOpenChange={(v) => !v && onClose()}>
      <DialogContent>
        <DialogHeader><DialogTitle>Registra contatto · {lead.company_name}</DialogTitle></DialogHeader>
        <form onSubmit={submit} className="space-y-3">
          <div>
            <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">
              Nota (facoltativa)
            </label>
            <textarea
              rows={3}
              data-testid="log-contact-note-input"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="es. Chiamato, interessato, richiamare tra 3 giorni"
              className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]"
            />
          </div>
          <button data-testid="save-log-contact-button" type="submit" disabled={busy}
                  className="w-full bg-[#059669] text-white py-2.5 rounded-md text-[13px] font-medium disabled:opacity-50">
            {busy ? "Salvataggio…" : "Registra contatto"}
          </button>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function LeadForm({ initial, onSave }) {
  const [f, setF] = useState(initial
    ? { ...initial, next_follow_up_at: initial.next_follow_up_at || "" }
    : { company_name: "", contact_name: "", email: "", phone: "", source: "", estimated_value: 0, status: "nuovo", notes: "", next_follow_up_at: "" }
  );
  const fld = (l, k, type = "text") => (
    <div>
      <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">{l}</label>
      <input type={type} value={f[k] ?? ""} onChange={(e) => setF({ ...f, [k]: type === "number" ? parseFloat(e.target.value) || 0 : e.target.value })}
             className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
    </div>
  );
  return (
    <form onSubmit={async (e) => { e.preventDefault(); await onSave(f); }} className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        {fld("Ragione sociale *", "company_name")}
        {fld("Referente", "contact_name")}
        {fld("Email", "email", "email")}
        {fld("Telefono", "phone")}
        {fld("Fonte", "source")}
        {fld("Valore stimato", "estimated_value", "number")}
        {fld("Prossimo follow-up", "next_follow_up_at", "date")}
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Note</label>
        <textarea rows={2} value={f.notes ?? ""} onChange={(e) => setF({ ...f, notes: e.target.value })}
                  className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      </div>
      <button data-testid="save-lead-button" type="submit" className="w-full bg-[#0A192F] text-white py-2.5 rounded-md text-[13px] font-medium">
        {initial ? "Salva modifiche" : "Salva lead"}
      </button>
    </form>
  );
}

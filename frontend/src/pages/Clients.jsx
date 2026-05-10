import { useEffect, useState } from "react";
import api from "../api";
import { Link } from "react-router-dom";
import { Plus, Search, MapPin, Phone, Mail, Filter, Download, MessageCircle, Pencil } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../components/ui/dialog";
import { toast } from "sonner";
import { useMandante } from "../contexts/MandanteContext";
import { exportClients, whatsappLink } from "../utils/export";

const POTENTIAL_COLOR = { alto: "#059669", medio: "#FF5A00", basso: "#A1A1AA" };

function ClientForm({ initial, onSave, onClose, mandanti }) {
  const [f, setF] = useState(initial || {
    company_name: "", contact_name: "", email: "", phone: "", vat_number: "",
    address: "", city: "", province: "", zone: "", sector: "", potential: "medio",
    lat: null, lng: null, notes: "", mandante_ids: []
  });
  const update = (k, v) => setF({ ...f, [k]: v });
  return (
    <form onSubmit={async (e) => {
      e.preventDefault();
      try { await onSave(f); onClose(); toast.success("Cliente salvato"); } catch { toast.error("Errore salvataggio"); }
    }} className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <Field label="Ragione sociale *" v={f.company_name} on={(v) => update("company_name", v)} required testid="client-company-name" />
        <Field label="Referente" v={f.contact_name} on={(v) => update("contact_name", v)} testid="client-contact-name" />
        <Field label="Email" v={f.email} on={(v) => update("email", v)} type="email" />
        <Field label="Telefono" v={f.phone} on={(v) => update("phone", v)} />
        <Field label="P.IVA" v={f.vat_number} on={(v) => update("vat_number", v)} />
        <Field label="Indirizzo" v={f.address} on={(v) => update("address", v)} />
        <Field label="Città" v={f.city} on={(v) => update("city", v)} />
        <Field label="Provincia" v={f.province} on={(v) => update("province", v)} />
        <Field label="Zona / Regione" v={f.zone} on={(v) => update("zone", v)} />
        <Field label="Settore" v={f.sector} on={(v) => update("sector", v)} />
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Potenziale</label>
          <select value={f.potential} onChange={(e) => update("potential", e.target.value)}
                  className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
            <option value="basso">Basso</option><option value="medio">Medio</option><option value="alto">Alto</option>
          </select>
        </div>
        <Field label="Latitudine" v={f.lat || ""} on={(v) => update("lat", parseFloat(v) || null)} type="number" />
        <Field label="Longitudine" v={f.lng || ""} on={(v) => update("lng", parseFloat(v) || null)} type="number" />
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Mandanti collegati</label>
        <div className="flex flex-wrap gap-2">
          {mandanti.map((m) => {
            const sel = f.mandante_ids.includes(m.id);
            return (
              <button key={m.id} type="button"
                      onClick={() => update("mandante_ids", sel ? f.mandante_ids.filter(x => x !== m.id) : [...f.mandante_ids, m.id])}
                      className={`px-3 py-1.5 rounded-md border text-[12px] ${sel ? "border-[#0A192F] bg-[#0A192F] text-white" : "border-[#E4E4E1] text-[#52525B]"}`}>
                <span className="inline-block w-2 h-2 rounded-full mr-1.5" style={{ background: m.brand_color }} />
                {m.name}
              </button>
            );
          })}
        </div>
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Note</label>
        <textarea value={f.notes} onChange={(e) => update("notes", e.target.value)} rows={3}
                  className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      </div>
      <div className="flex justify-end gap-2 pt-2">
        <button type="button" onClick={onClose} className="px-4 py-2 border border-[#E4E4E1] rounded-md text-[13px] font-medium">Annulla</button>
        <button data-testid="save-client-button" type="submit" className="px-4 py-2 bg-[#0A192F] text-white rounded-md text-[13px] font-medium">Salva cliente</button>
      </div>
    </form>
  );
}

function Field({ label, v, on, type = "text", required, testid }) {
  return (
    <div>
      <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">{label}</label>
      <input data-testid={testid} type={type} required={required} value={v ?? ""} onChange={(e) => on(e.target.value)}
             className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px] focus:outline-none focus:border-[#0A192F]" />
    </div>
  );
}

export default function Clients() {
  const { mandanti } = useMandante();
  const [clients, setClients] = useState([]);
  const [q, setQ] = useState("");
  const [zone, setZone] = useState("");
  const [potential, setPotential] = useState("");
  const [open, setOpen] = useState(false);
  const [editTarget, setEditTarget] = useState(null);

  const load = async () => {
    const params = new URLSearchParams();
    if (q) params.append("q", q);
    if (zone) params.append("zone", zone);
    if (potential) params.append("potential", potential);
    const { data } = await api.get(`/clients?${params}`);
    setClients(data);
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [q, zone, potential]);

  const zones = [...new Set(clients.map((c) => c.zone).filter(Boolean))];

  return (
    <div className="p-4 md:p-8">
      {/* Header */}
      <div className="hidden md:flex items-end justify-between border-b border-[#E4E4E1] pb-6 mb-6">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00] mb-2">Anagrafiche</div>
          <h1 className="font-cabinet font-black text-4xl tracking-tight">Clienti</h1>
          <p className="text-[14px] text-[#52525B] mt-2">{clients.length} aziende nel tuo portafoglio.</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            data-testid="export-clients-button"
            onClick={() => exportClients().then(() => toast.success("Export scaricato")).catch(() => toast.error("Errore export"))}
            className="flex items-center gap-2 px-4 py-2.5 border border-[#E4E4E1] hover:border-[#0A192F] rounded-md text-[13px] font-medium"
          >
            <Download className="w-4 h-4" /> Esporta CSV
          </button>
          <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <button data-testid="new-client-button" className="flex items-center gap-2 px-4 py-2.5 bg-[#0A192F] hover:bg-[#172A45] text-white rounded-md text-[13px] font-medium">
              <Plus className="w-4 h-4" /> Nuovo cliente
            </button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader><DialogTitle className="font-cabinet">Nuovo cliente</DialogTitle></DialogHeader>
            <ClientForm mandanti={mandanti} onSave={async (f) => { await api.post("/clients", f); load(); }} onClose={() => setOpen(false)} />
          </DialogContent>
        </Dialog>
        </div>
      </div>

      {/* Dialog modifica cliente */}
      <Dialog open={!!editTarget} onOpenChange={(v) => !v && setEditTarget(null)}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle>Modifica cliente</DialogTitle></DialogHeader>
          {editTarget && (
            <ClientForm
              mandanti={mandanti}
              initial={{
                company_name: "", contact_name: "", email: "", phone: "",
                vat_number: "", address: "", city: "", province: "", zone: "",
                sector: "", potential: "medio", lat: null, lng: null, notes: "",
                mandante_ids: [],
                ...editTarget,
                mandante_ids: editTarget.mandante_ids || [],
              }}
              onSave={async (f) => { await api.put(`/clients/${editTarget.id}`, f); load(); toast.success("Cliente aggiornato"); }}
              onClose={() => setEditTarget(null)}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Filters */}
      <div className="flex flex-wrap gap-2 mb-4">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#A1A1AA]" />
          <input data-testid="client-search-input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Cerca per ragione sociale, città…"
                 className="w-full bg-white border border-[#E4E4E1] rounded-md pl-9 pr-3 py-2 text-[13px] focus:outline-none focus:border-[#0A192F]" />
        </div>
        <select value={zone} onChange={(e) => setZone(e.target.value)}
                className="bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
          <option value="">Tutte le zone</option>
          {zones.map((z) => <option key={z}>{z}</option>)}
        </select>
        <select value={potential} onChange={(e) => setPotential(e.target.value)}
                className="bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
          <option value="">Ogni potenziale</option>
          <option value="alto">Alto</option><option value="medio">Medio</option><option value="basso">Basso</option>
        </select>
        <div className="md:hidden">
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <button data-testid="new-client-button-mobile" className="flex items-center gap-2 px-4 py-2 bg-[#0A192F] text-white rounded-md text-[13px] font-medium">
                <Plus className="w-4 h-4" /> Nuovo
              </button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
              <DialogHeader><DialogTitle>Nuovo cliente</DialogTitle></DialogHeader>
              <ClientForm mandanti={mandanti} onSave={async (f) => { await api.post("/clients", f); load(); }} onClose={() => setOpen(false)} />
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Desktop table */}
      <div className="hidden md:block bg-white border border-[#E4E4E1] rounded-md overflow-hidden">
        <table className="w-full">
          <thead className="bg-[#F3F3F1] border-b border-[#E4E4E1]">
            <tr className="text-left">
              <th className="px-4 py-3 font-mono text-[10px] uppercase tracking-widest text-[#52525B]">Azienda</th>
              <th className="px-4 py-3 font-mono text-[10px] uppercase tracking-widest text-[#52525B]">Referente</th>
              <th className="px-4 py-3 font-mono text-[10px] uppercase tracking-widest text-[#52525B]">Località</th>
              <th className="px-4 py-3 font-mono text-[10px] uppercase tracking-widest text-[#52525B]">Settore</th>
              <th className="px-4 py-3 font-mono text-[10px] uppercase tracking-widest text-[#52525B]">Potenziale</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {clients.map((c) => (
              <tr key={c.id} className="border-b border-[#E4E4E1] hover:bg-[#F9F9F8] transition-colors">
                <td className="px-4 py-3">
                  <Link to={`/clienti/${c.id}`} data-testid={`client-row-${c.id}`} className="font-semibold text-[13px] hover:text-[#FF5A00]">{c.company_name}</Link>
                  {c.email && <div className="text-[11px] text-[#A1A1AA]">{c.email}</div>}
                </td>
                <td className="px-4 py-3 text-[13px]">{c.contact_name || "—"}</td>
                <td className="px-4 py-3 text-[13px]"><div>{c.city}</div><div className="text-[11px] text-[#A1A1AA]">{c.zone}</div></td>
                <td className="px-4 py-3 text-[13px]">{c.sector || "—"}</td>
                <td className="px-4 py-3"><span className="font-mono text-[10px] uppercase tracking-widest px-2 py-1 rounded" style={{ background: `${POTENTIAL_COLOR[c.potential]}20`, color: POTENTIAL_COLOR[c.potential] }}>{c.potential}</span></td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <button onClick={() => setEditTarget(c)} className="p-1.5 text-[#A1A1AA] hover:text-[#0A192F] hover:bg-[#F3F3F1] rounded transition-colors" title="Modifica">
                      <Pencil className="w-4 h-4" />
                    </button>
                    <Link to={`/clienti/${c.id}`} className="text-[#FF5A00] text-[12px] font-mono uppercase tracking-widest">apri</Link>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {clients.length === 0 && <div className="p-8 text-center text-[#A1A1AA] text-[13px]">Nessun cliente trovato.</div>}
      </div>

      {/* Mobile cards */}
      <div className="md:hidden space-y-2">
        {clients.map((c) => (
          <div key={c.id} className="block bg-white border border-[#E4E4E1] rounded-md p-4">
            <div className="flex justify-end mb-1">
              <button onClick={() => setEditTarget(c)} className="p-1 text-[#A1A1AA] hover:text-[#0A192F]" title="Modifica">
                <Pencil className="w-3.5 h-3.5" />
              </button>
            </div>
            <Link to={`/clienti/${c.id}`} data-testid={`client-card-${c.id}`}>
            <div className="flex items-start justify-between mb-2">
              <div className="font-cabinet font-bold text-[15px] truncate">{c.company_name}</div>
              <span className="font-mono text-[9px] uppercase tracking-widest px-1.5 py-0.5 rounded shrink-0 ml-2" style={{ background: `${POTENTIAL_COLOR[c.potential]}20`, color: POTENTIAL_COLOR[c.potential] }}>{c.potential}</span>
            </div>
            {c.contact_name && <div className="text-[12px] text-[#52525B] mb-1">{c.contact_name}</div>}
            <div className="flex items-center gap-3 text-[11px] text-[#A1A1AA] mt-2">
              {c.city && <span className="flex items-center gap-1"><MapPin className="w-3 h-3" />{c.city}</span>}
              {c.phone && <span className="flex items-center gap-1"><Phone className="w-3 h-3" />{c.phone}</span>}
            </div>
            </Link>
          </div>
        ))}
        {clients.length === 0 && <div className="bg-white border border-[#E4E4E1] rounded-md p-8 text-center text-[#A1A1AA] text-[13px]">Nessun cliente trovato.</div>}
      </div>
    </div>
  );
}

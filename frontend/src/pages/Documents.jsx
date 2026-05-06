import { useEffect, useState } from "react";
import api from "../api";
import { Plus, Folder, Trash2, FileText } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../components/ui/dialog";
import { toast } from "sonner";

const CAT_COLORS = { contratto: "#0A192F", offerta: "#FF5A00", fattura: "#059669", altro: "#52525B" };

export default function Documents() {
  const [docs, setDocs] = useState([]);
  const [clients, setClients] = useState([]);
  const [open, setOpen] = useState(false);

  const load = async () => {
    const [d, c] = await Promise.all([api.get("/documents"), api.get("/clients")]);
    setDocs(d.data); setClients(c.data);
  };
  useEffect(() => { load(); }, []);

  return (
    <div className="p-4 md:p-8">
      <div className="flex items-end justify-between border-b border-[#E4E4E1] pb-6 mb-6">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00] mb-2">Archivio</div>
          <h1 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight">Documenti</h1>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <button data-testid="new-doc-button" className="flex items-center gap-2 px-4 py-2.5 bg-[#0A192F] text-white rounded-md text-[13px] font-medium">
              <Plus className="w-4 h-4" /> Nuovo documento
            </button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Nuovo documento</DialogTitle></DialogHeader>
            <DocForm clients={clients} onSave={async (f) => { await api.post("/documents", f); load(); toast.success("Documento creato"); setOpen(false); }} />
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {docs.map(d => {
          const cli = clients.find(c => c.id === d.client_id);
          return (
            <div key={d.id} data-testid={`doc-${d.id}`} className="bg-white border border-[#E4E4E1] rounded-md p-4">
              <div className="flex items-start justify-between mb-3">
                <FileText className="w-5 h-5" style={{ color: CAT_COLORS[d.category] }} />
                <button onClick={async () => { await api.delete(`/documents/${d.id}`); load(); }} className="text-[#A1A1AA]"><Trash2 className="w-3.5 h-3.5" /></button>
              </div>
              <div className="font-cabinet font-bold text-[14px] leading-tight">{d.name}</div>
              <div className="font-mono text-[10px] uppercase tracking-widest mt-2" style={{ color: CAT_COLORS[d.category] }}>{d.category}</div>
              {cli && <div className="text-[12px] text-[#52525B] mt-2 pt-2 border-t border-[#E4E4E1]">{cli.company_name}</div>}
            </div>
          );
        })}
        {docs.length === 0 && <div className="md:col-span-3 bg-white border border-[#E4E4E1] rounded-md p-8 text-center text-[#A1A1AA] text-[13px]">Nessun documento archiviato.</div>}
      </div>
    </div>
  );
}

function DocForm({ clients, onSave }) {
  const [f, setF] = useState({ client_id: "", name: "", category: "contratto", url: "", notes: "" });
  return (
    <form onSubmit={async (e) => { e.preventDefault(); await onSave(f); }} className="space-y-3">
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Cliente</label>
        <select value={f.client_id} onChange={(e) => setF({ ...f, client_id: e.target.value })}
                className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
          <option value="">— nessuno —</option>
          {clients.map(c => <option key={c.id} value={c.id}>{c.company_name}</option>)}
        </select>
      </div>
      <Field label="Nome documento *" v={f.name} on={(v) => setF({ ...f, name: v })} required />
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Categoria</label>
        <select value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })}
                className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
          <option value="contratto">Contratto</option><option value="offerta">Offerta</option>
          <option value="fattura">Fattura</option><option value="altro">Altro</option>
        </select>
      </div>
      <Field label="URL / link" v={f.url} on={(v) => setF({ ...f, url: v })} />
      <button data-testid="save-doc-button" type="submit" className="w-full bg-[#0A192F] text-white py-2.5 rounded-md text-[13px] font-medium">Salva</button>
    </form>
  );
}

function Field({ label, v, on, type = "text", required }) {
  return (
    <div>
      <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">{label}</label>
      <input type={type} required={required} value={v ?? ""} onChange={(e) => on(e.target.value)}
             className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
    </div>
  );
}

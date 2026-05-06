import { useEffect, useState } from "react";
import api from "../api";
import { Plus, Trash2 } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../components/ui/dialog";
import { toast } from "sonner";
import { useMandante } from "../contexts/MandanteContext";

const fmt = (n) => new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(n || 0);

export default function Products() {
  const { mandanti } = useMandante();
  const [products, setProducts] = useState([]);
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState("");

  const load = async () => { const { data } = await api.get("/products"); setProducts(data); };
  useEffect(() => { load(); }, []);

  const filtered = filter ? products.filter(p => p.mandante_id === filter) : products;

  return (
    <div className="p-4 md:p-8">
      <div className="flex items-end justify-between border-b border-[#E4E4E1] pb-6 mb-6">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00] mb-2">Catalogo</div>
          <h1 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight">Prodotti & Listini</h1>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <button data-testid="new-product-button" className="flex items-center gap-2 px-4 py-2.5 bg-[#0A192F] text-white rounded-md text-[13px] font-medium">
              <Plus className="w-4 h-4" /> Nuovo prodotto
            </button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Nuovo prodotto</DialogTitle></DialogHeader>
            <ProductForm mandanti={mandanti} onSave={async (f) => { await api.post("/products", f); load(); toast.success("Prodotto creato"); setOpen(false); }} />
          </DialogContent>
        </Dialog>
      </div>

      <div className="flex gap-2 mb-4 overflow-x-auto">
        <button onClick={() => setFilter("")} className={`px-3 py-1.5 rounded-md text-[12px] font-medium whitespace-nowrap ${filter === "" ? "bg-[#0A192F] text-white" : "bg-white border border-[#E4E4E1]"}`}>Tutti</button>
        {mandanti.map(m => (
          <button key={m.id} onClick={() => setFilter(m.id)} className={`px-3 py-1.5 rounded-md text-[12px] font-medium whitespace-nowrap flex items-center gap-1.5 ${filter === m.id ? "bg-[#0A192F] text-white" : "bg-white border border-[#E4E4E1]"}`}>
            <span className="w-1.5 h-1.5 rounded-full" style={{ background: m.brand_color }} />{m.name}
          </button>
        ))}
      </div>

      <div className="bg-white border border-[#E4E4E1] rounded-md overflow-hidden">
        <div className="hidden md:grid grid-cols-6 gap-2 px-4 py-3 bg-[#F3F3F1] border-b border-[#E4E4E1] font-mono text-[10px] uppercase tracking-widest text-[#52525B]">
          <div className="col-span-2">Prodotto</div><div>SKU</div><div>Mandante</div><div className="text-right">Prezzo</div><div className="text-right">Margine</div>
        </div>
        {filtered.map(p => {
          const mand = mandanti.find(m => m.id === p.mandante_id);
          const margin = ((p.price - (p.cost || 0)) / p.price * 100).toFixed(0);
          return (
            <div key={p.id} data-testid={`product-${p.id}`} className="grid grid-cols-2 md:grid-cols-6 gap-2 px-4 py-3 border-b border-[#E4E4E1] items-center text-[13px]">
              <div className="col-span-2">
                <div className="font-medium">{p.name}</div>
                <div className="font-mono text-[10px] text-[#A1A1AA]">{p.category}</div>
              </div>
              <div className="font-mono text-[12px]">{p.sku || "—"}</div>
              <div className="text-[#52525B] flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: mand?.brand_color || "#A1A1AA" }} />
                {mand?.name}
              </div>
              <div className="text-right font-cabinet font-bold">{fmt(p.price)}</div>
              <div className="text-right font-mono text-[12px] text-[#059669]">{margin}%</div>
            </div>
          );
        })}
        {filtered.length === 0 && <div className="p-8 text-center text-[#A1A1AA] text-[13px]">Nessun prodotto.</div>}
      </div>
    </div>
  );
}

function ProductForm({ mandanti, onSave }) {
  const [f, setF] = useState({ mandante_id: "", name: "", sku: "", price: 0, cost: 0, category: "", commission_rate: null });
  return (
    <form onSubmit={async (e) => { e.preventDefault(); await onSave(f); }} className="space-y-3">
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Mandante *</label>
        <select required value={f.mandante_id} onChange={(e) => setF({ ...f, mandante_id: e.target.value })}
                className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
          <option value="">— seleziona —</option>
          {mandanti.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
        </select>
      </div>
      <Field label="Nome prodotto *" v={f.name} on={(v) => setF({ ...f, name: v })} required />
      <div className="grid grid-cols-2 gap-3">
        <Field label="SKU" v={f.sku} on={(v) => setF({ ...f, sku: v })} />
        <Field label="Categoria" v={f.category} on={(v) => setF({ ...f, category: v })} />
        <Field label="Prezzo *" v={f.price} on={(v) => setF({ ...f, price: parseFloat(v) || 0 })} type="number" required />
        <Field label="Costo" v={f.cost} on={(v) => setF({ ...f, cost: parseFloat(v) || 0 })} type="number" />
      </div>
      <button data-testid="save-product-button" type="submit" className="w-full bg-[#0A192F] text-white py-2.5 rounded-md text-[13px] font-medium">Salva</button>
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

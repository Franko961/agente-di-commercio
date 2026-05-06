import { useEffect, useState } from "react";
import api from "../api";
import { Plus, Trash2, FileText, Send, Check, X, Download, PenLine } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../components/ui/dialog";
import { format, parseISO } from "date-fns";
import { it } from "date-fns/locale";
import { toast } from "sonner";
import { exportOffers } from "../utils/export";
import SignaturePad from "../components/SignaturePad";

const fmt = (n) => new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(n || 0);

const STATUS_COLORS = {
  bozza: "#A1A1AA", inviata: "#FF5A00", accettata: "#059669", rifiutata: "#DC2626", scaduta: "#52525B"
};

export default function Offers() {
  const [offers, setOffers] = useState([]);
  const [clients, setClients] = useState([]);
  const [mandanti, setMandanti] = useState([]);
  const [products, setProducts] = useState([]);
  const [open, setOpen] = useState(false);
  const [signOffer, setSignOffer] = useState(null);

  const load = async () => {
    const [o, c, m, p] = await Promise.all([api.get("/offers"), api.get("/clients"), api.get("/mandanti"), api.get("/products")]);
    setOffers(o.data.sort((a, b) => b.created_at.localeCompare(a.created_at)));
    setClients(c.data); setMandanti(m.data); setProducts(p.data);
  };
  useEffect(() => { load(); }, []);

  const setStatus = async (id, status) => {
    await api.patch(`/offers/${id}/status`, { status });
    toast.success(`Offerta ${status}`);
    load();
  };

  const onSignSubmit = async (signatureDataUrl, signerName) => {
    await api.post(`/offers/${signOffer.id}/sign`, { signature: signatureDataUrl, signer_name: signerName });
    toast.success("Offerta firmata. PDF in download.");
    load();
  };

  return (
    <div className="p-4 md:p-8">
      <div className="flex items-end justify-between border-b border-[#E4E4E1] pb-6 mb-6">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00] mb-2">Trattative</div>
          <h1 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight">Offerte & Preventivi</h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            data-testid="export-offers-button"
            onClick={() => exportOffers().then(() => toast.success("Export scaricato")).catch(() => toast.error("Errore export"))}
            className="hidden sm:flex items-center gap-2 px-4 py-2.5 border border-[#E4E4E1] hover:border-[#0A192F] rounded-md text-[13px] font-medium"
          >
            <Download className="w-4 h-4" /> CSV
          </button>
          <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <button data-testid="new-offer-button" className="flex items-center gap-2 px-4 py-2.5 bg-[#0A192F] text-white rounded-md text-[13px] font-medium">
              <Plus className="w-4 h-4" /> Nuova offerta
            </button>
          </DialogTrigger>
          <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
            <DialogHeader><DialogTitle>Nuova offerta</DialogTitle></DialogHeader>
            <OfferForm clients={clients} mandanti={mandanti} products={products} onSave={async (f) => { await api.post("/offers", f); load(); toast.success("Offerta creata"); setOpen(false); }} />
          </DialogContent>
        </Dialog>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {offers.map((o) => {
          const cli = clients.find(c => c.id === o.client_id);
          const mand = mandanti.find(m => m.id === o.mandante_id);
          const expired = o.expires_at && new Date(o.expires_at) < new Date();
          return (
            <div key={o.id} data-testid={`offer-card-${o.id}`} className="bg-white border border-[#E4E4E1] rounded-md p-4">
              <div className="flex items-start justify-between gap-2 mb-3">
                <div className="font-mono text-[10px] uppercase tracking-widest" style={{ color: STATUS_COLORS[o.status] }}>{o.status}</div>
                <button onClick={async () => { await api.delete(`/offers/${o.id}`); load(); }} className="text-[#A1A1AA]"><Trash2 className="w-3.5 h-3.5" /></button>
              </div>
              <div className="font-cabinet font-bold text-[15px] leading-tight mb-2">{o.title}</div>
              <div className="text-[12px] text-[#52525B]">{cli?.company_name}</div>
              {mand && <div className="flex items-center gap-1.5 text-[11px] text-[#A1A1AA] mt-1"><span className="w-1.5 h-1.5 rounded-full" style={{ background: mand.brand_color }} />{mand.name}</div>}
              <div className="font-cabinet font-black text-2xl mt-3">{fmt(o.total)}</div>
              <div className="font-mono text-[10px] text-[#A1A1AA] mt-1">{o.items?.length || 0} righe</div>
              {o.expires_at && (
                <div className={`font-mono text-[10px] uppercase tracking-widest mt-2 ${expired ? "text-[#DC2626]" : "text-[#52525B]"}`}>
                  scade {format(parseISO(o.expires_at), "d MMM yyyy", { locale: it })}
                </div>
              )}
              <div className="flex gap-1 mt-3 pt-3 border-t border-[#E4E4E1]">
                {o.status !== "inviata" && o.status !== "accettata" && <button onClick={() => setStatus(o.id, "inviata")} className="flex-1 text-[11px] font-mono uppercase tracking-widest border border-[#E4E4E1] py-1.5 rounded">invia</button>}
                {o.status !== "accettata" && <button onClick={() => setStatus(o.id, "accettata")} className="flex-1 text-[11px] font-mono uppercase tracking-widest bg-[#059669] text-white py-1.5 rounded">accetta</button>}
                {o.status !== "rifiutata" && <button onClick={() => setStatus(o.id, "rifiutata")} className="flex-1 text-[11px] font-mono uppercase tracking-widest border border-[#E4E4E1] py-1.5 rounded">rifiuta</button>}
              </div>
              <button
                data-testid={`sign-offer-${o.id}`}
                onClick={() => setSignOffer(o)}
                className="mt-2 w-full flex items-center justify-center gap-1.5 text-[11px] font-mono uppercase tracking-widest bg-[#0A192F] hover:bg-[#172A45] text-white py-2 rounded"
              >
                <PenLine className="w-3 h-3 text-[#FF5A00]" />
                {o.signature ? "ri-firma & PDF" : "firma & PDF"}
              </button>
            </div>
          );
        })}
      </div>
      {offers.length === 0 && <div className="bg-white border border-[#E4E4E1] rounded-md p-8 text-center text-[#A1A1AA] text-[13px]">Nessuna offerta. Creane una.</div>}

      {/* Signature dialog */}
      <Dialog open={!!signOffer} onOpenChange={(v) => !v && setSignOffer(null)}>
        <DialogContent className="max-w-xl">
          <DialogHeader><DialogTitle className="font-cabinet">Firma offerta</DialogTitle></DialogHeader>
          {signOffer && (
            <SignaturePad
              offer={signOffer}
              client={clients.find(c => c.id === signOffer.client_id)}
              mandante={mandanti.find(m => m.id === signOffer.mandante_id)}
              onSign={onSignSubmit}
              onClose={() => setSignOffer(null)}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function OfferForm({ clients, mandanti, products, onSave }) {
  const [f, setF] = useState({
    client_id: "", mandante_id: "", title: "", items: [{ description: "", quantity: 1, unit_price: 0, discount: 0 }],
    expires_at: "", status: "bozza", notes: ""
  });
  const filtered = f.mandante_id ? products.filter(p => p.mandante_id === f.mandante_id) : products;
  const addItem = () => setF({ ...f, items: [...f.items, { description: "", quantity: 1, unit_price: 0, discount: 0 }] });
  const updItem = (i, k, v) => { const items = [...f.items]; items[i] = { ...items[i], [k]: v }; setF({ ...f, items }); };
  const total = f.items.reduce((s, it) => s + it.quantity * it.unit_price * (1 - it.discount / 100), 0);

  return (
    <form onSubmit={async (e) => {
      e.preventDefault();
      const data = { ...f, expires_at: f.expires_at ? new Date(f.expires_at).toISOString() : null };
      await onSave(data);
    }} className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Cliente *</label>
          <select required value={f.client_id} onChange={(e) => setF({ ...f, client_id: e.target.value })}
                  className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
            <option value="">— seleziona —</option>
            {clients.map(c => <option key={c.id} value={c.id}>{c.company_name}</option>)}
          </select>
        </div>
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Mandante *</label>
          <select required value={f.mandante_id} onChange={(e) => setF({ ...f, mandante_id: e.target.value })}
                  className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
            <option value="">— seleziona —</option>
            {mandanti.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
          </select>
        </div>
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Titolo *</label>
        <input required value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })}
               className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-2">Righe offerta</label>
        <div className="space-y-2">
          {f.items.map((it, i) => (
            <div key={i} className="grid grid-cols-12 gap-2 items-center">
              <select value={it.product_id || ""}
                      onChange={(e) => {
                        const p = products.find(x => x.id === e.target.value);
                        if (p) { updItem(i, "product_id", p.id); updItem(i, "description", p.name); updItem(i, "unit_price", p.price); }
                      }}
                      className="col-span-3 bg-white border border-[#E4E4E1] rounded-md px-2 py-1.5 text-[12px]">
                <option value="">prodotto</option>
                {filtered.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
              <input value={it.description} onChange={(e) => updItem(i, "description", e.target.value)} placeholder="Descrizione"
                     className="col-span-4 bg-white border border-[#E4E4E1] rounded-md px-2 py-1.5 text-[12px]" />
              <input type="number" value={it.quantity} onChange={(e) => updItem(i, "quantity", parseFloat(e.target.value) || 0)} placeholder="Qta"
                     className="col-span-1 bg-white border border-[#E4E4E1] rounded-md px-2 py-1.5 text-[12px]" />
              <input type="number" value={it.unit_price} onChange={(e) => updItem(i, "unit_price", parseFloat(e.target.value) || 0)} placeholder="€"
                     className="col-span-2 bg-white border border-[#E4E4E1] rounded-md px-2 py-1.5 text-[12px]" />
              <input type="number" value={it.discount} onChange={(e) => updItem(i, "discount", parseFloat(e.target.value) || 0)} placeholder="%"
                     className="col-span-2 bg-white border border-[#E4E4E1] rounded-md px-2 py-1.5 text-[12px]" />
            </div>
          ))}
        </div>
        <button type="button" onClick={addItem} className="mt-2 text-[12px] font-mono uppercase tracking-widest text-[#FF5A00]">+ aggiungi riga</button>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Scadenza</label>
          <input type="date" value={f.expires_at} onChange={(e) => setF({ ...f, expires_at: e.target.value })}
                 className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
        </div>
        <div className="text-right">
          <div className="font-mono text-[10px] uppercase tracking-widest text-[#52525B]">Totale</div>
          <div className="font-cabinet font-black text-3xl">{fmt(total)}</div>
        </div>
      </div>
      <button data-testid="save-offer-button" type="submit" className="w-full bg-[#0A192F] text-white py-2.5 rounded-md text-[13px] font-medium">Salva offerta</button>
    </form>
  );
}

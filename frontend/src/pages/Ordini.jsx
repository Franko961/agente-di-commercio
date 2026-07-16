import { useEffect, useMemo, useState } from "react";
import api from "../api";
import { Search, ShoppingCart, Building, Trash2 } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";
import { format, parseISO } from "date-fns";
import { it } from "date-fns/locale";
import { toast } from "sonner";

const fmt = (n) => new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(n || 0);

export default function Ordini() {
  const [clients, setClients] = useState([]);
  const [mandanti, setMandanti] = useState([]);
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [offers, setOffers] = useState([]);
  const [query, setQuery] = useState("");
  const [activeClient, setActiveClient] = useState(null);

  const load = async () => {
    const [c, m, p, o, of] = await Promise.all([
      api.get("/clients"), api.get("/mandanti"), api.get("/products"), api.get("/orders"), api.get("/offers"),
    ]);
    setClients(c.data); setMandanti(m.data); setProducts(p.data); setOrders(o.data); setOffers(of.data);
  };
  useEffect(() => { load(); }, []);

  const filteredClients = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return clients;
    return clients.filter((c) =>
      c.company_name?.toLowerCase().includes(q) ||
      c.contact_name?.toLowerCase().includes(q) ||
      c.city?.toLowerCase().includes(q)
    );
  }, [clients, query]);

  const ordersForClient = (clientId) =>
    orders.filter((o) => o.client_id === clientId).sort((a, b) => b.created_at.localeCompare(a.created_at));

  // Preventivi ancora da decidere per questo cliente: bozza o già inviata,
  // non ancora accettata/rifiutata/scaduta.
  const pendingOffersForClient = (clientId) =>
    offers
      .filter((o) => o.client_id === clientId && ["bozza", "inviata"].includes(o.status))
      .sort((a, b) => b.created_at.localeCompare(a.created_at));

  const saveOrder = async (payload) => {
    await api.post("/orders", payload);
    toast.success("Ordine registrato — provvigione calcolata");
    await load();
  };

  const deleteOrder = async (order) => {
    if (!window.confirm("Eliminare questo ordine? Verrà eliminata anche la provvigione collegata.")) return;
    await api.delete(`/orders/${order.id}`);
    toast.success("Ordine e provvigione collegata eliminati");
    await load();
  };

  const acceptOffer = async (offer) => {
    // Accetta il preventivo così com'è: niente da reinserire, i prodotti sono
    // già quelli dell'offerta. L'ordine e la provvigione vengono generati
    // automaticamente lato backend (offer_service → order_service.create_from_offer).
    await api.patch(`/offers/${offer.id}/status`, { status: "accettata" });
    toast.success("Preventivo accettato — ordine e provvigione generati");
    await load();
  };

  return (
    <div className="p-4 md:p-8">
      <div className="border-b border-[#E4E4E1] pb-6 mb-6">
        <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00] mb-2">Vendite</div>
        <h1 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight">Ordini</h1>
        <p className="text-[#52525B] text-[14px] mt-2">Seleziona un cliente per registrare o rivedere i suoi ordini.</p>
      </div>

      <div className="relative mb-4">
        <Search className="w-4 h-4 text-[#A1A1AA] absolute left-3 top-1/2 -translate-y-1/2" />
        <input
          data-testid="orders-client-search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Cerca cliente per nome, referente o città…"
          className="w-full bg-white border border-[#E4E4E1] rounded-md pl-9 pr-3 py-2.5 text-[13px] focus:outline-none focus:border-[#0A192F]"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {filteredClients.map((c) => {
          const clientOrders = ordersForClient(c.id);
          const pendingCount = pendingOffersForClient(c.id).length;
          const totale = clientOrders.reduce((s, o) => s + (o.total || 0), 0);
          return (
            <button
              key={c.id}
              data-testid={`orders-client-card-${c.id}`}
              onClick={() => setActiveClient(c)}
              className="text-left bg-white border border-[#E4E4E1] hover:border-[#0A192F] rounded-md p-4 transition-colors relative"
            >
              {pendingCount > 0 && (
                <span className="absolute -top-2 -right-2 bg-[#FF5A00] text-white text-[10px] font-mono font-bold w-5 h-5 rounded-full flex items-center justify-center">
                  {pendingCount}
                </span>
              )}
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="font-cabinet font-bold text-[15px] truncate">{c.company_name}</div>
                  <div className="text-[12px] text-[#52525B] truncate">{c.contact_name || c.city || "—"}</div>
                </div>
                <ShoppingCart className="w-4 h-4 text-[#A1A1AA] shrink-0" />
              </div>
              <div className="flex items-center justify-between mt-3 pt-3 border-t border-[#E4E4E1]">
                <span className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA]">
                  {clientOrders.length} {clientOrders.length === 1 ? "ordine" : "ordini"}
                </span>
                <span className="font-cabinet font-bold text-[14px]">{fmt(totale)}</span>
              </div>
            </button>
          );
        })}
      </div>
      {filteredClients.length === 0 && (
        <div className="bg-white border border-[#E4E4E1] rounded-md p-8 text-center text-[#A1A1AA] text-[13px]">
          Nessun cliente trovato.
        </div>
      )}

      <Dialog open={!!activeClient} onOpenChange={(v) => !v && setActiveClient(null)}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-cabinet flex items-center gap-2">
              <Building className="w-4 h-4 text-[#FF5A00]" />
              {activeClient?.company_name}
            </DialogTitle>
          </DialogHeader>

          {activeClient && (
            <div className="space-y-6">
              {pendingOffersForClient(activeClient.id).length > 0 && (
                <div>
                  <div className="font-mono text-[10px] uppercase tracking-widest text-[#FF5A00] mb-2">Preventivi in attesa</div>
                  <div className="space-y-2">
                    {pendingOffersForClient(activeClient.id).map((o) => {
                      const mand = mandanti.find((m) => m.id === o.mandante_id);
                      return (
                        <div key={o.id} data-testid={`pending-offer-row-${o.id}`} className="bg-[#FFF3EC] border border-[#FFD8C2] rounded-md p-3 flex items-center justify-between gap-3">
                          <div className="min-w-0">
                            <div className="font-medium text-[13px] truncate">{o.title}</div>
                            <div className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] mt-1">
                              {mand && <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: mand.brand_color }} />}
                              {mand?.name || "—"} · {o.status} · {o.sale_type}
                            </div>
                          </div>
                          <div className="flex items-center gap-3 shrink-0">
                            <div className="font-cabinet font-bold text-[15px]">{fmt(o.total)}</div>
                            <button
                              data-testid={`accept-offer-${o.id}`}
                              onClick={() => acceptOffer(o)}
                              className="bg-[#059669] hover:opacity-90 text-white text-[11px] font-mono uppercase tracking-widest px-3 py-1.5 rounded"
                            >
                              accetta
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              <div>
                <div className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] mb-2">Storico ordini</div>
                <div className="space-y-2">
                  {ordersForClient(activeClient.id).length === 0 && (
                    <div className="bg-[#F9F9F8] border border-[#E4E4E1] rounded-md p-4 text-center text-[#A1A1AA] text-[12px]">
                      Nessun ordine registrato per questo cliente.
                    </div>
                  )}
                  {ordersForClient(activeClient.id).map((o) => {
                    const mand = mandanti.find((m) => m.id === o.mandante_id);
                    return (
                      <div key={o.id} data-testid={`order-row-${o.id}`} className="bg-[#F9F9F8] border border-[#E4E4E1] rounded-md p-3 flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex items-center gap-1.5 text-[12px] font-medium">
                            {mand && <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: mand.brand_color }} />}
                            {mand?.name || "—"}
                          </div>
                          <div className="font-mono text-[10px] uppercase tracking-widest text-[#A1A1AA] mt-1">
                            {format(parseISO(o.created_at), "d MMM yyyy", { locale: it })} · {o.items?.length || 0} righe · {o.sale_type}
                            {o.source_offer_id && <span className="text-[#FF5A00]"> · da offerta</span>}
                          </div>
                        </div>
                        <div className="flex items-center gap-3 shrink-0">
                          <div className="font-cabinet font-bold text-[15px]">{fmt(o.total)}</div>
                          <button
                            data-testid={`delete-order-${o.id}`}
                            onClick={() => deleteOrder(o)}
                            className="text-[#A1A1AA] hover:text-[#DC2626] p-1"
                            title="Elimina ordine (e la provvigione collegata)"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div>
                <div className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] mb-2">Nuovo ordine</div>
                <OrderForm
                  client={activeClient}
                  mandanti={mandanti}
                  products={products}
                  onSave={async (f) => { await saveOrder(f); setActiveClient(null); }}
                />
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function OrderForm({ client, mandanti, products, onSave }) {
  const [f, setF] = useState({
    client_id: client.id, mandante_id: "", sale_type: "nuovo", notes: "",
    items: [{ description: "", quantity: 1, unit_price: 0, discount: 0 }],
  });
  const filtered = f.mandante_id ? products.filter((p) => p.mandante_id === f.mandante_id) : products;
  const addItem = () => setF((prev) => ({ ...prev, items: [...prev.items, { description: "", quantity: 1, unit_price: 0, discount: 0 }] }));
  // Aggiorna una o più chiavi della riga i in un colpo solo, partendo sempre
  // dallo stato più recente (setF funzionale): evita che chiamate multiple in
  // sequenza (es. selezione prodotto: product_id + description + unit_price)
  // si sovrascrivano a vicenda perdendo i primi aggiornamenti.
  const updItem = (i, patch) => setF((prev) => {
    const items = [...prev.items];
    items[i] = { ...items[i], ...patch };
    return { ...prev, items };
  });
  const total = f.items.reduce((s, it) => s + it.quantity * it.unit_price * (1 - it.discount / 100), 0);

  return (
    <form
      onSubmit={async (e) => {
        e.preventDefault();
        try { await onSave(f); } catch { toast.error("Errore durante la registrazione dell'ordine"); }
      }}
      className="space-y-3"
    >
      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Mandante *</label>
        <select
          required value={f.mandante_id}
          onChange={(e) => setF({ ...f, mandante_id: e.target.value })}
          className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]"
        >
          <option value="">— seleziona —</option>
          {mandanti.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
        </select>
      </div>

      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Tipo vendita</label>
        <div className="flex border border-[#E4E4E1] rounded-md overflow-hidden">
          {[["nuovo", "Nuovo"], ["rinnovo", "Rinnovo"]].map(([val, label]) => (
            <button key={val} type="button" onClick={() => setF({ ...f, sale_type: val })}
              className={`flex-1 py-2 text-[12px] font-medium transition-colors ${f.sale_type === val ? "bg-[#0A192F] text-white" : "bg-white text-[#52525B]"}`}>
              {label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-2">Righe ordine</label>
        <div className="space-y-2">
          {f.items.map((it, i) => (
            <div key={i} className="grid grid-cols-12 gap-2 items-center">
              <select
                value={it.product_id || ""}
                onChange={(e) => {
                  const p = filtered.find((x) => x.id === e.target.value);
                  if (p) updItem(i, { product_id: p.id, description: p.name, unit_price: p.price });
                }}
                className="col-span-3 bg-white border border-[#E4E4E1] rounded-md px-2 py-1.5 text-[12px]"
              >
                <option value="">prodotto</option>
                {filtered.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
              <input value={it.description} onChange={(e) => updItem(i, { description: e.target.value })} placeholder="Descrizione" required
                     className="col-span-4 bg-white border border-[#E4E4E1] rounded-md px-2 py-1.5 text-[12px]" />
              <input type="number" min="0" step="any" value={it.quantity} onChange={(e) => updItem(i, { quantity: parseFloat(e.target.value) || 0 })} placeholder="Qta"
                     className="col-span-1 bg-white border border-[#E4E4E1] rounded-md px-2 py-1.5 text-[12px]" />
              <input type="number" min="0" step="any" value={it.unit_price} onChange={(e) => updItem(i, { unit_price: parseFloat(e.target.value) || 0 })} placeholder="€"
                     className="col-span-2 bg-white border border-[#E4E4E1] rounded-md px-2 py-1.5 text-[12px]" />
              <input type="number" min="0" max="100" step="any" value={it.discount} onChange={(e) => updItem(i, { discount: parseFloat(e.target.value) || 0 })} placeholder="%"
                     className="col-span-2 bg-white border border-[#E4E4E1] rounded-md px-2 py-1.5 text-[12px]" />
            </div>
          ))}
        </div>
        <button type="button" onClick={addItem} className="mt-2 text-[12px] font-mono uppercase tracking-widest text-[#FF5A00]">+ aggiungi riga</button>
      </div>

      <div>
        <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Note</label>
        <textarea value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} rows={2}
                  className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
      </div>

      <div className="flex items-center justify-between pt-1">
        <div>
          <div className="font-mono text-[10px] uppercase tracking-widest text-[#52525B]">Totale</div>
          <div className="font-cabinet font-black text-2xl">{fmt(total)}</div>
        </div>
        <button data-testid="save-order-button" type="submit" className="bg-[#0A192F] hover:bg-[#172A45] text-white px-5 py-2.5 rounded-md text-[13px] font-medium">
          Registra ordine
        </button>
      </div>
    </form>
  );
}

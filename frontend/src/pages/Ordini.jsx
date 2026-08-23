import { useEffect, useMemo, useState } from "react";
import api from "../api";
import { Search, ShoppingCart, Building, Trash2, Pencil } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";
import ProductCombobox from "../components/ProductCombobox";
import { useMandante } from "../contexts/MandanteContext";
import { format, parseISO } from "date-fns";
import { it } from "date-fns/locale";
import { toast } from "sonner";

const fmt = (n) => new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(n || 0);

const ORDER_STATUS_LABELS = {
  confermato: "Confermato", in_evasione: "In evasione", spedito: "Spedito",
  consegnato: "Consegnato", annullato: "Annullato", reso: "Reso",
};
const ORDER_STATUS_COLORS = {
  confermato: "#0A192F", in_evasione: "#B45309", spedito: "#0EA5E9",
  consegnato: "#059669", annullato: "#DC2626", reso: "#DC2626",
};
const PAYMENT_STATUS_LABELS = { non_pagato: "Non pagato", parziale: "Pagamento parziale", pagato: "Pagato" };
const PAYMENT_STATUS_COLORS = { non_pagato: "#DC2626", parziale: "#B45309", pagato: "#059669" };

export default function Ordini() {
  const { activeMandante } = useMandante();
  const mandanteParam = activeMandante && activeMandante !== "all" ? activeMandante : undefined;
  const [clients, setClients] = useState([]);
  const [mandanti, setMandanti] = useState([]);
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [offers, setOffers] = useState([]);
  const [query, setQuery] = useState("");
  const [activeClient, setActiveClient] = useState(null);
  const [showNewOrderForm, setShowNewOrderForm] = useState(false);
  const [editingOrder, setEditingOrder] = useState(null);

  const load = async () => {
    const [c, m, p, o, of] = await Promise.all([
      api.get("/clients"), api.get("/mandanti"), api.get("/products"),
      api.get("/orders", { params: { mandante_id: mandanteParam } }),
      api.get("/offers", { params: { mandante_id: mandanteParam } }),
    ]);
    setClients(c.data); setMandanti(m.data); setProducts(p.data); setOrders(o.data); setOffers(of.data);
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [mandanteParam]);

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

  const saveEditedOrder = async (oid, payload) => {
    await api.put(`/orders/${oid}`, payload);
    toast.success("Ordine aggiornato — provvigione ricalcolata");
    await load();
  };

  const updateOrderField = async (order, field, value) => {
    const wasCancelled = ["annullato", "reso"].includes(order.status);
    const willBeCancelled = ["annullato", "reso"].includes(value);
    try {
      await api.patch(`/orders/${order.id}/status`, { [field]: value });
      if (field === "status" && willBeCancelled && !wasCancelled) {
        toast.success("Ordine annullato — provvigione collegata rimossa");
      } else if (field === "status" && wasCancelled && !willBeCancelled) {
        toast.success("Ordine riattivato — provvigione rigenerata");
      } else {
        toast.success("Aggiornato");
      }
      await load();
    } catch {
      toast.error("Errore durante l'aggiornamento");
    }
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
        <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#B23E00] mb-2">Vendite</div>
        <h1 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight">Ordini</h1>
        <p className="text-[#52525B] text-[14px] mt-2">Seleziona un cliente per registrare o rivedere i suoi ordini.</p>
      </div>

      <div className="relative mb-4">
        <Search className="w-4 h-4 text-[#6B6B72] absolute left-3 top-1/2 -translate-y-1/2" />
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
              onClick={() => { setActiveClient(c); setShowNewOrderForm(false); }}
              className="text-left bg-white border border-[#E4E4E1] hover:border-[#0A192F] rounded-md p-4 transition-colors relative"
            >
              {pendingCount > 0 && (
                <span className="absolute -top-2 -right-2 bg-[#B23E00] text-white text-[10px] font-mono font-bold w-5 h-5 rounded-full flex items-center justify-center">
                  {pendingCount}
                </span>
              )}
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="font-cabinet font-bold text-[15px] truncate">{c.company_name}</div>
                  <div className="text-[12px] text-[#52525B] truncate">{c.contact_name || c.city || "—"}</div>
                </div>
                <ShoppingCart className="w-4 h-4 text-[#6B6B72] shrink-0" />
              </div>
              <div className="flex items-center justify-between mt-3 pt-3 border-t border-[#E4E4E1]">
                <span className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72]">
                  {clientOrders.length} {clientOrders.length === 1 ? "ordine" : "ordini"}
                </span>
                <span className="font-cabinet font-bold text-[14px]">{fmt(totale)}</span>
              </div>
            </button>
          );
        })}
      </div>
      {filteredClients.length === 0 && (
        <div className="bg-white border border-[#E4E4E1] rounded-md p-8 text-center text-[#6B6B72] text-[13px]">
          Nessun cliente trovato.
        </div>
      )}

      <Dialog open={!!activeClient} onOpenChange={(v) => !v && setActiveClient(null)}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-cabinet flex items-center gap-2">
              <Building className="w-4 h-4 text-[#B23E00]" />
              {activeClient?.company_name}
            </DialogTitle>
          </DialogHeader>

          {activeClient && (
            <div className="space-y-6">
              {pendingOffersForClient(activeClient.id).length > 0 && (
                <div>
                  <div className="font-mono text-[10px] uppercase tracking-widest text-[#B23E00] mb-2">Preventivi in attesa</div>
                  <div className="space-y-2">
                    {pendingOffersForClient(activeClient.id).map((o) => {
                      const mand = mandanti.find((m) => m.id === o.mandante_id);
                      return (
                        <div key={o.id} data-testid={`pending-offer-row-${o.id}`} className="bg-[#FFF3EC] border border-[#FFD8C2] rounded-md p-3 flex items-center justify-between gap-3">
                          <div className="min-w-0">
                            <div className="font-medium text-[13px] truncate">{o.title}</div>
                            <div className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-widest text-[#6B6B72] mt-1">
                              {mand && <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: mand.brand_color }} />}
                              {mand?.name || "—"} · {o.status} · {o.sale_type}
                            </div>
                          </div>
                          <div className="flex items-center gap-3 shrink-0">
                            <div className="font-cabinet font-bold text-[15px]">{fmt(o.total)}</div>
                            <button
                              type="button"
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
                    <div className="bg-[#F9F9F8] border border-[#E4E4E1] rounded-md p-4 text-center text-[#6B6B72] text-[12px]">
                      Nessun ordine registrato per questo cliente.
                    </div>
                  )}
                  {ordersForClient(activeClient.id).map((o) => {
                    const mand = mandanti.find((m) => m.id === o.mandante_id);
                    const cancelled = ["annullato", "reso"].includes(o.status);
                    return (
                      <div key={o.id} data-testid={`order-row-${o.id}`} className="bg-[#F9F9F8] border border-[#E4E4E1] rounded-md p-3 space-y-2">
                        <div className="flex items-center justify-between gap-3">
                          <div className="min-w-0">
                            <div className="flex items-center gap-1.5 text-[12px] font-medium">
                              {mand && <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: mand.brand_color }} />}
                              {mand?.name || "—"}
                              {o.numero_ordine && <span className="text-[#6B6B72] font-mono text-[11px]">· {o.numero_ordine}</span>}
                            </div>
                            <div className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72] mt-1">
                              {format(parseISO(o.created_at), "d MMM yyyy", { locale: it })} · {o.items?.length || 0} righe · {o.sale_type}
                              {o.source_offer_id && <span className="text-[#B23E00]"> · da offerta</span>}
                              {o.commission && <span> · provvigione {fmt(o.commission.amount)}</span>}
                            </div>
                            {o.expected_delivery_date && (
                              <div className="font-mono text-[10px] text-[#6B6B72] mt-0.5">
                                Consegna prevista: {format(parseISO(o.expected_delivery_date), "d MMM yyyy", { locale: it })}
                                {o.delivery_date && <> · consegnato il {format(parseISO(o.delivery_date), "d MMM yyyy", { locale: it })}</>}
                              </div>
                            )}
                          </div>
                          <div className="flex items-center gap-3 shrink-0">
                            <div className={`font-cabinet font-bold text-[15px] ${cancelled ? "line-through text-[#6B6B72]" : ""}`}>{fmt(o.total)}</div>
                            <button
                              type="button"
                              data-testid={`edit-order-${o.id}`}
                              onClick={() => setEditingOrder(o)}
                              className="text-[#6B6B72] hover:text-[#0A192F] p-1"
                              title="Modifica ordine"
                              aria-label="Modifica ordine"
                            >
                              <Pencil className="w-3.5 h-3.5" />
                            </button>
                            <button
                              type="button"
                              data-testid={`delete-order-${o.id}`}
                              onClick={() => deleteOrder(o)}
                              className="text-[#6B6B72] hover:text-[#DC2626] p-1"
                              title="Elimina ordine (e la provvigione collegata)"
                              aria-label="Elimina ordine (e la provvigione collegata)"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 pt-2 border-t border-[#E4E4E1]">
                          <select
                            data-testid={`order-status-${o.id}`}
                            value={o.status || "confermato"}
                            onChange={(e) => updateOrderField(o, "status", e.target.value)}
                            style={{ color: ORDER_STATUS_COLORS[o.status] || "#0A192F" }}
                            className="bg-white border border-[#E4E4E1] rounded-md px-2 py-1 text-[11px] font-medium"
                          >
                            {Object.entries(ORDER_STATUS_LABELS).map(([val, label]) => (
                              <option key={val} value={val}>{label}</option>
                            ))}
                          </select>
                          <select
                            data-testid={`order-payment-${o.id}`}
                            value={o.payment_status || "non_pagato"}
                            onChange={(e) => updateOrderField(o, "payment_status", e.target.value)}
                            style={{ color: PAYMENT_STATUS_COLORS[o.payment_status] || "#DC2626" }}
                            className="bg-white border border-[#E4E4E1] rounded-md px-2 py-1 text-[11px] font-medium"
                          >
                            {Object.entries(PAYMENT_STATUS_LABELS).map(([val, label]) => (
                              <option key={val} value={val}>{label}</option>
                            ))}
                          </select>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="font-mono text-[10px] uppercase tracking-widest text-[#52525B]">Nuovo ordine</div>
                  {!showNewOrderForm && (
                    <button
                      type="button"
                      data-testid="show-new-order-form-button"
                      onClick={() => setShowNewOrderForm(true)}
                      className="text-[12px] font-mono uppercase tracking-widest text-[#B23E00]"
                    >
                      + registra manualmente
                    </button>
                  )}
                </div>
                {showNewOrderForm && (
                  <OrderForm
                    client={activeClient}
                    mandanti={mandanti}
                    products={products}
                    onSave={async (f) => { await saveOrder(f); setActiveClient(null); }}
                  />
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={!!editingOrder} onOpenChange={(v) => !v && setEditingOrder(null)}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-cabinet flex items-center gap-2">
              <Pencil className="w-4 h-4 text-[#B23E00]" />
              Modifica ordine {editingOrder?.numero_ordine ? `· ${editingOrder.numero_ordine}` : ""}
            </DialogTitle>
          </DialogHeader>
          {editingOrder && (
            <OrderForm
              client={clients.find((c) => c.id === editingOrder.client_id) || {}}
              order={editingOrder}
              mandanti={mandanti}
              products={products}
              onSave={async (f) => { await saveEditedOrder(editingOrder.id, f); setEditingOrder(null); }}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function OrderForm({ client, order, mandanti, products, onSave }) {
  const [f, setF] = useState(() => order ? {
    client_id: order.client_id, mandante_id: order.mandante_id, sale_type: order.sale_type || "nuovo",
    notes: order.notes || "", items: order.items?.length ? order.items : [{ description: "", quantity: 1, unit_price: 0, discount: 0 }],
    numero_ordine: order.numero_ordine || "", status: order.status || "confermato",
    payment_status: order.payment_status || "non_pagato",
    expected_delivery_date: order.expected_delivery_date || "", delivery_date: order.delivery_date || "",
  } : {
    client_id: client.id, mandante_id: "", sale_type: "nuovo", notes: "",
    items: [{ description: "", quantity: 1, unit_price: 0, discount: 0 }],
    numero_ordine: "", status: "confermato", payment_status: "non_pagato",
    expected_delivery_date: "", delivery_date: "",
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
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Numero ordine</label>
          <input value={f.numero_ordine} onChange={(e) => setF({ ...f, numero_ordine: e.target.value })}
                 placeholder="generato automaticamente se vuoto"
                 className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
        </div>
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
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Stato ordine</label>
          <select value={f.status} onChange={(e) => setF({ ...f, status: e.target.value })}
                  className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
            {Object.entries(ORDER_STATUS_LABELS).map(([val, label]) => (
              <option key={val} value={val}>{label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Pagamento</label>
          <select value={f.payment_status} onChange={(e) => setF({ ...f, payment_status: e.target.value })}
                  className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]">
            {Object.entries(PAYMENT_STATUS_LABELS).map(([val, label]) => (
              <option key={val} value={val}>{label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Consegna prevista</label>
          <input type="date" value={f.expected_delivery_date} onChange={(e) => setF({ ...f, expected_delivery_date: e.target.value })}
                 className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
        </div>
        <div>
          <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Consegna effettiva</label>
          <input type="date" value={f.delivery_date} onChange={(e) => setF({ ...f, delivery_date: e.target.value })}
                 className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
        </div>
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
            // grid-cols-2 sotto sm, grid-cols-12 da sm in su: a 12 colonne
            // fisse (senza collasso) i 5 campi diventavano larghi pochi
            // pixel su schermi stretti (320-375px) o sfondavano il dialog
            // — sotto sm ricadono su 2 righe leggibili (combobox e
            // descrizione a tutta larghezza, quantità/prezzo affiancati,
            // sconto a tutta larghezza).
            <div key={i} className="grid grid-cols-2 sm:grid-cols-12 gap-2 items-center">
              <ProductCombobox
                products={filtered}
                value={it.product_id}
                onSelect={(p) => updItem(i, { product_id: p.id, description: p.name, unit_price: p.price })}
                className="col-span-2 sm:col-span-3 w-full"
              />
              <input value={it.description} onChange={(e) => updItem(i, { description: e.target.value })} placeholder="Descrizione" required
                     className="col-span-2 sm:col-span-4 w-full bg-white border border-[#E4E4E1] rounded-md px-2 py-1.5 text-[12px]" />
              <input type="number" min="0" step="any" value={it.quantity} onChange={(e) => updItem(i, { quantity: parseFloat(e.target.value) || 0 })} placeholder="Qta"
                     className="col-span-1 w-full bg-white border border-[#E4E4E1] rounded-md px-2 py-1.5 text-[12px]" />
              <input type="number" min="0" step="any" value={it.unit_price} onChange={(e) => updItem(i, { unit_price: parseFloat(e.target.value) || 0 })} placeholder="€"
                     className="col-span-1 sm:col-span-2 w-full bg-white border border-[#E4E4E1] rounded-md px-2 py-1.5 text-[12px]" />
              <input type="number" min="0" max="100" step="any" value={it.discount} onChange={(e) => updItem(i, { discount: parseFloat(e.target.value) || 0 })} placeholder="%"
                     className="col-span-2 w-full bg-white border border-[#E4E4E1] rounded-md px-2 py-1.5 text-[12px]" />
            </div>
          ))}
        </div>
        <button type="button" onClick={addItem} className="mt-2 text-[12px] font-mono uppercase tracking-widest text-[#B23E00]">+ aggiungi riga</button>
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
          {order ? "Salva modifiche" : "Registra ordine"}
        </button>
      </div>
    </form>
  );
}

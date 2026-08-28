import { useState } from "react";
import { toast } from "sonner";
import ProductCombobox from "../ProductCombobox";
import { fmt, ORDER_STATUS_LABELS, PAYMENT_STATUS_LABELS } from "./constants";

export default function OrderForm({ client, order, mandanti, products, onSave }) {
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

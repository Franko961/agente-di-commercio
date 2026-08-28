import { Building, Trash2, Pencil } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../ui/dialog";
import { format, parseISO } from "date-fns";
import { it } from "date-fns/locale";
import OrderForm from "./OrderForm";
import { fmt, ORDER_STATUS_LABELS, ORDER_STATUS_COLORS, PAYMENT_STATUS_LABELS, PAYMENT_STATUS_COLORS } from "./constants";

export default function ClientHistoryDialog({
  activeClient, onClose, mandanti, products,
  ordersForClient, pendingOffersForClient, acceptOffer, updateOrderField, deleteOrder,
  setEditingOrder, showNewOrderForm, setShowNewOrderForm, onSaveNewOrder,
}) {
  return (
    <Dialog open={!!activeClient} onOpenChange={(v) => !v && onClose()}>
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
                  onSave={onSaveNewOrder}
                />
              )}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

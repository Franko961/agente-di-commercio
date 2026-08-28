import { useEffect, useMemo, useState } from "react";
import { Pencil } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";
import { useMandante } from "../contexts/MandanteContext";
import { toast } from "sonner";
import { listClients } from "../api/clients";
import { listMandanti } from "../api/mandanti";
import { listProducts } from "../api/products";
import { listOffers, updateOfferStatus } from "../api/offers";
import useOrders from "../hooks/useOrders";
import ClientList from "../components/ordini/ClientList";
import ClientHistoryDialog from "../components/ordini/ClientHistoryDialog";
import OrderForm from "../components/ordini/OrderForm";

export default function Ordini() {
  const { activeMandante } = useMandante();
  const mandanteParam = activeMandante && activeMandante !== "all" ? activeMandante : undefined;
  const [clients, setClients] = useState([]);
  const [mandanti, setMandanti] = useState([]);
  const [products, setProducts] = useState([]);
  const {
    orders, create: createOrderApi, update: updateOrderApi, updateStatus: updateOrderStatusApi,
    remove: removeOrderApi, reload: reloadOrders,
  } = useOrders({ mandante_id: mandanteParam });
  const [offers, setOffers] = useState([]);
  const [query, setQuery] = useState("");
  const [activeClient, setActiveClient] = useState(null);
  const [showNewOrderForm, setShowNewOrderForm] = useState(false);
  const [editingOrder, setEditingOrder] = useState(null);

  useEffect(() => {
    Promise.all([listClients(), listMandanti(), listProducts()]).then(([c, m, p]) => {
      setClients(c); setMandanti(m); setProducts(p);
    });
  }, []);

  const loadOffers = () => listOffers({ mandante_id: mandanteParam }).then(setOffers);
  useEffect(() => { loadOffers(); /* eslint-disable-next-line */ }, [mandanteParam]);

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
    await createOrderApi(payload);
    toast.success("Ordine registrato — provvigione calcolata");
  };

  const saveEditedOrder = async (oid, payload) => {
    await updateOrderApi(oid, payload);
    toast.success("Ordine aggiornato — provvigione ricalcolata");
  };

  const updateOrderField = async (order, field, value) => {
    const wasCancelled = ["annullato", "reso"].includes(order.status);
    const willBeCancelled = ["annullato", "reso"].includes(value);
    try {
      await updateOrderStatusApi(order.id, { [field]: value });
      if (field === "status" && willBeCancelled && !wasCancelled) {
        toast.success("Ordine annullato — provvigione collegata rimossa");
      } else if (field === "status" && wasCancelled && !willBeCancelled) {
        toast.success("Ordine riattivato — provvigione rigenerata");
      } else {
        toast.success("Aggiornato");
      }
    } catch {
      toast.error("Errore durante l'aggiornamento");
    }
  };

  const deleteOrder = async (order) => {
    if (!window.confirm("Eliminare questo ordine? Verrà eliminata anche la provvigione collegata.")) return;
    await removeOrderApi(order.id);
    toast.success("Ordine e provvigione collegata eliminati");
  };

  const acceptOffer = async (offer) => {
    // Accetta il preventivo così com'è: niente da reinserire, i prodotti sono
    // già quelli dell'offerta. L'ordine e la provvigione vengono generati
    // automaticamente lato backend (offer_service → order_service.create_from_offer).
    await updateOfferStatus(offer.id, "accettata");
    toast.success("Preventivo accettato — ordine e provvigione generati");
    await Promise.all([reloadOrders(), loadOffers()]);
  };

  return (
    <div className="p-4 md:p-8">
      <div className="border-b border-[#E4E4E1] pb-6 mb-6">
        <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#B23E00] mb-2">Vendite</div>
        <h1 className="font-cabinet font-black text-3xl md:text-4xl tracking-tight">Ordini</h1>
        <p className="text-[#52525B] text-[14px] mt-2">Seleziona un cliente per registrare o rivedere i suoi ordini.</p>
      </div>

      <ClientList
        filteredClients={filteredClients}
        query={query}
        setQuery={setQuery}
        ordersForClient={ordersForClient}
        pendingOffersForClient={pendingOffersForClient}
        onSelectClient={(c) => { setActiveClient(c); setShowNewOrderForm(false); }}
      />

      <ClientHistoryDialog
        activeClient={activeClient}
        onClose={() => setActiveClient(null)}
        mandanti={mandanti}
        products={products}
        ordersForClient={ordersForClient}
        pendingOffersForClient={pendingOffersForClient}
        acceptOffer={acceptOffer}
        updateOrderField={updateOrderField}
        deleteOrder={deleteOrder}
        setEditingOrder={setEditingOrder}
        showNewOrderForm={showNewOrderForm}
        setShowNewOrderForm={setShowNewOrderForm}
        onSaveNewOrder={async (f) => { await saveOrder(f); setActiveClient(null); }}
      />

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

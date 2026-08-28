import { useCallback, useEffect, useState } from "react";
import { listOrders, createOrder, updateOrder, updateOrderStatus, deleteOrder } from "../api/orders";

/**
 * Elenco ordini (filtrabile per mandante) + mutazioni, stesso pattern di
 * useOffers: ogni scrittura ricarica la sola lista ordini. A differenza
 * dell'originale pages/Ordini.jsx (dove ogni mutazione ricaricava anche
 * clienti/mandanti/prodotti/offerte in blocco), qui il reload è mirato —
 * quei tre domini non cambiano mai per effetto di una scrittura sugli
 * ordini, e le offerte vengono ricaricate a parte solo dopo un'accettazione
 * (vedi acceptOffer in Ordini.jsx).
 */
export default function useOrders(filters = {}) {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const filtersKey = JSON.stringify(filters);

  const reload = useCallback(() => {
    setLoading(true);
    return listOrders(JSON.parse(filtersKey)).then((data) => {
      setOrders(data);
      setLoading(false);
      return data;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtersKey]);

  useEffect(() => { reload(); }, [reload]);

  const create = useCallback(async (payload) => {
    const created = await createOrder(payload);
    await reload();
    return created;
  }, [reload]);

  const update = useCallback(async (id, payload) => {
    const updated = await updateOrder(id, payload);
    await reload();
    return updated;
  }, [reload]);

  const updateStatus = useCallback(async (id, payload) => {
    const result = await updateOrderStatus(id, payload);
    await reload();
    return result;
  }, [reload]);

  const remove = useCallback(async (id) => {
    await deleteOrder(id);
    await reload();
  }, [reload]);

  return { orders, loading, reload, create, update, updateStatus, remove };
}

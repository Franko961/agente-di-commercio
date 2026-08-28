import { useCallback, useEffect, useState } from "react";
import { listOffers, createOffer, deleteOffer, updateOfferStatus, signOffer } from "../api/offers";

/**
 * Elenco offerte (filtrabile per mandante) + mutazioni, stesso pattern di
 * useClients/useLeads: ogni scrittura ricarica la lista da sola.
 */
export default function useOffers(filters = {}) {
  const [offers, setOffers] = useState([]);
  const [loading, setLoading] = useState(true);
  const filtersKey = JSON.stringify(filters);

  const reload = useCallback(() => {
    setLoading(true);
    return listOffers(JSON.parse(filtersKey)).then((data) => {
      setOffers(data);
      setLoading(false);
      return data;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtersKey]);

  useEffect(() => { reload(); }, [reload]);

  const create = useCallback(async (payload) => {
    const created = await createOffer(payload);
    await reload();
    return created;
  }, [reload]);

  const remove = useCallback(async (id) => {
    await deleteOffer(id);
    await reload();
  }, [reload]);

  const setStatus = useCallback(async (id, status) => {
    const result = await updateOfferStatus(id, status);
    await reload();
    return result;
  }, [reload]);

  const sign = useCallback(async (id, payload) => {
    const result = await signOffer(id, payload);
    await reload();
    return result;
  }, [reload]);

  return { offers, loading, reload, create, remove, setStatus, sign };
}

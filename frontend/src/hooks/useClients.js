import { useCallback, useEffect, useState } from "react";
import { listClients, createClient, updateClient, deleteClient } from "../api/clients";
import { trackEvent } from "../lib/analytics";

/**
 * Elenco clienti filtrato + mutazioni, con ricarica automatica dopo ogni
 * scrittura. `filters` può essere un nuovo oggetto letterale ad ogni
 * render del chiamante (come in pages/Clients.jsx): l'effetto dipende dalla
 * sua serializzazione JSON, non dall'identità dell'oggetto, quindi non
 * ricarica ad ogni render se i VALORI dei filtri non sono cambiati.
 */
export default function useClients(filters = {}) {
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const filtersKey = JSON.stringify(filters);

  const reload = useCallback(() => {
    setLoading(true);
    return listClients(JSON.parse(filtersKey)).then((data) => {
      setClients(data);
      setLoading(false);
      return data;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtersKey]);

  useEffect(() => { reload(); }, [reload]);

  const create = useCallback(async (payload) => {
    const created = await createClient(payload);
    // _first_action è aggiunto dal backend SOLO quando questo è davvero il
    // primo cliente/lead/ordine mai creato dall'utente (vedi
    // activation_service lato backend) — segnale di attivazione trial per
    // GA4, non un campo del cliente stesso.
    if (created?._first_action) trackEvent("first_real_action", { type: "client" });
    await reload();
    return created;
  }, [reload]);

  const update = useCallback(async (id, payload) => {
    const updated = await updateClient(id, payload);
    await reload();
    return updated;
  }, [reload]);

  const remove = useCallback(async (id) => {
    await deleteClient(id);
    await reload();
  }, [reload]);

  return { clients, loading, reload, create, update, remove };
}

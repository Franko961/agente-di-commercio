import { useCallback, useEffect, useState } from "react";
import { listLeads, createLead, updateLead, deleteLead, updateLeadStatus, logLeadContact } from "../api/leads";

/**
 * Elenco lead + mutazioni — stesso pattern di useClients/useEmployees, con
 * un'eccezione: `moveStatus` aggiorna lo stato locale in modo ottimistico
 * invece di ricaricare l'intera board dopo ogni chiamata. È usata dal
 * drag-and-drop della Kanban (pages/Leads.jsx): un reload completo ad ogni
 * spostamento produrrebbe uno sfarfallio visibile della board, mentre qui
 * basta aggiornare lo stato della card spostata.
 */
export default function useLeads() {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(() => {
    setLoading(true);
    return listLeads().then((data) => {
      setLeads(data);
      setLoading(false);
      return data;
    });
  }, []);

  useEffect(() => { reload(); }, [reload]);

  const create = useCallback(async (payload) => {
    const created = await createLead(payload);
    await reload();
    return created;
  }, [reload]);

  const update = useCallback(async (id, payload) => {
    const updated = await updateLead(id, payload);
    await reload();
    return updated;
  }, [reload]);

  const remove = useCallback(async (id) => {
    await deleteLead(id);
    await reload();
  }, [reload]);

  const logContact = useCallback(async (id, payload) => {
    const result = await logLeadContact(id, payload);
    await reload();
    return result;
  }, [reload]);

  const moveStatus = useCallback(async (id, status) => {
    setLeads((prev) => prev.map((l) => (l.id === id ? { ...l, status } : l)));
    await updateLeadStatus(id, status);
  }, []);

  return { leads, loading, reload, create, update, remove, logContact, moveStatus };
}

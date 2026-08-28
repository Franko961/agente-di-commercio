import { useCallback, useEffect, useState } from "react";
import { listDocuments, uploadDocument, deleteDocument } from "../api/documents";

/**
 * Elenco documenti + mutazioni. A differenza di useClients/useEmployees non
 * ricarica l'intero elenco dopo ogni scrittura: preserva i due comportamenti
 * ottimistici già presenti in pages/Documents.jsx —
 *   - `remove` toglie subito la card dalla UI e ripristina solo in caso di
 *     errore (ripristino = reload, non serve tenere una copia locale);
 *   - `create` inserisce il documento appena caricato in testa alla lista
 *     usando la risposta del backend, senza un giro di rete in più.
 */
export default function useDocuments() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(() => {
    setLoading(true);
    return listDocuments().then((data) => {
      setDocuments(data);
      setLoading(false);
      return data;
    });
  }, []);

  useEffect(() => { reload(); }, [reload]);

  const create = useCallback(async (formData, config) => {
    const created = await uploadDocument(formData, config);
    setDocuments((prev) => [created, ...prev]);
    return created;
  }, []);

  const remove = useCallback(async (id) => {
    setDocuments((prev) => prev.filter((d) => d.id !== id));
    try {
      await deleteDocument(id);
    } catch (err) {
      await reload(); // ripristina la card se la cancellazione fallisce lato server
      throw err;
    }
  }, [reload]);

  return { documents, loading, reload, create, remove };
}

import { useCallback, useEffect, useState } from "react";
import { listVehicleDeadlines, createVehicleDeadline, updateVehicleDeadline, deleteVehicleDeadline } from "../api/vehicles";

/** Elenco scadenze documentali dei mezzi + mutazioni. */
export default function useVehicleDeadlines() {
  const [deadlines, setDeadlines] = useState([]);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(() => {
    setLoading(true);
    return listVehicleDeadlines().then((data) => {
      setDeadlines(data);
      setLoading(false);
      return data;
    });
  }, []);

  useEffect(() => { reload(); }, [reload]);

  const create = useCallback(async (payload) => {
    const created = await createVehicleDeadline(payload);
    await reload();
    return created;
  }, [reload]);

  const update = useCallback(async (id, payload) => {
    const updated = await updateVehicleDeadline(id, payload);
    await reload();
    return updated;
  }, [reload]);

  const remove = useCallback(async (id) => {
    await deleteVehicleDeadline(id);
    await reload();
  }, [reload]);

  return { deadlines, loading, reload, create, update, remove };
}

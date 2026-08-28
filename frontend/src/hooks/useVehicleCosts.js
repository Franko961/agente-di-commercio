import { useCallback, useEffect, useState } from "react";
import { listVehicleCosts, createVehicleCost, updateVehicleCost, deleteVehicleCost } from "../api/vehicles";

/** Elenco costi dei mezzi + mutazioni. */
export default function useVehicleCosts() {
  const [costs, setCosts] = useState([]);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(() => {
    setLoading(true);
    return listVehicleCosts().then((data) => {
      setCosts(data);
      setLoading(false);
      return data;
    });
  }, []);

  useEffect(() => { reload(); }, [reload]);

  const create = useCallback(async (payload) => {
    const created = await createVehicleCost(payload);
    await reload();
    return created;
  }, [reload]);

  const update = useCallback(async (id, payload) => {
    const updated = await updateVehicleCost(id, payload);
    await reload();
    return updated;
  }, [reload]);

  const remove = useCallback(async (id) => {
    await deleteVehicleCost(id);
    await reload();
  }, [reload]);

  return { costs, loading, reload, create, update, remove };
}

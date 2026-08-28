import { useCallback, useEffect, useState } from "react";
import { listVehicles, createVehicle, updateVehicle, setVehicleActive, deleteVehicle } from "../api/vehicles";

/** Elenco mezzi + mutazioni, stesso pattern di useClients/useEmployees. */
export default function useVehicles() {
  const [vehicles, setVehicles] = useState([]);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(() => {
    setLoading(true);
    return listVehicles().then((data) => {
      setVehicles(data);
      setLoading(false);
      return data;
    });
  }, []);

  useEffect(() => { reload(); }, [reload]);

  const create = useCallback(async (payload) => {
    const created = await createVehicle(payload);
    await reload();
    return created;
  }, [reload]);

  const update = useCallback(async (id, payload) => {
    const updated = await updateVehicle(id, payload);
    await reload();
    return updated;
  }, [reload]);

  const setActive = useCallback(async (id, active) => {
    const result = await setVehicleActive(id, active);
    await reload();
    return result;
  }, [reload]);

  const remove = useCallback(async (id) => {
    await deleteVehicle(id);
    await reload();
  }, [reload]);

  return { vehicles, loading, reload, create, update, setActive, remove };
}

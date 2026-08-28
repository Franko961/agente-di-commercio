import { useCallback, useEffect, useState } from "react";
import { listCargoLoads, createCargoLoad, updateCargoLoad, signCargoLoad, deleteCargoLoad } from "../api/vehicles";

/** Elenco carichi trasportati + mutazioni. */
export default function useCargoLoads() {
  const [loads, setLoads] = useState([]);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(() => {
    setLoading(true);
    return listCargoLoads().then((data) => {
      setLoads(data);
      setLoading(false);
      return data;
    });
  }, []);

  useEffect(() => { reload(); }, [reload]);

  const create = useCallback(async (payload) => {
    const created = await createCargoLoad(payload);
    await reload();
    return created;
  }, [reload]);

  const update = useCallback(async (id, payload) => {
    const updated = await updateCargoLoad(id, payload);
    await reload();
    return updated;
  }, [reload]);

  const sign = useCallback(async (id, payload) => {
    const result = await signCargoLoad(id, payload);
    await reload();
    return result;
  }, [reload]);

  const remove = useCallback(async (id) => {
    await deleteCargoLoad(id);
    await reload();
  }, [reload]);

  return { loads, loading, reload, create, update, sign, remove };
}

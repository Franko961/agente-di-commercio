import { useCallback, useEffect, useState } from "react";
import {
  listEmployees, createEmployee, updateEmployee, deleteEmployee,
  setEmployeeActive, regenerateEmployeeToken,
} from "../api/employees";

/**
 * Elenco dipendenti + mutazioni, con ricarica automatica dopo ogni
 * scrittura — stesso pattern di useClients.js.
 */
export default function useEmployees() {
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(() => {
    setLoading(true);
    return listEmployees().then((data) => {
      setEmployees(data);
      setLoading(false);
      return data;
    });
  }, []);

  useEffect(() => { reload(); }, [reload]);

  const create = useCallback(async (payload) => {
    const created = await createEmployee(payload);
    await reload();
    return created;
  }, [reload]);

  const update = useCallback(async (id, payload) => {
    const updated = await updateEmployee(id, payload);
    await reload();
    return updated;
  }, [reload]);

  const remove = useCallback(async (id) => {
    await deleteEmployee(id);
    await reload();
  }, [reload]);

  const setActive = useCallback(async (id, active) => {
    const result = await setEmployeeActive(id, active);
    await reload();
    return result;
  }, [reload]);

  const regenerateToken = useCallback(async (id) => {
    const result = await regenerateEmployeeToken(id);
    await reload();
    return result;
  }, [reload]);

  return { employees, loading, reload, create, update, remove, setActive, regenerateToken };
}

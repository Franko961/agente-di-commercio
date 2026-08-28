import { createContext, useContext, useEffect, useState } from "react";
import { listMandanti } from "../api/mandanti";
import { useAuth } from "./AuthContext";

const MandanteContext = createContext(null);

export function MandanteProvider({ children }) {
  const { user } = useAuth();
  const [mandanti, setMandanti] = useState([]);
  const [activeMandante, setActiveMandante] = useState("all");

  const refresh = async () => {
    if (!user) return;
    setMandanti(await listMandanti());
  };

  useEffect(() => { refresh(); }, [user]);

  return (
    <MandanteContext.Provider value={{ mandanti, activeMandante, setActiveMandante, refreshMandanti: refresh }}>
      {children}
    </MandanteContext.Provider>
  );
}

export const useMandante = () => useContext(MandanteContext);

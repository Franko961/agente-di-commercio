import { createContext, useContext, useEffect, useState } from "react";
import api from "../api";
import { useAuth } from "./AuthContext";

const MandanteContext = createContext(null);

export function MandanteProvider({ children }) {
  const { user } = useAuth();
  const [mandanti, setMandanti] = useState([]);
  const [activeMandante, setActiveMandante] = useState("all");

  const refresh = async () => {
    if (!user) return;
    const { data } = await api.get("/mandanti");
    setMandanti(data);
  };

  useEffect(() => { refresh(); }, [user]);

  return (
    <MandanteContext.Provider value={{ mandanti, activeMandante, setActiveMandante, refreshMandanti: refresh }}>
      {children}
    </MandanteContext.Provider>
  );
}

export const useMandante = () => useContext(MandanteContext);

import { createContext, useContext, useEffect, useState } from "react";
import api from "../api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/auth/me")
      .then(({ data }) => setUser(data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    setUser(data);
    return data;
  };

  const register = async (name, email, password, plan="base") => {
    const { data } = await api.post("/auth/register", { name, email, password, plan });
    setUser(data);
    return data;
  };

  const logout = async () => {
    try { await api.post("/auth/logout"); } catch (e) {}
    setUser(null);
  };

  const markOnboardingSeen = async () => {
    // Ottimista: nasconde subito la guida anche se la chiamata al backend
    // fallisse o fosse lenta, così l'utente non resta bloccato a guardarla.
    setUser((prev) => (prev ? { ...prev, onboarding_seen: true } : prev));
    try { await api.post("/auth/onboarding-seen"); } catch (e) {}
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, markOnboardingSeen }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);

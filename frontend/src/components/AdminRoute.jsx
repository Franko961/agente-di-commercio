import { Navigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export default function AdminRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-[#F9F9F8]">
      <div className="font-mono text-sm text-[#52525B]">caricamento...</div>
    </div>
  );
  if (!user) return <Navigate to="/login" />;
  if (user.role !== "admin") return <Navigate to="/app" />;
  return children;
}

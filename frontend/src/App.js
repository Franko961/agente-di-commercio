import { BrowserRouter, Routes, Route } from "react-router-dom";
import "@/App.css";
import { AuthProvider } from "./contexts/AuthContext";
import { MandanteProvider } from "./contexts/MandanteContext";
import ProtectedRoute from "./components/ProtectedRoute";
import AdminRoute from "./components/AdminRoute";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Clients from "./pages/Clients";
import ClientDetail from "./pages/ClientDetail";
import Leads from "./pages/Leads";
import Agenda from "./pages/Agenda";
import MapView from "./pages/MapView";
import Offers from "./pages/Offers";
import Commissions from "./pages/Commissions";
import Mandanti from "./pages/Mandanti";
import Products from "./pages/Products";
import Documents from "./pages/Documents";
import Automations from "./pages/Automations";
import AIAssistant from "./pages/AIAssistant";
import Subscription from "./pages/Subscription";
import Admin from "./pages/Admin";
import Pricing from "./pages/Pricing";
import OfflineBanner from "./components/OfflineBanner";
import { Toaster } from "./components/ui/sonner";

function App() {
  return (
    <div className="App">
      <OfflineBanner />
      <BrowserRouter>
        <AuthProvider>
          <MandanteProvider>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/prezzi" element={<Pricing />} />
              <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
                <Route path="/" element={<Dashboard />} />
                <Route path="/clienti" element={<Clients />} />
                <Route path="/clienti/:id" element={<ClientDetail />} />
                <Route path="/lead" element={<Leads />} />
                <Route path="/agenda" element={<Agenda />} />
                <Route path="/mappa" element={<MapView />} />
                <Route path="/offerte" element={<Offers />} />
                <Route path="/provvigioni" element={<Commissions />} />
                <Route path="/mandanti" element={<Mandanti />} />
                <Route path="/prodotti" element={<Products />} />
                <Route path="/documenti" element={<Documents />} />
                <Route path="/automazioni" element={<Automations />} />
                <Route path="/ai" element={<AIAssistant />} />
                <Route path="/abbonamento" element={<Subscription />} />
                <Route path="/admin" element={<AdminRoute><Admin /></AdminRoute>} />
              </Route>
            </Routes>
          </MandanteProvider>
        </AuthProvider>
      </BrowserRouter>
      <Toaster richColors position="top-right" />
    </div>
  );
}

export default App;

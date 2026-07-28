import { BrowserRouter, Routes, Route } from "react-router-dom";
import "@/App.css";
import { AuthProvider } from "./contexts/AuthContext";
import { MandanteProvider } from "./contexts/MandanteContext";
import ProtectedRoute from "./components/ProtectedRoute";
import AdminRoute from "./components/AdminRoute";
import Layout from "./components/Layout";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Clients from "./pages/Clients";
import ImportClienti from "./pages/ImportClienti";
import ClientDetail from "./pages/ClientDetail";
import Leads from "./pages/Leads";
import Agenda from "./pages/Agenda";
import MapView from "./pages/MapView";
import Offers from "./pages/Offers";
import Ordini from "./pages/Ordini";
import Commissions from "./pages/Commissions";
import Mandanti from "./pages/Mandanti";
import Products from "./pages/Products";
import Spese from "./pages/Spese";
import Documents from "./pages/Documents";
import Automations from "./pages/Automations";
import AIAssistant from "./pages/AIAssistant";
import Subscription from "./pages/Subscription";
import Settings from "./pages/Settings";
import Admin from "./pages/Admin";
import Pricing from "./pages/Pricing";
import RichiediDemo from "./pages/RichiediDemo";
import BlogIndex from "./pages/BlogIndex";
import BlogPost from "./pages/BlogPost";
import GuidedTour from "./pages/GuidedTour";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import Privacy from "./pages/Privacy";
import Terms from "./pages/Terms";
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
              <Route path="/" element={<Landing />} />
              <Route path="/login" element={<Login />} />
              <Route path="/prezzi" element={<Pricing />} />
              <Route path="/richiedi-demo" element={<RichiediDemo />} />
              <Route path="/blog" element={<BlogIndex />} />
              <Route path="/blog/:slug" element={<BlogPost />} />
              <Route path="/tour" element={<GuidedTour />} />
              <Route path="/password-dimenticata" element={<ForgotPassword />} />
              <Route path="/reset-password" element={<ResetPassword />} />
              <Route path="/privacy" element={<Privacy />} />
              <Route path="/termini" element={<Terms />} />
              <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
                <Route path="/app" element={<Dashboard />} />
                <Route path="/app/clienti" element={<Clients />} />
                <Route path="/app/clienti/importa" element={<ImportClienti />} />
                <Route path="/app/clienti/:id" element={<ClientDetail />} />
                <Route path="/app/lead" element={<Leads />} />
                <Route path="/app/agenda" element={<Agenda />} />
                <Route path="/app/mappa" element={<MapView />} />
                <Route path="/app/offerte" element={<Offers />} />
                <Route path="/app/ordini" element={<Ordini />} />
                <Route path="/app/provvigioni" element={<Commissions />} />
                <Route path="/app/spese" element={<Spese />} />
                <Route path="/app/mandanti" element={<Mandanti />} />
                <Route path="/app/prodotti" element={<Products />} />
                <Route path="/app/documenti" element={<Documents />} />
                <Route path="/app/automazioni" element={<Automations />} />
                <Route path="/app/ai" element={<AIAssistant />} />
                <Route path="/app/abbonamento" element={<Subscription />} />
                <Route path="/app/impostazioni" element={<Settings />} />
                <Route path="/app/admin" element={<AdminRoute><Admin /></AdminRoute>} />
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

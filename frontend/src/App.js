import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import "@/App.css";
import { AuthProvider } from "./contexts/AuthContext";
import { MandanteProvider } from "./contexts/MandanteContext";
import { CookieConsentProvider } from "./contexts/CookieConsentContext";
import ProtectedRoute from "./components/ProtectedRoute";
import AdminRoute from "./components/AdminRoute";
import Layout from "./components/Layout";
import AnalyticsRouteGuard from "./components/AnalyticsRouteGuard";
import CookieConsentBanner from "./components/CookieConsentBanner";
import OfflineBanner from "./components/OfflineBanner";
import { Toaster } from "./components/ui/sonner";

// Ogni pagina in un chunk separato (React.lazy), invece di un unico bundle
// da ~2.8MB con TUTTE le pagine, incluse quelle del gestionale privato
// (mappe/Leaflet, PDF/jsPDF, grafici/Recharts, firma digitale) che un
// visitatore pubblico — arrivato da una ricerca o un link condiviso sulla
// homepage o un articolo del blog — non userà mai. Un bundle enorme
// rallenta il primo caricamento (Core Web Vitals, fattore di ranking
// Google) e aumenta l'abbandono prima ancora che la pagina sia pronta.
const Landing = lazy(() => import("./pages/Landing"));
const Login = lazy(() => import("./pages/Login"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Clients = lazy(() => import("./pages/Clients"));
const ImportClienti = lazy(() => import("./pages/ImportClienti"));
const ClientDetail = lazy(() => import("./pages/ClientDetail"));
const Leads = lazy(() => import("./pages/Leads"));
const Agenda = lazy(() => import("./pages/Agenda"));
const MapView = lazy(() => import("./pages/MapView"));
const Offers = lazy(() => import("./pages/Offers"));
const Ordini = lazy(() => import("./pages/Ordini"));
const Commissions = lazy(() => import("./pages/Commissions"));
const Mandanti = lazy(() => import("./pages/Mandanti"));
const Products = lazy(() => import("./pages/Products"));
const Spese = lazy(() => import("./pages/Spese"));
const Documents = lazy(() => import("./pages/Documents"));
const Automations = lazy(() => import("./pages/Automations"));
const AIAssistant = lazy(() => import("./pages/AIAssistant"));
const Subscription = lazy(() => import("./pages/Subscription"));
const Settings = lazy(() => import("./pages/Settings"));
const Admin = lazy(() => import("./pages/Admin"));
const Pricing = lazy(() => import("./pages/Pricing"));
const RichiediDemo = lazy(() => import("./pages/RichiediDemo"));
const LandingAI = lazy(() => import("./pages/LandingAI"));
const BlogIndex = lazy(() => import("./pages/BlogIndex"));
const BlogPost = lazy(() => import("./pages/BlogPost"));
const GuidedTour = lazy(() => import("./pages/GuidedTour"));
const HelpCenter = lazy(() => import("./pages/HelpCenter"));
const WhySalesFly = lazy(() => import("./pages/WhySalesFly"));
const Contatti = lazy(() => import("./pages/Contatti"));
const ForgotPassword = lazy(() => import("./pages/ForgotPassword"));
const ResetPassword = lazy(() => import("./pages/ResetPassword"));
const Privacy = lazy(() => import("./pages/Privacy"));
const Terms = lazy(() => import("./pages/Terms"));

// Stesso stile del loader già usato in ProtectedRoute per l'attesa della
// sessione, per non mostrare due indicatori di caricamento diversi durante
// lo stesso primo avvio dell'app.
function PageLoader() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#F9F9F8]">
      <div className="font-mono text-sm text-[#52525B]">caricamento...</div>
    </div>
  );
}

function App() {
  return (
    <div className="App">
      <OfflineBanner />
      <CookieConsentProvider>
        <BrowserRouter>
          <AnalyticsRouteGuard />
          <CookieConsentBanner />
          <AuthProvider>
            <MandanteProvider>
              <Suspense fallback={<PageLoader />}>
              <Routes>
              <Route path="/" element={<Landing />} />
              <Route path="/login" element={<Login />} />
              <Route path="/prezzi" element={<Pricing />} />
              <Route path="/richiedi-demo" element={<RichiediDemo />} />
              <Route path="/assistente-ai" element={<LandingAI />} />
              <Route path="/blog" element={<BlogIndex />} />
              <Route path="/blog/:slug" element={<BlogPost />} />
              <Route path="/tour" element={<GuidedTour />} />
              <Route path="/perche-salesfly" element={<WhySalesFly />} />
              <Route path="/contatti" element={<Contatti />} />
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
                <Route path="/app/aiuto" element={<HelpCenter />} />
                <Route path="/app/admin" element={<AdminRoute><Admin /></AdminRoute>} />
              </Route>
              </Routes>
              </Suspense>
            </MandanteProvider>
          </AuthProvider>
        </BrowserRouter>
      </CookieConsentProvider>
      <Toaster richColors position="top-right" />
    </div>
  );
}

export default App;

import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import "@/App.css";
import { AuthProvider } from "./contexts/AuthContext";
import { MandanteProvider } from "./contexts/MandanteContext";
import { CookieConsentProvider } from "./contexts/CookieConsentContext";
import ProtectedRoute from "./components/ProtectedRoute";
import AdminRoute from "./components/AdminRoute";
import ModuleGuard from "./components/ModuleGuard";
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
//
// Layout (sidebar/header dell'app autenticata, con menu e notifiche —
// componenti Radix UI) era l'unico import ancora eager: finiva nel bundle
// condiviso caricato anche da chi visita solo la homepage pubblica,
// gonfiandolo di codice mai eseguito lì (verificato con Lighthouse: ~54%
// del bundle principale inutilizzato sulla home). Già dentro il confine
// <Suspense> qui sotto, che copre tutte le rotte — nessuna modifica
// ulteriore necessaria per renderlo lazy in sicurezza.
const Landing = lazy(() => import("./pages/Landing"));
const Layout = lazy(() => import("./components/Layout"));
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
const Personale = lazy(() => import("./pages/Personale"));
const Presenze = lazy(() => import("./pages/Presenze"));
const RichiediAssenza = lazy(() => import("./pages/RichiediAssenza"));
const Timbra = lazy(() => import("./pages/Timbra"));
const Flotta = lazy(() => import("./pages/Flotta"));
const Subscription = lazy(() => import("./pages/Subscription"));
const Settings = lazy(() => import("./pages/Settings"));
const Admin = lazy(() => import("./pages/Admin"));
const Pricing = lazy(() => import("./pages/Pricing"));
const RichiediDemo = lazy(() => import("./pages/RichiediDemo"));
const RichiediDemoGrazie = lazy(() => import("./pages/RichiediDemoGrazie"));
const LandingAI = lazy(() => import("./pages/LandingAI"));
const BlogIndex = lazy(() => import("./pages/BlogIndex"));
const BlogPost = lazy(() => import("./pages/BlogPost"));
const GuidedTour = lazy(() => import("./pages/GuidedTour"));
const HelpCenter = lazy(() => import("./pages/HelpCenter"));
const WhySalesFly = lazy(() => import("./pages/WhySalesFly"));
const ChiSiamo = lazy(() => import("./pages/ChiSiamo"));
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
              <Route path="/richiedi-demo/grazie" element={<RichiediDemoGrazie />} />
              <Route path="/richiedi-assenza/:token" element={<RichiediAssenza />} />
              <Route path="/timbra/:token" element={<Timbra />} />
              <Route path="/assistente-ai" element={<LandingAI />} />
              <Route path="/blog" element={<BlogIndex />} />
              <Route path="/blog/:slug" element={<BlogPost />} />
              <Route path="/tour" element={<GuidedTour />} />
              <Route path="/perche-salesfly" element={<WhySalesFly />} />
              <Route path="/chi-siamo" element={<ChiSiamo />} />
              <Route path="/contatti" element={<Contatti />} />
              <Route path="/password-dimenticata" element={<ForgotPassword />} />
              <Route path="/reset-password" element={<ResetPassword />} />
              <Route path="/privacy" element={<Privacy />} />
              <Route path="/termini" element={<Terms />} />
              <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
                <Route path="/app" element={<Dashboard />} />
                <Route path="/app/clienti" element={<ModuleGuard module="clienti"><Clients /></ModuleGuard>} />
                <Route path="/app/clienti/importa" element={<ModuleGuard module="clienti"><ImportClienti /></ModuleGuard>} />
                <Route path="/app/clienti/:id" element={<ModuleGuard module="clienti"><ClientDetail /></ModuleGuard>} />
                <Route path="/app/lead" element={<ModuleGuard module="lead"><Leads /></ModuleGuard>} />
                <Route path="/app/agenda" element={<ModuleGuard module="agenda"><Agenda /></ModuleGuard>} />
                <Route path="/app/mappa" element={<ModuleGuard module="mappa"><MapView /></ModuleGuard>} />
                <Route path="/app/offerte" element={<ModuleGuard module="offerte"><Offers /></ModuleGuard>} />
                <Route path="/app/ordini" element={<ModuleGuard module="ordini"><Ordini /></ModuleGuard>} />
                <Route path="/app/provvigioni" element={<ModuleGuard module="provvigioni"><Commissions /></ModuleGuard>} />
                <Route path="/app/spese" element={<ModuleGuard module="spese"><Spese /></ModuleGuard>} />
                <Route path="/app/mandanti" element={<ModuleGuard module="mandanti"><Mandanti /></ModuleGuard>} />
                <Route path="/app/prodotti" element={<ModuleGuard module="prodotti"><Products /></ModuleGuard>} />
                <Route path="/app/documenti" element={<ModuleGuard module="documenti"><Documents /></ModuleGuard>} />
                <Route path="/app/automazioni" element={<ModuleGuard module="automazioni"><Automations /></ModuleGuard>} />
                <Route path="/app/ai" element={<ModuleGuard module="ai"><AIAssistant /></ModuleGuard>} />
                <Route path="/app/personale" element={<ModuleGuard module="personale" extra><Personale /></ModuleGuard>} />
                <Route path="/app/presenze" element={<ModuleGuard module="personale" extra><Presenze /></ModuleGuard>} />
                <Route path="/app/flotta" element={<ModuleGuard module="flotta" extra><Flotta /></ModuleGuard>} />
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

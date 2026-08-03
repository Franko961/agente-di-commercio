import { useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";
import usePlans from "../hooks/usePlans";
import PageMeta from "../components/PageMeta";

// Pagina raggiunta SOLO dopo un invio riuscito del modulo in RichiediDemo.jsx
// (via navigate con state, non un semplice toggle sulla stessa pagina):
// serve da URL dedicato per il tracciamento conversioni (Google Ads/Analytics),
// che altrimenti non avrebbe modo di distinguere chi ha solo visto il modulo
// da chi l'ha davvero inviato. Non è in pageMeta.js/sitemap.xml (non è
// contenuto da indicizzare, è un passaggio transazionale) ed è noindex.
export default function RichiediDemoGrazie() {
  const { trialDays } = usePlans();
  const location = useLocation();
  const navigate = useNavigate();
  const state = location.state;

  // Raggiunta direttamente (link salvato, digitata a mano, bot) invece che
  // tramite il redirect dopo l'invio: non c'è nulla di vero da confermare,
  // si torna al modulo invece di mostrare una conferma non dovuta.
  useEffect(() => {
    if (!state) navigate("/richiedi-demo", { replace: true });
  }, [state, navigate]);

  if (!state) return null;

  return (
    <div className="min-h-screen bg-[#F9F9F8] flex flex-col">
      <PageMeta
        path="/richiedi-demo/grazie"
        title="Richiesta inviata — SALESFLY"
        description="La tua richiesta di accesso alla demo di SALESFLY è stata inviata."
        noindex
      />

      <header className="border-b border-[#E4E4E1] bg-white px-6 py-4 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-9 h-9 flex items-center justify-center shrink-0">
            <img src="/logo-mark.png" alt="SALESFLY" className="w-full h-full object-contain" />
          </div>
          <span className="font-cabinet font-black text-lg">SALESFLY.</span>
        </Link>
        <Link to="/login" className="text-[13px] text-[#52525B] hover:text-[#0A192F]">Accedi</Link>
      </header>

      <main className="flex-1 px-6 py-16 max-w-lg mx-auto w-full">
        {state.emailFailed ? (
          <div className="bg-white border border-[#E4E4E1] rounded-xl p-8 text-center">
            <CheckCircle2 className="w-12 h-12 text-amber-500 mx-auto mb-4" />
            <h1 className="font-cabinet font-black text-2xl mb-2">Account creato</h1>
            <p className="text-[#52525B] text-sm mb-4">
              Il tuo account con {trialDays} giorni di prova gratuita è pronto, ma non siamo
              riusciti a inviarti l'email con il link per impostare la password. Usa
              "Password dimenticata" nella pagina di accesso per impostarne una.
            </p>
            <Link to="/login" className="text-sm font-medium text-[#0A192F] underline">
              Vai alla pagina di accesso
            </Link>
          </div>
        ) : (
          <div className="bg-white border border-[#E4E4E1] rounded-xl p-8 text-center">
            <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-4" />
            <h1 className="font-cabinet font-black text-2xl mb-2">Controlla la tua email</h1>
            <p className="text-[#52525B] text-sm">
              Abbiamo creato il tuo account con {trialDays} giorni di prova gratuita e ti abbiamo
              inviato un link per impostare la tua password e accedere. Se non lo trovi, controlla anche nello spam.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}

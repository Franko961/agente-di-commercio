import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { CheckCircle2, Smartphone, Timer } from "lucide-react";
import api, { API_BASE } from "../api";
import { toast } from "sonner";
import PageMeta from "../components/PageMeta";

const TYPES = [
  { value: "ferie", label: "Ferie" },
  { value: "permesso", label: "Permesso" },
  { value: "malattia", label: "Malattia" },
];

// Pagina pubblica raggiunta dal link personale di un dipendente (vedi
// employee_service.create_employee sul backend): nessun login richiesto,
// il token nell'URL identifica sia il dipendente sia, indirettamente,
// l'azienda a cui appartiene. Non è in pageMeta.js/sitemap (non è
// contenuto da indicizzare, è uno strumento interno condiviso via link
// diretto) ed è noindex — stesso principio di RichiediDemoGrazie.jsx.
export default function RichiediAssenza() {
  const { token } = useParams();
  const [employeeName, setEmployeeName] = useState(null); // null = caricamento, false = link non valido
  const [form, setForm] = useState({ type: "ferie", date_from: "", date_to: "", note: "" });
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [installPrompt, setInstallPrompt] = useState(null);
  const [isStandalone, setIsStandalone] = useState(false);
  const [isIos, setIsIos] = useState(false);
  const [attendance, setAttendance] = useState(null); // { clocked_in, since } — null = caricamento
  const [clockBusy, setClockBusy] = useState(false);

  useEffect(() => {
    api.get(`/employees/by-token/${token}`)
      .then(({ data }) => setEmployeeName(data.name))
      .catch(() => setEmployeeName(false));
  }, [token]);

  const loadAttendance = () => {
    api.get(`/employees/by-token/${token}/attendance-status`)
      .then(({ data }) => setAttendance(data))
      .catch(() => setAttendance(null));
  };
  useEffect(() => { if (employeeName) loadAttendance(); }, [employeeName]); // eslint-disable-line react-hooks/exhaustive-deps

  const toggleClock = async () => {
    setClockBusy(true);
    try {
      await api.post(`/employees/by-token/${token}/${attendance?.clocked_in ? "clock-out" : "clock-in"}`);
      toast.success(attendance?.clocked_in ? "Uscita registrata" : "Ingresso registrato");
      loadAttendance();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Timbratura non riuscita, riprova tra poco");
    } finally {
      setClockBusy(false);
    }
  };

  // Rende installabile come "app" a sé stante QUESTA pagina (con il token
  // già nell'URL), non l'intero gestionale: il manifest statico in
  // index.html punta a "/" (usato per installare SALESFLY da /app).
  // Sostituisce temporaneamente <link rel="manifest"> con l'URL reale servito
  // dal backend (GET /employees/by-token/{token}/manifest.webmanifest), e lo
  // ripristina smontando il componente. Prima versione usava un Blob URL
  // generato qui in JS: su iOS "Aggiungi a Home" installava comunque l'intera
  // app SALESFLY invece di questa pagina — Safari non gestisce in modo
  // affidabile un manifest con href blob: e ripiega su quello statico
  // dell'app principale (scope "/"). Un URL https reale non ha questo problema.
  useEffect(() => {
    if (!employeeName) return;
    const manifestLink = document.querySelector('link[rel="manifest"]');
    const originalHref = manifestLink?.getAttribute("href");
    if (manifestLink) manifestLink.setAttribute("href", `${API_BASE}/employees/by-token/${token}/manifest.webmanifest`);

    // iOS/Safari non legge affatto il manifest per "Aggiungi a Home": si
    // basa solo su questi meta tag (assenti da index.html perché
    // riguardano solo questa pagina, non l'app principale).
    const appleTitle = document.createElement("meta");
    appleTitle.name = "apple-mobile-web-app-title";
    appleTitle.content = "Assenze";
    document.head.appendChild(appleTitle);
    const appleCapable = document.createElement("meta");
    appleCapable.name = "apple-mobile-web-app-capable";
    appleCapable.content = "yes";
    document.head.appendChild(appleCapable);

    return () => {
      if (manifestLink && originalHref) manifestLink.setAttribute("href", originalHref);
      appleTitle.remove();
      appleCapable.remove();
    };
  }, [employeeName, token]);

  // Rileva se mostrare un invito a installare: Android/Chrome espone un
  // evento nativo con cui offrire un tasto "Aggiungi" (installazione in un
  // tocco); iOS/Safari non lo espone affatto — lì l'unica via è il tasto
  // Condividi del browser, non azionabile da codice, quindi mostriamo solo
  // un'istruzione testuale. Se l'app è già installata (aperta in modalità
  // standalone), non mostriamo nulla.
  useEffect(() => {
    setIsStandalone(window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true);
    setIsIos(/iphone|ipad|ipod/i.test(window.navigator.userAgent) && !window.MSStream);
    const onBeforeInstall = (e) => {
      e.preventDefault();
      setInstallPrompt(e);
    };
    window.addEventListener("beforeinstallprompt", onBeforeInstall);
    return () => window.removeEventListener("beforeinstallprompt", onBeforeInstall);
  }, []);

  const installApp = async () => {
    if (!installPrompt) return;
    await installPrompt.prompt();
    await installPrompt.userChoice;
    setInstallPrompt(null);
  };

  const submit = async (e) => {
    e.preventDefault();
    if (form.date_to < form.date_from) {
      toast.error("La data di fine non può precedere quella di inizio");
      return;
    }
    setBusy(true);
    try {
      await api.post("/leave-requests", { employee_token: token, ...form });
      setSent(true);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Invio non riuscito, riprova tra poco");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F9F9F8] flex flex-col">
      <PageMeta path="/richiedi-assenza" title="Richiesta assenza — SALESFLY" description="Invia una richiesta di ferie, permesso o malattia." noindex />

      <header className="border-b border-[#E4E4E1] bg-white px-6 py-4 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-9 h-9 flex items-center justify-center shrink-0">
            <img src="/logo-mark.png" alt="SALESFLY" className="w-full h-full object-contain" />
          </div>
          <span className="font-cabinet font-black text-lg">SALESFLY.</span>
        </Link>
      </header>

      <main className="flex-1 px-6 py-16 max-w-lg mx-auto w-full">
        {employeeName === null && (
          <p className="text-center text-[#A1A1AA] text-[14px]">Caricamento…</p>
        )}

        {employeeName === false && (
          <div className="bg-white border border-[#E4E4E1] rounded-xl p-8 text-center">
            <h1 className="font-cabinet font-black text-2xl mb-2">Link non valido</h1>
            <p className="text-[#52525B] text-sm">
              Questo link non è (più) valido. Contatta chi gestisce il personale della tua azienda per riceverne uno nuovo.
            </p>
          </div>
        )}

        {employeeName && !isStandalone && (installPrompt || isIos) && (
          <div className="bg-white border border-[#E4E4E1] rounded-xl p-4 mb-6 flex items-start gap-3">
            <Smartphone className="w-5 h-5 text-[#FF5A00] shrink-0 mt-0.5" />
            {installPrompt ? (
              <div className="flex-1 flex items-center justify-between gap-3 flex-wrap">
                <p className="text-[13px] text-[#52525B]">Salva questo link sulla schermata Home per riaprirlo come un'app.</p>
                <button onClick={installApp} className="shrink-0 px-3 py-1.5 bg-[#0A192F] text-white rounded-md text-[12px] font-medium">
                  Aggiungi alla Home
                </button>
              </div>
            ) : (
              <p className="text-[13px] text-[#52525B]">
                Salva questo link come un'app: tocca <strong>Condividi</strong> qui sotto, poi <strong>"Aggiungi a Home"</strong>.
              </p>
            )}
          </div>
        )}

        {employeeName && attendance && (
          <div className="bg-white border border-[#E4E4E1] rounded-xl p-6 mb-6 text-center">
            <Timer className={`w-8 h-8 mx-auto mb-2 ${attendance.clocked_in ? "text-emerald-500" : "text-[#A1A1AA]"}`} />
            {attendance.clocked_in ? (
              <p className="text-[13px] text-[#52525B] mb-4">
                In servizio dalle <strong>{new Date(attendance.since).toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" })}</strong>
              </p>
            ) : (
              <p className="text-[13px] text-[#52525B] mb-4">Non sei in servizio.</p>
            )}
            <button onClick={toggleClock} disabled={clockBusy}
              className={`px-6 py-2.5 rounded-md text-sm font-medium disabled:opacity-60 ${
                attendance.clocked_in ? "bg-[#DC2626] text-white" : "bg-[#0A192F] text-white"
              }`}>
              {clockBusy ? "Attendere…" : attendance.clocked_in ? "Timbra uscita" : "Timbra ingresso"}
            </button>
          </div>
        )}

        {employeeName && sent && (
          <div className="bg-white border border-[#E4E4E1] rounded-xl p-8 text-center">
            <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-4" />
            <h1 className="font-cabinet font-black text-2xl mb-2">Richiesta inviata</h1>
            <p className="text-[#52525B] text-sm">
              La tua richiesta è stata inviata e verrà revisionata a breve. Riceverai una notifica appena verrà approvata o rifiutata.
            </p>
          </div>
        )}

        {employeeName && !sent && (
          <>
            <div className="text-center mb-8">
              <h1 className="font-cabinet font-black text-3xl mb-2">Ciao {employeeName.split(" ")[0]}.</h1>
              <p className="text-[#52525B] text-sm">Invia una richiesta di ferie, permesso o malattia.</p>
            </div>

            <form onSubmit={submit} className="bg-white border border-[#E4E4E1] rounded-xl p-6 space-y-4">
              <div>
                <label className="block text-[12px] font-medium text-[#52525B] mb-1.5">Tipo *</label>
                <div className="grid grid-cols-3 gap-2">
                  {TYPES.map((t) => (
                    <button key={t.value} type="button" onClick={() => setForm({ ...form, type: t.value })}
                      className={`py-2.5 rounded-md border-2 text-[13px] font-medium transition-colors ${
                        form.type === t.value ? "border-[#FF5A00] bg-[#FF5A00] text-white" : "border-[#E4E4E1] text-[#52525B]"
                      }`}>
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[12px] font-medium text-[#52525B] mb-1">Dal *</label>
                  <input type="date" required value={form.date_from} onChange={(e) => setForm({ ...form, date_from: e.target.value })}
                    className="w-full border border-[#E4E4E1] rounded-md px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-[12px] font-medium text-[#52525B] mb-1">Al *</label>
                  <input type="date" required value={form.date_to} onChange={(e) => setForm({ ...form, date_to: e.target.value })}
                    className="w-full border border-[#E4E4E1] rounded-md px-3 py-2 text-sm" />
                </div>
              </div>

              <div>
                <label className="block text-[12px] font-medium text-[#52525B] mb-1">Note (opzionale)</label>
                <textarea value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} rows={3}
                  className="w-full border border-[#E4E4E1] rounded-md px-3 py-2 text-sm" />
              </div>

              <button type="submit" disabled={busy}
                className="w-full bg-[#0A192F] text-white rounded-md py-2.5 text-sm font-medium disabled:opacity-60">
                {busy ? "Invio in corso…" : "Invia richiesta"}
              </button>
            </form>
          </>
        )}
      </main>
    </div>
  );
}

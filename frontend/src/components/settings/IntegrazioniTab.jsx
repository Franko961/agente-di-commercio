import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { CalendarDays, CheckCircle2, Loader2, RefreshCw, Unplug, Plug, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { getGoogleCalendarStatus, connectGoogleCalendar, disconnectGoogleCalendar, syncGoogleCalendar } from "../../api/integrations";

export default function IntegrazioniTab() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [status, setStatus] = useState(null); // null = caricamento
  const [busy, setBusy] = useState(false);

  const loadStatus = async () => {
    try {
      setStatus(await getGoogleCalendarStatus());
    } catch (e) {
      setStatus({ connected: false });
    }
  };

  useEffect(() => {
    loadStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const gcal = searchParams.get("gcal");
    if (gcal === "connected") {
      toast.success("Google Calendar collegato con successo");
      loadStatus();
      searchParams.delete("gcal");
      setSearchParams(searchParams, { replace: true });
    } else if (gcal === "error") {
      toast.error("Collegamento a Google Calendar non riuscito. Riprova.");
      searchParams.delete("gcal");
      searchParams.delete("reason");
      setSearchParams(searchParams, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const connect = async () => {
    setBusy(true);
    try {
      const data = await connectGoogleCalendar();
      window.location.href = data.auth_url;
    } catch (e) {
      toast.error("Impossibile avviare il collegamento a Google");
      setBusy(false);
    }
  };

  const disconnect = async () => {
    setBusy(true);
    try {
      await disconnectGoogleCalendar();
      toast.success("Google Calendar scollegato");
      await loadStatus();
    } catch (e) {
      toast.error("Errore durante lo scollegamento");
    } finally {
      setBusy(false);
    }
  };

  const syncNow = async () => {
    setBusy(true);
    try {
      await syncGoogleCalendar();
      toast.success("Sincronizzazione avviata");
    } catch (e) {
      toast.error("Errore durante la sincronizzazione");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="mb-8">
        <div className="font-mono text-[11px] uppercase tracking-widest text-[#B23E00] mb-1">Impostazioni</div>
        <h1 className="font-cabinet text-3xl font-black">Integrazioni</h1>
        <p className="text-[#52525B] mt-1">Collega servizi esterni per far lavorare Salesfly insieme ai tuoi strumenti.</p>
      </div>

      <div className="border border-[#E4E4E1] rounded-lg p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-md bg-[#F3F3F1] flex items-center justify-center shrink-0">
              <CalendarDays className="w-5 h-5 text-[#0A192F]" />
            </div>
            <div>
              <div className="font-semibold text-[15px]">Google Calendar</div>
              <div className="text-[13px] text-[#52525B] mt-0.5">
                Sincronizza automaticamente gli appuntamenti dell'Agenda con Google Calendar, in entrambe le direzioni.
              </div>
              {status?.connected && (
                <div className="flex items-center gap-1.5 mt-2 text-[12px] text-[#16A34A] font-medium">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Collegato come {status.google_email}
                </div>
              )}
              {status?.connected && status.needs_reauth && (
                <div className="flex items-center gap-1.5 mt-2 text-[12px] text-[#DC2626] font-medium">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  L'autorizzazione non è più valida: riconnetti per riprendere la sincronizzazione
                </div>
              )}
            </div>
          </div>

          {status === null ? (
            <Loader2 className="w-4 h-4 animate-spin text-[#6B6B72]" />
          ) : status.connected ? (
            <div className="flex items-center gap-2 shrink-0">
              {status.needs_reauth && (
                <button
                  data-testid="gcal-reconnect-button"
                  onClick={connect}
                  disabled={busy}
                  className="flex items-center gap-1.5 px-3 py-2 bg-[#B23E00] hover:bg-[#E04F00] text-white rounded-md text-[12px] font-medium transition-colors disabled:opacity-50"
                >
                  <Plug className="w-3.5 h-3.5" /> Riconnetti
                </button>
              )}
              <button
                data-testid="gcal-sync-button"
                onClick={syncNow}
                disabled={busy}
                className="flex items-center gap-1.5 px-3 py-2 border border-[#E4E4E1] hover:border-[#0A192F] rounded-md text-[12px] font-medium transition-colors disabled:opacity-50"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Sincronizza ora
              </button>
              <button
                data-testid="gcal-disconnect-button"
                onClick={disconnect}
                disabled={busy}
                className="flex items-center gap-1.5 px-3 py-2 border border-[#E4E4E1] hover:border-[#DC2626] hover:text-[#DC2626] rounded-md text-[12px] font-medium transition-colors disabled:opacity-50"
              >
                <Unplug className="w-3.5 h-3.5" /> Scollega
              </button>
            </div>
          ) : (
            <button
              data-testid="gcal-connect-button"
              onClick={connect}
              disabled={busy}
              className="shrink-0 px-4 py-2 bg-[#B23E00] hover:bg-[#E04F00] text-white rounded-md text-[13px] font-medium transition-colors disabled:opacity-50"
            >
              {busy ? "Attendere…" : "Connetti"}
            </button>
          )}
        </div>
      </div>

      <p className="text-[11px] text-[#6B6B72] font-mono mt-4">
        La sincronizzazione con Google avviene automaticamente ogni pochi minuti, oltre che subito dopo ogni modifica fatta qui in Salesfly.
      </p>
    </>
  );
}

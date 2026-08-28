import { useEffect, useMemo, useState } from "react";
import { Route, X } from "lucide-react";
import { toast } from "sonner";
import { listClients } from "../api/clients";
import { getAddresses } from "../api/settings";
import { geocodeAddress } from "../api/geocoding";
import { optimizeRoute } from "../api/routePlanning";
import { createAppointmentsBulk } from "../api/appointments";
import { isValidCoord, loadStoredRoutePlan, saveStoredRoutePlan, todayIso } from "../components/mapview/constants";
import ClientsMap from "../components/mapview/ClientsMap";
import RoutePlannerForm from "../components/mapview/RoutePlannerForm";
import RoutePlanDetail from "../components/mapview/RoutePlanDetail";

export default function MapView() {
  const stored = loadStoredRoutePlan();
  const [clients, setClients] = useState([]);
  const [planOpen, setPlanOpen] = useState(stored?.planOpen || false);
  const [selectedIds, setSelectedIds] = useState(stored?.selectedIds || []);
  const [planDate, setPlanDate] = useState(stored?.planDate || todayIso());
  const [startTime, setStartTime] = useState(stored?.startTime || "09:00");
  const [visitMinutes, setVisitMinutes] = useState(stored?.visitMinutes || 30);
  const [startMode, setStartMode] = useState(stored?.startMode || "first_client");
  const [roundTrip, setRoundTrip] = useState(stored?.roundTrip || false);
  const [customQuery, setCustomQuery] = useState(stored?.customQuery || "");
  const [customCoord, setCustomCoord] = useState(stored?.customCoord || null);
  const [customResults, setCustomResults] = useState([]);
  const [customSearching, setCustomSearching] = useState(false);
  const [geoBusy, setGeoBusy] = useState(false);
  const [addresses, setAddresses] = useState(null);
  const [plan, setPlan] = useState(stored?.plan || null);
  // Tappe già visitate, segnate a mano dall'agente (vedi markVisited): non
  // c'è modo affidabile di rilevarlo in automatico via GPS se per navigare
  // si usa Google Maps in un'altra app, quindi resta un tocco manuale.
  const [completedIds, setCompletedIds] = useState(stored?.completedIds || []);
  const [busy, setBusy] = useState(false);
  const [savingAgenda, setSavingAgenda] = useState(false);
  const [savedToAgenda, setSavedToAgenda] = useState(stored?.savedToAgenda || false);

  useEffect(() => {
    saveStoredRoutePlan({
      planOpen, selectedIds, startTime, visitMinutes, plan, completedIds, planDate, savedToAgenda,
      startMode, roundTrip, customQuery, customCoord,
    });
  }, [planOpen, selectedIds, startTime, visitMinutes, plan, completedIds, planDate, savedToAgenda, startMode, roundTrip, customQuery, customCoord]);

  useEffect(() => { listClients().then((data) => setClients(data.filter(c => isValidCoord(c.lat, c.lng)))); }, []);
  useEffect(() => { getAddresses().then(setAddresses).catch(() => setAddresses({})); }, []);

  const homeReady = isValidCoord(addresses?.home_lat, addresses?.home_lng);
  const officeReady = isValidCoord(addresses?.office_lat, addresses?.office_lng);

  const searchCustomAddress = async () => {
    if (customQuery.trim().length < 3) return;
    setCustomSearching(true);
    try {
      const data = await geocodeAddress(customQuery.trim());
      setCustomResults(data);
    } catch {
      setCustomResults([]);
    } finally {
      setCustomSearching(false);
    }
  };

  const pickCustomAddress = (r) => {
    setCustomCoord({ lat: r.lat, lng: r.lng });
    setCustomQuery(r.display_name);
    setCustomResults([]);
  };

  const getCurrentPosition = () =>
    new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error("Geolocalizzazione non supportata da questo browser"));
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (pos) => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
        () => reject(new Error("Impossibile ottenere la posizione attuale — controlla i permessi di localizzazione")),
        { enableHighAccuracy: true, timeout: 10000 }
      );
    });

  const center = clients.length ? [clients[0].lat, clients[0].lng] : [44.5, 11.0];

  const toggleSelected = (id) => {
    setSelectedIds((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]);
  };

  const optimize = async () => {
    if (selectedIds.length === 0) {
      toast.error("Seleziona almeno un cliente da visitare");
      return;
    }

    let startLat = null, startLng = null;
    if (startMode === "current_location") {
      setGeoBusy(true);
      try {
        const pos = await getCurrentPosition();
        startLat = pos.lat;
        startLng = pos.lng;
      } catch (e) {
        toast.error(e.message);
        setGeoBusy(false);
        return;
      }
      setGeoBusy(false);
    } else if (startMode === "custom") {
      if (!customCoord) {
        toast.error("Cerca e scegli un indirizzo di partenza prima di continuare");
        return;
      }
      startLat = customCoord.lat;
      startLng = customCoord.lng;
    }

    setBusy(true);
    setPlan(null);
    setCompletedIds([]);
    setSavedToAgenda(false);
    try {
      const data = await optimizeRoute({
        client_ids: selectedIds,
        start_time: startTime,
        visit_minutes: Number(visitMinutes) || 30,
        start_mode: startMode,
        start_lat: startLat,
        start_lng: startLng,
        round_trip: roundTrip,
      });
      setPlan(data);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Impossibile calcolare il giro visita");
    } finally {
      setBusy(false);
    }
  };

  const saveToAgenda = async () => {
    if (!plan) return;
    setSavingAgenda(true);
    try {
      const appointments = plan.stops.map((s) => ({
        client_id: s.client_id,
        title: `Visita: ${s.company_name}`,
        description: "Generato dal pianificatore giro visite",
        start: new Date(`${planDate}T${s.eta}:00`).toISOString(),
        end: new Date(`${planDate}T${s.departure}:00`).toISOString(),
        location: [s.address, s.city].filter(Boolean).join(", "),
        status: "pianificato",
      }));
      await createAppointmentsBulk(appointments);
      setSavedToAgenda(true);
      toast.success(`${appointments.length} appuntamenti creati in Agenda`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Errore nel salvataggio in Agenda");
    } finally {
      setSavingAgenda(false);
    }
  };

  const resetPlan = () => {
    setPlan(null);
    setSelectedIds([]);
    setCompletedIds([]);
    setSavedToAgenda(false);
  };

  // La "tappa corrente" è la prima non ancora segnata come visitata,
  // nell'ordine ottimizzato: è quella evidenziata nell'elenco e su cui ha
  // senso premere "Naviga" adesso.
  const currentStopId = plan?.stops.find((s) => !completedIds.includes(s.client_id))?.client_id ?? null;

  const markVisited = (stop, isCurrentlyDone) => {
    setCompletedIds((prev) => {
      if (isCurrentlyDone) return prev.filter((id) => id !== stop.client_id);
      return [...prev, stop.client_id];
    });
    if (!isCurrentlyDone && plan) {
      const idx = plan.stops.findIndex((s) => s.client_id === stop.client_id);
      const next = plan.stops.slice(idx + 1).find((s) => !completedIds.includes(s.client_id) && s.client_id !== stop.client_id);
      toast.success(
        next ? `Visita a "${stop.company_name}" conclusa — prossima tappa: ${next.company_name}` : `Visita a "${stop.company_name}" conclusa — giro completato!`
      );
    }
  };

  const routeLine = useMemo(() => {
    if (!plan) return null;
    const points = plan.stops.map((s) => [s.lat, s.lng]);
    if (plan.origin) points.unshift([plan.origin.lat, plan.origin.lng]);
    if (plan.round_trip) points.push(plan.origin ? [plan.origin.lat, plan.origin.lng] : points[0]);
    return points;
  }, [plan]);

  return (
    // Su mobile sottrae anche l'altezza della bottom-nav fissa (MobileNav,
    // stessi 80px/bottom-20 usati da VoiceAssistant.jsx per lo stesso
    // motivo), non solo l'header (64px): senza, il pannello di
    // pianificazione riempiva il container fino al bordo esatto dello
    // schermo, e i pulsanti "Salva il giro in Agenda"/"Nuova
    // pianificazione" — ultimo elemento non scrollabile del pannello —
    // finivano proprio dove la bottom-nav (z-40) li copre.
    <div className="flex flex-col h-[calc(100vh-64px-80px)] md:h-screen">
      <div className="p-4 md:p-8 border-b border-[#E4E4E1] bg-white flex items-center justify-between gap-4 flex-wrap">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#B23E00] mb-1">Geolocalizzazione</div>
          <h1 className="font-cabinet font-black text-2xl md:text-3xl tracking-tight">Mappa Clienti</h1>
          <p className="text-[13px] text-[#52525B] mt-1">{clients.length} clienti geolocalizzati</p>
        </div>
        <button
          data-testid="plan-route-button"
          onClick={() => setPlanOpen(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-[#0A192F] text-white rounded-md text-[13px] font-medium"
        >
          <Route className="w-4 h-4" /> Pianifica giornata
        </button>
      </div>

      <div className="flex-1 min-h-0 relative flex">
        <div className="flex-1 relative" data-testid="map-container">
          <ClientsMap center={center} clients={clients} plan={plan} routeLine={routeLine} />
        </div>

        {planOpen && (
          <div data-testid="route-planner-panel" className="w-full sm:w-[380px] shrink-0 min-h-0 bg-white border-l border-[#E4E4E1] flex flex-col">
            <div className="p-4 border-b border-[#E4E4E1] flex items-center justify-between">
              <div className="font-cabinet font-bold text-[15px] flex items-center gap-2">
                <Route className="w-4 h-4 text-[#B23E00]" /> Pianifica giornata
              </div>
              <button onClick={() => setPlanOpen(false)} className="text-[#6B6B72] hover:text-[#0A0A0A]">
                <X className="w-4 h-4" />
              </button>
            </div>

            {!plan && (
              <RoutePlannerForm
                clients={clients} selectedIds={selectedIds} toggleSelected={toggleSelected}
                startMode={startMode} setStartMode={setStartMode} homeReady={homeReady} officeReady={officeReady}
                customQuery={customQuery} setCustomQuery={setCustomQuery} customCoord={customCoord} setCustomCoord={setCustomCoord}
                customResults={customResults} customSearching={customSearching}
                searchCustomAddress={searchCustomAddress} pickCustomAddress={pickCustomAddress}
                roundTrip={roundTrip} setRoundTrip={setRoundTrip}
                planDate={planDate} setPlanDate={setPlanDate} startTime={startTime} setStartTime={setStartTime}
                visitMinutes={visitMinutes} setVisitMinutes={setVisitMinutes}
                optimize={optimize} busy={busy} geoBusy={geoBusy}
              />
            )}

            {plan && (
              <RoutePlanDetail
                plan={plan} planDate={planDate} completedIds={completedIds} currentStopId={currentStopId} markVisited={markVisited}
                saveToAgenda={saveToAgenda} savingAgenda={savingAgenda} savedToAgenda={savedToAgenda} resetPlan={resetPlan}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

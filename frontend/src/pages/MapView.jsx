import { useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline } from "react-leaflet";
import L from "leaflet";
// Vedi il commento in LocationPicker.jsx: importato qui invece che come
// @import globale così finisce nel chunk lazy di questa pagina, non nel
// bundle caricato da ogni pagina pubblica.
import "leaflet/dist/leaflet.css";
import { Link } from "react-router-dom";
import {
  Route, Loader2, X, MapPin, Clock, Navigation, ExternalLink, CheckCircle2, RotateCcw,
  LocateFixed, Search, CalendarPlus,
} from "lucide-react";
import { toast } from "sonner";
import api from "../api";

// Etichette leggibili per ogni modalità di partenza, usate sia nel <select>
// sia per riassumere all'utente cosa è stato scelto una volta calcolato il
// giro (plan.start_mode arriva identico dal backend).
const START_MODE_LABELS = {
  first_client: "Primo cliente selezionato",
  current_location: "La mia posizione attuale",
  home: "Casa",
  office: "Ufficio",
  custom: "Indirizzo personalizzato",
};

// Link universale di Google Maps: funziona su Android (apre l'app se
// installata), iOS (apre l'app Google Maps se installata, altrimenti
// Safari) e desktop (apre maps.google.com) con un'unica URL, senza dover
// distinguere il dispositivo. Le indicazioni vere e proprie — voce, traffico
// in tempo reale, ricalcolo se si sbaglia strada — restano tutte a carico di
// Google Maps: non ha senso provare a ricostruirle dentro SalesFly.
function navigationUrl(lat, lng) {
  return `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}&travelmode=driving`;
}

// Stesso controllo di LocationPicker.jsx: una coordinata corrotta (fuori dai
// limiti geografici possibili) passata direttamente a Leaflet può portare a
// un crash "Out of Memory" del browser a certi livelli di zoom, invece di
// limitarsi a non mostrare quel marker.
function isValidCoord(lat, lng) {
  return (
    typeof lat === "number" && typeof lng === "number" &&
    Number.isFinite(lat) && Number.isFinite(lng) &&
    lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180
  );
}

// Custom marker
const orangeIcon = L.divIcon({
  className: "",
  html: '<div class="custom-pin"></div>',
  iconSize: [28, 28],
  iconAnchor: [14, 28],
});

function numberedIcon(n) {
  return L.divIcon({
    className: "",
    html: `<div class="custom-pin custom-pin-numbered"><span>${n}</span></div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 28],
  });
}

// Marker distinto per il punto di partenza "virtuale" (posizione attuale,
// casa, ufficio o indirizzo personalizzato): non è una tappa da visitare,
// quindi non deve confondersi con i pin numerati dei clienti.
const originIcon = L.divIcon({
  className: "",
  html: '<div class="custom-pin" style="background:#0A192F"></div>',
  iconSize: [28, 28],
  iconAnchor: [14, 28],
});

// La pianificazione del giro visita viene tenuta in sessionStorage (non solo
// nello stato del componente): senza questo, uscire dalla pagina Mappa per
// aprire una scheda cliente e poi tornare indietro faceva sparire il piano
// appena calcolato, perché React smonta il componente ad ogni cambio pagina
// e ne riparte da zero. sessionStorage sopravvive alla navigazione tra le
// pagine dell'app (si perde solo chiudendo la scheda/il browser, il che ha
// senso per un piano pensato per "la giornata di oggi").
const ROUTE_PLAN_STORAGE_KEY = "salesfly:route-plan";

function loadStoredRoutePlan() {
  try {
    const raw = sessionStorage.getItem(ROUTE_PLAN_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

// Data di calendario locale, non new Date().toISOString().slice(0,10): quel
// metodo legge anno/mese/giorno in UTC, che nell'ultima/prima ora o due del
// giorno locale (a seconda del fuso) può differire dalla data dell'utente —
// usato solo come default della data del giro pianificato, mai per salvare
// timestamp.
const todayIso = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
};

function saveStoredRoutePlan(state) {
  try {
    sessionStorage.setItem(ROUTE_PLAN_STORAGE_KEY, JSON.stringify(state));
  } catch {
    // sessionStorage può non essere disponibile (es. modalità privata con
    // restrizioni) — la pianificazione resta comunque utilizzabile per la
    // sessione corrente, semplicemente non sopravvive alla navigazione.
  }
}

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

  useEffect(() => { api.get("/clients").then(({ data }) => setClients(data.filter(c => isValidCoord(c.lat, c.lng)))); }, []);
  useEffect(() => { api.get("/settings/addresses").then(({ data }) => setAddresses(data)).catch(() => setAddresses({})); }, []);

  const homeReady = isValidCoord(addresses?.home_lat, addresses?.home_lng);
  const officeReady = isValidCoord(addresses?.office_lat, addresses?.office_lng);

  const searchCustomAddress = async () => {
    if (customQuery.trim().length < 3) return;
    setCustomSearching(true);
    try {
      const { data } = await api.get("/geocode", { params: { q: customQuery.trim() } });
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
      const { data } = await api.post("/route-planning/optimize", {
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
      await api.post("/appointments/bulk", { appointments });
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
          <MapContainer center={center} zoom={6} style={{ height: "100%", width: "100%" }} scrollWheelZoom>
            <TileLayer
              attribution='&copy; OpenStreetMap'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {routeLine && (
              <Polyline positions={routeLine} pathOptions={{ color: "#B23E00", weight: 3, dashArray: "6 6" }} />
            )}
            {plan?.origin && (
              <Marker position={[plan.origin.lat, plan.origin.lng]} icon={originIcon}>
                <Popup>
                  <div className="font-cabinet font-bold text-[14px]">Punto di partenza</div>
                  <div className="text-[11px] text-[#52525B] mt-1">{START_MODE_LABELS[plan.start_mode] || plan.origin.label}</div>
                </Popup>
              </Marker>
            )}
            {clients.map((c) => {
              const stopIndex = plan?.stops.findIndex((s) => s.client_id === c.id);
              const isInPlan = stopIndex !== undefined && stopIndex !== -1;
              return (
                <Marker key={c.id} position={[c.lat, c.lng]} icon={isInPlan ? numberedIcon(stopIndex + 1) : orangeIcon}>
                  <Popup>
                    <div className="font-cabinet font-bold text-[14px]">{c.company_name}</div>
                    <div className="text-[11px] text-[#52525B] mt-1">{c.city} ({c.province})</div>
                    <div className="text-[11px] text-[#52525B]">{c.sector}</div>
                    <Link to={`/app/clienti/${c.id}`} className="block mt-2 text-[11px] font-mono uppercase tracking-widest text-[#B23E00]">Apri scheda →</Link>
                  </Popup>
                </Marker>
              );
            })}
          </MapContainer>
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
              <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4">
                <div>
                  <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">
                    Clienti da visitare ({selectedIds.length} selezionati)
                  </label>
                  <div className="border border-[#E4E4E1] rounded-md max-h-64 overflow-y-auto divide-y divide-[#E4E4E1]">
                    {clients.map((c) => (
                      <label key={c.id} className="flex items-center gap-2 px-3 py-2 text-[13px] cursor-pointer hover:bg-[#F9F9F8]">
                        <input
                          type="checkbox"
                          data-testid={`plan-client-checkbox-${c.id}`}
                          checked={selectedIds.includes(c.id)}
                          onChange={() => toggleSelected(c.id)}
                        />
                        <span className="truncate">{c.company_name}</span>
                        <span className="text-[11px] text-[#6B6B72] ml-auto shrink-0">{c.city}</span>
                      </label>
                    ))}
                    {clients.length === 0 && (
                      <div className="px-3 py-4 text-[12px] text-[#6B6B72]">Nessun cliente geolocalizzato</div>
                    )}
                  </div>
                </div>

                <div>
                  <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Punto di partenza</label>
                  <select
                    data-testid="start-mode-select"
                    value={startMode}
                    onChange={(e) => setStartMode(e.target.value)}
                    className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]"
                  >
                    <option value="first_client">Primo cliente selezionato</option>
                    <option value="current_location">La mia posizione attuale (GPS)</option>
                    <option value="home" disabled={!homeReady}>Casa{!homeReady ? " (non impostata)" : ""}</option>
                    <option value="office" disabled={!officeReady}>Ufficio{!officeReady ? " (non impostato)" : ""}</option>
                    <option value="custom">Indirizzo personalizzato</option>
                  </select>
                  {(startMode === "home" && !homeReady) || (startMode === "office" && !officeReady) ? (
                    <div className="text-[11px] text-[#6B6B72] mt-1">
                      Configura l'indirizzo in <Link to="/app/impostazioni" className="text-[#B23E00] underline">Impostazioni → Punti di partenza</Link>.
                    </div>
                  ) : null}

                  {startMode === "current_location" && (
                    <div className="flex items-center gap-1.5 text-[11px] text-[#52525B] mt-1.5">
                      <LocateFixed className="w-3.5 h-3.5 shrink-0" /> Ti verrà chiesto il permesso di localizzazione al momento del calcolo.
                    </div>
                  )}

                  {startMode === "custom" && (
                    <div className="mt-2">
                      <div className="flex gap-2">
                        <input
                          value={customQuery}
                          onChange={(e) => { setCustomQuery(e.target.value); setCustomCoord(null); }}
                          onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); searchCustomAddress(); } }}
                          placeholder="Cerca indirizzo di partenza…"
                          data-testid="custom-start-address-input"
                          className="flex-1 bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]"
                        />
                        <button
                          type="button"
                          onClick={searchCustomAddress}
                          disabled={customSearching || customQuery.trim().length < 3}
                          className="shrink-0 flex items-center gap-1.5 px-3 py-2 bg-[#0A192F] text-white rounded-md text-[12px] font-medium disabled:opacity-50"
                        >
                          {customSearching ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                      {customResults.length > 0 && (
                        <div className="mt-2 border border-[#E4E4E1] rounded-md overflow-hidden bg-white">
                          {customResults.map((r, i) => (
                            <button
                              key={i}
                              type="button"
                              onClick={() => pickCustomAddress(r)}
                              className="w-full text-left px-3 py-2 text-[12px] hover:bg-[#F3F3F1] border-b border-[#E4E4E1] last:border-b-0 flex items-start gap-2"
                            >
                              <MapPin className="w-3.5 h-3.5 text-[#B23E00] shrink-0 mt-0.5" />
                              <span>{r.display_name}</span>
                            </button>
                          ))}
                        </div>
                      )}
                      {customCoord && (
                        <div className="text-[11px] text-[#059669] mt-1.5 flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3" /> Punto di partenza selezionato
                        </div>
                      )}
                    </div>
                  )}
                </div>

                <label className="flex items-center gap-2 text-[13px] cursor-pointer">
                  <input type="checkbox" checked={roundTrip} onChange={(e) => setRoundTrip(e.target.checked)} data-testid="round-trip-checkbox" />
                  Torna al punto di partenza a fine giornata
                </label>

                <div>
                  <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Data del giro</label>
                  <input type="date" value={planDate} onChange={(e) => setPlanDate(e.target.value)}
                         data-testid="plan-date-input"
                         className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Ora inizio</label>
                    <input type="time" value={startTime} onChange={(e) => setStartTime(e.target.value)}
                           className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
                  </div>
                  <div>
                    <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">Min. per visita</label>
                    <input type="number" min={5} step={5} value={visitMinutes} onChange={(e) => setVisitMinutes(e.target.value)}
                           className="w-full bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]" />
                  </div>
                </div>

                <button
                  data-testid="optimize-route-submit"
                  onClick={optimize}
                  disabled={busy || geoBusy}
                  className="w-full flex items-center justify-center gap-2 bg-[#B23E00] hover:bg-[#E04F00] text-white py-2.5 rounded-md text-[13px] font-medium disabled:opacity-50"
                >
                  {(busy || geoBusy) ? <Loader2 className="w-4 h-4 animate-spin" /> : <Navigation className="w-4 h-4" />}
                  {geoBusy ? "Rilevamento posizione…" : busy ? "Calcolo in corso…" : "Ottimizza giro"}
                </button>
              </div>
            )}

            {plan && (
              <div className="flex-1 min-h-0 flex flex-col">
                <div className="p-4 border-b border-[#E4E4E1] bg-[#F9F9F8]">
                  <div className="flex items-center gap-1.5 text-[11px] text-[#52525B] mb-1">
                    <MapPin className="w-3 h-3 shrink-0" />
                    Partenza: {START_MODE_LABELS[plan.start_mode] || "Primo cliente selezionato"}
                    {plan.round_trip && " · con ritorno al punto di partenza"}
                  </div>
                  <div className="flex items-center gap-1.5 text-[11px] text-[#52525B] mb-3">
                    <CalendarPlus className="w-3 h-3 shrink-0" />
                    Giorno: {new Date(`${planDate}T00:00:00`).toLocaleDateString("it-IT", { weekday: "long", day: "numeric", month: "long" })}
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-center mb-3">
                    <div>
                      <div className="font-cabinet font-black text-lg">{plan.total_distance_km}</div>
                      <div className="font-mono text-[9px] uppercase tracking-widest text-[#6B6B72]">km</div>
                    </div>
                    <div>
                      <div className="font-cabinet font-black text-lg">{plan.total_travel_minutes}</div>
                      <div className="font-mono text-[9px] uppercase tracking-widest text-[#6B6B72]">min. viaggio</div>
                    </div>
                    <div>
                      <div className="font-cabinet font-black text-lg">{plan.estimated_end_time}</div>
                      <div className="font-mono text-[9px] uppercase tracking-widest text-[#6B6B72]">fine stimata</div>
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center justify-between text-[11px] font-mono uppercase tracking-widest text-[#52525B] mb-1">
                      <span>Avanzamento</span>
                      <span data-testid="route-progress-count">{completedIds.length} / {plan.stops.length}</span>
                    </div>
                    <div className="h-1.5 bg-[#E4E4E1] rounded-full overflow-hidden">
                      <div className="h-full bg-[#B23E00] transition-all" style={{ width: `${(completedIds.length / plan.stops.length) * 100}%` }} />
                    </div>
                  </div>
                </div>

                {!plan.used_real_routing && (
                  <div className="px-4 py-2 text-[11px] text-[#6B6B72] bg-[#F9F9F8] border-b border-[#E4E4E1]">
                    Km e tempi sono una stima in linea d'aria (nessun servizio di routing configurato), non distanze reali su strada.
                  </div>
                )}

                {plan.warnings && plan.warnings.length > 0 && (
                  <div data-testid="route-warnings" className="px-4 py-2.5 text-[11px] text-[#DC2626] bg-[#DC2626]/5 border-b border-[#DC2626]/20 space-y-1">
                    {plan.warnings.map((w, i) => <div key={i}>⚠️ {w}</div>)}
                  </div>
                )}

                <div className="flex-1 min-h-0 overflow-y-auto divide-y divide-[#E4E4E1]">
                  {plan.stops.map((s, i) => {
                    const isDone = completedIds.includes(s.client_id);
                    const isCurrent = s.client_id === currentStopId;
                    return (
                      <div key={s.client_id} data-testid={`route-stop-${s.client_id}`}
                           className={`p-4 flex gap-3 ${s.suspicious_distance ? "bg-[#DC2626]/5" : isCurrent ? "bg-[#B23E00]/5 border-l-4 border-[#B23E00]" : ""} ${isDone ? "opacity-50" : ""}`}>
                        <div className={`w-6 h-6 rounded-full text-white text-[11px] font-bold flex items-center justify-center shrink-0 mt-0.5 ${isDone ? "bg-[#059669]" : "bg-[#0A192F]"}`}>
                          {isDone ? <CheckCircle2 className="w-3.5 h-3.5" /> : i + 1}
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <div className={`font-cabinet font-bold text-[13px] truncate ${isDone ? "line-through" : ""}`}>{s.company_name}</div>
                            {isCurrent && !isDone && (
                              <span className="font-mono text-[9px] uppercase tracking-widest text-[#B23E00] shrink-0">prossima tappa</span>
                            )}
                          </div>
                          <div className="text-[11px] text-[#52525B] flex items-center gap-1 mt-0.5">
                            <MapPin className="w-3 h-3 shrink-0" /> {s.city || s.address || "—"}
                          </div>
                          <div className={`text-[11px] flex items-center gap-1 mt-0.5 ${s.suspicious_distance ? "text-[#DC2626] font-medium" : "text-[#52525B]"}`}>
                            <Clock className="w-3 h-3 shrink-0" /> arrivo {s.eta} · uscita {s.departure}
                            {(i > 0 || plan.origin) && ` · ${s.distance_from_prev_km} km (${s.travel_minutes_from_prev} min)`}
                            {s.suspicious_distance && " ⚠️"}
                          </div>
                          <div className="flex items-center gap-2 mt-2">
                            <a
                              href={navigationUrl(s.lat, s.lng)}
                              target="_blank" rel="noopener noreferrer"
                              data-testid={`navigate-stop-${s.client_id}`}
                              className="flex items-center gap-1 px-2.5 py-1.5 bg-[#0A192F] text-white rounded text-[11px] font-medium"
                            >
                              <ExternalLink className="w-3 h-3" /> Naviga
                            </a>
                            <button
                              onClick={() => markVisited(s, isDone)}
                              data-testid={`mark-visited-${s.client_id}`}
                              className={`flex items-center gap-1 px-2.5 py-1.5 rounded text-[11px] font-medium border ${isDone ? "border-[#E4E4E1] text-[#52525B]" : "border-[#059669] text-[#059669]"}`}
                            >
                              {isDone ? <><RotateCcw className="w-3 h-3" /> Riapri</> : <><CheckCircle2 className="w-3 h-3" /> Segna come visitato</>}
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                  {plan.return_leg && (
                    <div data-testid="route-return-leg" className="p-4 flex gap-3 bg-[#F9F9F8]">
                      <div className="w-6 h-6 rounded-full text-white text-[11px] font-bold flex items-center justify-center shrink-0 mt-0.5 bg-[#0A192F]">
                        <RotateCcw className="w-3.5 h-3.5" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="font-cabinet font-bold text-[13px]">Ritorno al punto di partenza</div>
                        <div className="text-[11px] text-[#52525B] flex items-center gap-1 mt-0.5">
                          <Clock className="w-3 h-3 shrink-0" /> {plan.return_leg.distance_km} km ({plan.return_leg.travel_minutes} min)
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                <div className="p-4 border-t border-[#E4E4E1] space-y-2">
                  <button
                    onClick={saveToAgenda}
                    disabled={savingAgenda || savedToAgenda}
                    data-testid="save-route-to-agenda"
                    className="w-full flex items-center justify-center gap-2 bg-[#0A192F] hover:bg-[#172A45] text-white py-2.5 rounded-md text-[13px] font-medium disabled:opacity-50"
                  >
                    {savingAgenda ? <Loader2 className="w-4 h-4 animate-spin" /> : savedToAgenda ? <CheckCircle2 className="w-4 h-4" /> : <CalendarPlus className="w-4 h-4" />}
                    {savingAgenda ? "Salvataggio…" : savedToAgenda ? "Salvato in Agenda" : "Salva il giro in Agenda"}
                  </button>
                  <button onClick={resetPlan} className="w-full text-[12px] text-[#52525B] underline">
                    ← Nuova pianificazione
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

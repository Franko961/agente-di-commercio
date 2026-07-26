import { useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline } from "react-leaflet";
import L from "leaflet";
import { Link } from "react-router-dom";
import { Route, Loader2, X, MapPin, Clock, Navigation, ExternalLink, CheckCircle2, RotateCcw } from "lucide-react";
import { toast } from "sonner";
import api from "../api";

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
  const [startTime, setStartTime] = useState(stored?.startTime || "09:00");
  const [visitMinutes, setVisitMinutes] = useState(stored?.visitMinutes || 30);
  const [plan, setPlan] = useState(stored?.plan || null);
  // Tappe già visitate, segnate a mano dall'agente (vedi markVisited): non
  // c'è modo affidabile di rilevarlo in automatico via GPS se per navigare
  // si usa Google Maps in un'altra app, quindi resta un tocco manuale.
  const [completedIds, setCompletedIds] = useState(stored?.completedIds || []);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    saveStoredRoutePlan({ planOpen, selectedIds, startTime, visitMinutes, plan, completedIds });
  }, [planOpen, selectedIds, startTime, visitMinutes, plan, completedIds]);

  useEffect(() => { api.get("/clients").then(({ data }) => setClients(data.filter(c => isValidCoord(c.lat, c.lng)))); }, []);

  const center = clients.length ? [clients[0].lat, clients[0].lng] : [44.5, 11.0];

  const toggleSelected = (id) => {
    setSelectedIds((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]);
  };

  const optimize = async () => {
    if (selectedIds.length === 0) {
      toast.error("Seleziona almeno un cliente da visitare");
      return;
    }
    setBusy(true);
    setPlan(null);
    setCompletedIds([]);
    try {
      const { data } = await api.post("/route-planning/optimize", {
        client_ids: selectedIds,
        start_time: startTime,
        visit_minutes: Number(visitMinutes) || 30,
      });
      setPlan(data);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Impossibile calcolare il giro visita");
    } finally {
      setBusy(false);
    }
  };

  const resetPlan = () => {
    setPlan(null);
    setSelectedIds([]);
    setCompletedIds([]);
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

  const routeLine = useMemo(
    () => plan ? plan.stops.map((s) => [s.lat, s.lng]) : null,
    [plan]
  );

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] md:h-screen">
      <div className="p-4 md:p-8 border-b border-[#E4E4E1] bg-white flex items-center justify-between gap-4 flex-wrap">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00] mb-1">Geolocalizzazione</div>
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

      <div className="flex-1 relative flex">
        <div className="flex-1 relative" data-testid="map-container">
          <MapContainer center={center} zoom={6} style={{ height: "100%", width: "100%" }} scrollWheelZoom>
            <TileLayer
              attribution='&copy; OpenStreetMap'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {routeLine && (
              <Polyline positions={routeLine} pathOptions={{ color: "#FF5A00", weight: 3, dashArray: "6 6" }} />
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
                    <Link to={`/app/clienti/${c.id}`} className="block mt-2 text-[11px] font-mono uppercase tracking-widest text-[#FF5A00]">Apri scheda →</Link>
                  </Popup>
                </Marker>
              );
            })}
          </MapContainer>
        </div>

        {planOpen && (
          <div data-testid="route-planner-panel" className="w-full sm:w-[380px] shrink-0 bg-white border-l border-[#E4E4E1] overflow-y-auto flex flex-col">
            <div className="p-4 border-b border-[#E4E4E1] flex items-center justify-between">
              <div className="font-cabinet font-bold text-[15px] flex items-center gap-2">
                <Route className="w-4 h-4 text-[#FF5A00]" /> Pianifica giornata
              </div>
              <button onClick={() => setPlanOpen(false)} className="text-[#A1A1AA] hover:text-[#0A0A0A]">
                <X className="w-4 h-4" />
              </button>
            </div>

            {!plan && (
              <div className="p-4 space-y-4">
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
                        <span className="text-[11px] text-[#A1A1AA] ml-auto shrink-0">{c.city}</span>
                      </label>
                    ))}
                    {clients.length === 0 && (
                      <div className="px-3 py-4 text-[12px] text-[#A1A1AA]">Nessun cliente geolocalizzato</div>
                    )}
                  </div>
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
                  disabled={busy}
                  className="w-full flex items-center justify-center gap-2 bg-[#FF5A00] hover:bg-[#E04F00] text-white py-2.5 rounded-md text-[13px] font-medium disabled:opacity-50"
                >
                  {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Navigation className="w-4 h-4" />}
                  {busy ? "Calcolo in corso…" : "Ottimizza giro"}
                </button>
              </div>
            )}

            {plan && (
              <div className="flex-1 flex flex-col">
                <div className="p-4 border-b border-[#E4E4E1] bg-[#F9F9F8]">
                  <div className="grid grid-cols-3 gap-2 text-center mb-3">
                    <div>
                      <div className="font-cabinet font-black text-lg">{plan.total_distance_km}</div>
                      <div className="font-mono text-[9px] uppercase tracking-widest text-[#A1A1AA]">km</div>
                    </div>
                    <div>
                      <div className="font-cabinet font-black text-lg">{plan.total_travel_minutes}</div>
                      <div className="font-mono text-[9px] uppercase tracking-widest text-[#A1A1AA]">min. viaggio</div>
                    </div>
                    <div>
                      <div className="font-cabinet font-black text-lg">{plan.estimated_end_time}</div>
                      <div className="font-mono text-[9px] uppercase tracking-widest text-[#A1A1AA]">fine stimata</div>
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center justify-between text-[11px] font-mono uppercase tracking-widest text-[#52525B] mb-1">
                      <span>Avanzamento</span>
                      <span data-testid="route-progress-count">{completedIds.length} / {plan.stops.length}</span>
                    </div>
                    <div className="h-1.5 bg-[#E4E4E1] rounded-full overflow-hidden">
                      <div className="h-full bg-[#FF5A00] transition-all" style={{ width: `${(completedIds.length / plan.stops.length) * 100}%` }} />
                    </div>
                  </div>
                </div>

                {!plan.used_real_routing && (
                  <div className="px-4 py-2 text-[11px] text-[#A1A1AA] bg-[#F9F9F8] border-b border-[#E4E4E1]">
                    Km e tempi sono una stima in linea d'aria (nessun servizio di routing configurato), non distanze reali su strada.
                  </div>
                )}

                {plan.warnings && plan.warnings.length > 0 && (
                  <div data-testid="route-warnings" className="px-4 py-2.5 text-[11px] text-[#DC2626] bg-[#DC2626]/5 border-b border-[#DC2626]/20 space-y-1">
                    {plan.warnings.map((w, i) => <div key={i}>⚠️ {w}</div>)}
                  </div>
                )}

                <div className="flex-1 overflow-y-auto divide-y divide-[#E4E4E1]">
                  {plan.stops.map((s, i) => {
                    const isDone = completedIds.includes(s.client_id);
                    const isCurrent = s.client_id === currentStopId;
                    return (
                      <div key={s.client_id} data-testid={`route-stop-${s.client_id}`}
                           className={`p-4 flex gap-3 ${s.suspicious_distance ? "bg-[#DC2626]/5" : isCurrent ? "bg-[#FF5A00]/5 border-l-4 border-[#FF5A00]" : ""} ${isDone ? "opacity-50" : ""}`}>
                        <div className={`w-6 h-6 rounded-full text-white text-[11px] font-bold flex items-center justify-center shrink-0 mt-0.5 ${isDone ? "bg-[#059669]" : "bg-[#0A192F]"}`}>
                          {isDone ? <CheckCircle2 className="w-3.5 h-3.5" /> : i + 1}
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <div className={`font-cabinet font-bold text-[13px] truncate ${isDone ? "line-through" : ""}`}>{s.company_name}</div>
                            {isCurrent && !isDone && (
                              <span className="font-mono text-[9px] uppercase tracking-widest text-[#FF5A00] shrink-0">prossima tappa</span>
                            )}
                          </div>
                          <div className="text-[11px] text-[#52525B] flex items-center gap-1 mt-0.5">
                            <MapPin className="w-3 h-3 shrink-0" /> {s.city || s.address || "—"}
                          </div>
                          <div className={`text-[11px] flex items-center gap-1 mt-0.5 ${s.suspicious_distance ? "text-[#DC2626] font-medium" : "text-[#52525B]"}`}>
                            <Clock className="w-3 h-3 shrink-0" /> arrivo {s.eta} · uscita {s.departure}
                            {i > 0 && ` · ${s.distance_from_prev_km} km (${s.travel_minutes_from_prev} min)`}
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
                </div>

                <div className="p-4 border-t border-[#E4E4E1]">
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

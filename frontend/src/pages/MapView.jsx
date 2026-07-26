import { useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline } from "react-leaflet";
import L from "leaflet";
import { Link } from "react-router-dom";
import { Route, Loader2, X, MapPin, Clock, Navigation } from "lucide-react";
import { toast } from "sonner";
import api from "../api";

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

export default function MapView() {
  const [clients, setClients] = useState([]);
  const [planOpen, setPlanOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState([]);
  const [startTime, setStartTime] = useState("09:00");
  const [visitMinutes, setVisitMinutes] = useState(30);
  const [plan, setPlan] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { api.get("/clients").then(({ data }) => setClients(data.filter(c => c.lat && c.lng))); }, []);

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
                <div className="p-4 border-b border-[#E4E4E1] bg-[#F9F9F8] grid grid-cols-3 gap-2 text-center">
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

                {!plan.used_real_routing && (
                  <div className="px-4 py-2 text-[11px] text-[#A1A1AA] bg-[#F9F9F8] border-b border-[#E4E4E1]">
                    Km e tempi sono una stima in linea d'aria (nessun servizio di routing configurato), non distanze reali su strada.
                  </div>
                )}

                <div className="flex-1 overflow-y-auto divide-y divide-[#E4E4E1]">
                  {plan.stops.map((s, i) => (
                    <div key={s.client_id} data-testid={`route-stop-${s.client_id}`} className="p-4 flex gap-3">
                      <div className="w-6 h-6 rounded-full bg-[#0A192F] text-white text-[11px] font-bold flex items-center justify-center shrink-0 mt-0.5">
                        {i + 1}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="font-cabinet font-bold text-[13px] truncate">{s.company_name}</div>
                        <div className="text-[11px] text-[#52525B] flex items-center gap-1 mt-0.5">
                          <MapPin className="w-3 h-3 shrink-0" /> {s.city || s.address || "—"}
                        </div>
                        <div className="text-[11px] text-[#52525B] flex items-center gap-1 mt-0.5">
                          <Clock className="w-3 h-3 shrink-0" /> arrivo {s.eta} · uscita {s.departure}
                          {i > 0 && ` · ${s.distance_from_prev_km} km (${s.travel_minutes_from_prev} min)`}
                        </div>
                      </div>
                    </div>
                  ))}
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

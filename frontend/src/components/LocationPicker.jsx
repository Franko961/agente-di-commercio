import { useState } from "react";
import { MapContainer, TileLayer, Marker, useMapEvents } from "react-leaflet";
import L from "leaflet";
import { Search, Loader2, MapPin } from "lucide-react";
import api from "../api";

const orangeIcon = L.divIcon({
  className: "",
  html: '<div class="custom-pin"></div>',
  iconSize: [28, 28],
  iconAnchor: [14, 28],
});

const ITALY_CENTER = [42.5, 12.5];

// Coordinate al di fuori di questi limiti non sono fisicamente valide (una
// latitudine/longitudine reale sta sempre in questo intervallo). Senza
// questo controllo, un valore corrotto (es. lat/lng invertite da un
// geocoding finito su un omonimo altrove, o un dato salvato male) veniva
// passato così com'è a Leaflet: a zoom alto, Leaflet prova a calcolare la
// griglia di tile per quel punto e può arrivare a esaurire la memoria del
// browser (crash "Out of Memory" osservato in produzione), invece di
// limitarsi a non mostrare un pin.
function isValidCoord(lat, lng) {
  return (
    typeof lat === "number" && typeof lng === "number" &&
    Number.isFinite(lat) && Number.isFinite(lng) &&
    lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180
  );
}

// Ascolta i click sulla mappa e li inoltra al genitore: react-leaflet non
// espone un prop onClick diretto su MapContainer per questo caso, va fatto
// con un figlio "invisibile" che si aggancia agli eventi della mappa.
function ClickToPlace({ onPick }) {
  useMapEvents({
    click(e) {
      onPick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

/**
 * Alternativa all'inserimento manuale di latitudine/longitudine: l'utente
 * può cercare un indirizzo (geocodificato tramite Nominatim/OpenStreetMap,
 * nessuna chiave API richiesta) oppure posizionare/trascinare un pin
 * direttamente sulla mappa. Le coordinate numeriche restano visibili in
 * basso solo come riferimento, non richiedono più di essere digitate.
 */
export default function LocationPicker({ address, city, province, lat, lng, onChange }) {
  const [query, setQuery] = useState([address, city, province].filter(Boolean).join(", "));
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [searched, setSearched] = useState(false);

  const hasPosition = isValidCoord(lat, lng);
  const center = hasPosition ? [lat, lng] : ITALY_CENTER;

  const search = async () => {
    if (query.trim().length < 3) return;
    setSearching(true);
    setSearched(false);
    try {
      const { data } = await api.get("/geocode", { params: { q: query.trim() } });
      setResults(data);
    } catch {
      setResults([]);
    } finally {
      setSearching(false);
      setSearched(true);
    }
  };

  const pick = (r) => {
    onChange(r.lat, r.lng);
    setResults([]);
  };

  return (
    <div>
      <label className="font-mono text-[10px] uppercase tracking-widest text-[#52525B] block mb-1.5">
        Posizione (per la mappa clienti)
      </label>

      <div className="flex gap-2 mb-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); search(); } }}
          placeholder="Cerca indirizzo…"
          className="flex-1 bg-white border border-[#E4E4E1] rounded-md px-3 py-2 text-[13px]"
        />
        <button
          type="button"
          onClick={search}
          disabled={searching || query.trim().length < 3}
          className="shrink-0 flex items-center gap-1.5 px-3 py-2 bg-[#0A192F] text-white rounded-md text-[12px] font-medium disabled:opacity-50"
        >
          {searching ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
          Cerca
        </button>
      </div>

      {results.length > 0 && (
        <div className="mb-2 border border-[#E4E4E1] rounded-md overflow-hidden bg-white">
          {results.map((r, i) => (
            <button
              key={i}
              type="button"
              onClick={() => pick(r)}
              className="w-full text-left px-3 py-2 text-[12px] hover:bg-[#F3F3F1] border-b border-[#E4E4E1] last:border-b-0 flex items-start gap-2"
            >
              <MapPin className="w-3.5 h-3.5 text-[#FF5A00] shrink-0 mt-0.5" />
              <span>{r.display_name}</span>
            </button>
          ))}
        </div>
      )}
      {searched && results.length === 0 && !searching && (
        <div className="mb-2 text-[12px] text-[#A1A1AA]">
          Nessun indirizzo trovato — prova a semplificarlo, oppure posiziona il pin direttamente sulla mappa qui sotto.
        </div>
      )}

      <div className="rounded-md overflow-hidden border border-[#E4E4E1]" style={{ height: 220 }}>
        <MapContainer center={center} zoom={hasPosition ? 15 : 5} style={{ height: "100%", width: "100%" }} scrollWheelZoom={false}>
          <TileLayer attribution="&copy; OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <ClickToPlace onPick={onChange} />
          {hasPosition && (
            <Marker
              position={[lat, lng]}
              icon={orangeIcon}
              draggable
              eventHandlers={{
                dragend: (e) => {
                  const p = e.target.getLatLng();
                  onChange(p.lat, p.lng);
                },
              }}
            />
          )}
        </MapContainer>
      </div>
      <div className="text-[11px] text-[#A1A1AA] font-mono mt-1">
        {hasPosition
          ? <>Clicca sulla mappa o trascina il pin per correggere · {lat.toFixed(5)}, {lng.toFixed(5)}</>
          : "Clicca sulla mappa per posizionare il pin"}
      </div>
    </div>
  );
}

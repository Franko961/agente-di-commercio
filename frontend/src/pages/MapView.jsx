import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import { Link } from "react-router-dom";
import api from "../api";

// Custom marker
const orangeIcon = L.divIcon({
  className: "",
  html: '<div class="custom-pin"></div>',
  iconSize: [28, 28],
  iconAnchor: [14, 28],
});

export default function MapView() {
  const [clients, setClients] = useState([]);
  useEffect(() => { api.get("/clients").then(({ data }) => setClients(data.filter(c => c.lat && c.lng))); }, []);

  const center = clients.length ? [clients[0].lat, clients[0].lng] : [44.5, 11.0];

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] md:h-screen">
      <div className="p-4 md:p-8 border-b border-[#E4E4E1] bg-white">
        <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#FF5A00] mb-1">Geolocalizzazione</div>
        <h1 className="font-cabinet font-black text-2xl md:text-3xl tracking-tight">Mappa Clienti</h1>
        <p className="text-[13px] text-[#52525B] mt-1">{clients.length} clienti geolocalizzati</p>
      </div>
      <div className="flex-1 relative" data-testid="map-container">
        <MapContainer center={center} zoom={6} style={{ height: "100%", width: "100%" }} scrollWheelZoom>
          <TileLayer
            attribution='&copy; OpenStreetMap'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {clients.map((c) => (
            <Marker key={c.id} position={[c.lat, c.lng]} icon={orangeIcon}>
              <Popup>
                <div className="font-cabinet font-bold text-[14px]">{c.company_name}</div>
                <div className="text-[11px] text-[#52525B] mt-1">{c.city} ({c.province})</div>
                <div className="text-[11px] text-[#52525B]">{c.sector}</div>
                <Link to={`/clienti/${c.id}`} className="block mt-2 text-[11px] font-mono uppercase tracking-widest text-[#FF5A00]">Apri scheda →</Link>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </div>
  );
}

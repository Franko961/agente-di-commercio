import { MapContainer, TileLayer, Marker, Popup, Polyline } from "react-leaflet";
// Vedi il commento in LocationPicker.jsx: importato qui invece che come
// @import globale così finisce nel chunk lazy di questa pagina, non nel
// bundle caricato da ogni pagina pubblica.
import "leaflet/dist/leaflet.css";
import { Link } from "react-router-dom";
import { START_MODE_LABELS, orangeIcon, numberedIcon, originIcon } from "./constants";

export default function ClientsMap({ center, clients, plan, routeLine }) {
  return (
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
  );
}

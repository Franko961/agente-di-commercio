import { Link } from "react-router-dom";
import { Loader2, MapPin, Navigation, LocateFixed, Search, CheckCircle2 } from "lucide-react";

export default function RoutePlannerForm({
  clients, selectedIds, toggleSelected,
  startMode, setStartMode, homeReady, officeReady,
  customQuery, setCustomQuery, customCoord, setCustomCoord, customResults, customSearching, searchCustomAddress, pickCustomAddress,
  roundTrip, setRoundTrip,
  planDate, setPlanDate, startTime, setStartTime, visitMinutes, setVisitMinutes,
  optimize, busy, geoBusy,
}) {
  return (
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
  );
}

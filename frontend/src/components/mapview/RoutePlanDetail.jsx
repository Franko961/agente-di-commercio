import { Loader2, MapPin, Clock, ExternalLink, CheckCircle2, RotateCcw, CalendarPlus } from "lucide-react";
import { START_MODE_LABELS, navigationUrl } from "./constants";

export default function RoutePlanDetail({
  plan, planDate, completedIds, currentStopId, markVisited,
  saveToAgenda, savingAgenda, savedToAgenda, resetPlan,
}) {
  return (
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
  );
}

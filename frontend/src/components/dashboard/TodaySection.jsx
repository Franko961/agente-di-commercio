import { Link } from "react-router-dom";
import { format } from "date-fns";
import { it } from "date-fns/locale";
import { Calendar, PhoneCall, AlertTriangle, Banknote, Navigation, Target, Sparkles, ArrowRight } from "lucide-react";
import { fmt, focusClientSentence, projectionSentence } from "./constants";

function TodayStat({ to, icon: Icon, value, label }) {
  return (
    <Link to={to} className="flex items-center gap-3 py-3 px-3 rounded-md hover:bg-[#F3F3F1] transition-colors">
      <div className="w-9 h-9 rounded-md bg-[#F3F3F1] flex items-center justify-center shrink-0">
        <Icon className="w-4 h-4 text-[#0A192F]" strokeWidth={1.75} />
      </div>
      <div className="min-w-0">
        <div className="font-cabinet font-black text-xl leading-none">{value}</div>
        <div className="text-[11px] text-[#52525B] mt-1 truncate">{label}</div>
      </div>
    </Link>
  );
}

export default function TodaySection({ today }) {
  return (
    <div className="bg-white border border-[#E4E4E1] rounded-md fade-up">
      <div className="px-5 pt-5 flex items-center justify-between">
        <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#B23E00]">
          Oggi · {format(new Date(), "EEEE d MMMM", { locale: it })}
        </div>
      </div>
      <div className="px-2 md:px-3 py-2 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-1">
        <TodayStat to="/app/agenda" icon={Calendar} value={today.appointments_today} label={today.appointments_today === 1 ? "appuntamento" : "appuntamenti"} />
        <TodayStat to="/app/clienti" icon={PhoneCall} value={today.clients_to_call} label={today.clients_to_call === 1 ? "cliente da richiamare" : "clienti da richiamare"} />
        <TodayStat to="/app/offerte" icon={AlertTriangle} value={today.offers_expiring} label={today.offers_expiring === 1 ? "offerta in scadenza" : "offerte in scadenza"} />
        <TodayStat to="/app/provvigioni" icon={Banknote} value={today.payments_to_verify} label={today.payments_to_verify === 1 ? "pagamento da verificare" : "pagamenti da verificare"} />
        <TodayStat to="/app/mappa" icon={Navigation} value={today.km_today != null ? `${today.km_today} km` : "—"} label="km previsti" />
        <TodayStat to="/app/provvigioni" icon={Target} value={fmt(today.daily_goal)} label="obiettivo del giorno" />
      </div>
      {(focusClientSentence(today.focus_client) || projectionSentence(today)) && (
        <div className="mx-4 mb-4 mt-1 flex items-start gap-2.5 bg-[#FFF7ED] border border-[#FED7AA] rounded-md px-4 py-3">
          <Sparkles className="w-4 h-4 text-[#B23E00] shrink-0 mt-0.5" />
          <div className="text-[13px] text-[#0A0A0A] leading-snug space-y-1">
            <span className="font-mono text-[10px] uppercase tracking-widest text-[#B23E00] block mb-1">Suggerimento AI</span>
            {focusClientSentence(today.focus_client) && <div>{focusClientSentence(today.focus_client)}</div>}
            {projectionSentence(today) && <div>{projectionSentence(today)}</div>}
          </div>
          {today.focus_client?.client_id && (
            <Link to={`/app/clienti/${today.focus_client.client_id}`} className="ml-auto shrink-0 mt-0.5">
              <ArrowRight className="w-4 h-4 text-[#B23E00]" />
            </Link>
          )}
        </div>
      )}
    </div>
  );
}

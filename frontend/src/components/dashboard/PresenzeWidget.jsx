import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { getAttendanceTodaySummary } from "../../api/attendance";

// Widget compatto "Presenze oggi": quanti dipendenti attesi in turno oggi
// hanno già timbrato (vedi attendance_service.today_summary) — mostrato sia
// nella home semplificata (nessun modulo core, es. CACI SRL) sia nella
// dashboard di vendita completa, per chi ha ANCHE il modulo Personale
// attivo. Fetch autonomo (non dipende da /dashboard/stats, che gli account
// senza moduli core non chiamano nemmeno) apposta per funzionare in
// entrambi i contesti senza duplicare la logica.
export default function PresenzeWidget() {
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    getAttendanceTodaySummary().then(setSummary).catch(() => {});
  }, []);

  // Nessun dipendente registrato: il widget non aggiungerebbe informazione utile.
  if (!summary || summary.total_active === 0) return null;

  return (
    <Link to="/app/presenze" data-testid="presenze-widget"
      className="bg-white border border-[#E4E4E1] rounded-md p-5 flex items-center justify-between gap-4 hover:border-[#0A192F] transition-colors fade-up">
      <div>
        <div className="font-mono text-[10px] uppercase tracking-widest text-[#6B6B72] mb-1">Presenze oggi</div>
        {summary.expected_today > 0 ? (
          <div className="font-cabinet font-black text-2xl text-[#0A0A0A]">
            {summary.clocked_today}/{summary.expected_today}
            <span className="ml-2 text-[13px] font-normal text-[#52525B]">dipendenti hanno timbrato</span>
          </div>
        ) : (
          <div className="text-[14px] text-[#52525B]">Nessun dipendente in turno oggi</div>
        )}
      </div>
      <ArrowRight className="w-4 h-4 text-[#B23E00] shrink-0" />
    </Link>
  );
}

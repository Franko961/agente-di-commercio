import { useEffect, useState, Fragment } from "react";
import { ChevronLeft, ChevronRight, ChevronDown } from "lucide-react";
import DayDetailSheet from "../DayDetailSheet";
import {
  ALL_TYPE_LABELS, ALL_TYPE_COLORS, ALL_TYPE_ICONS, TYPE_COLORS, PRESENTE_COLOR,
  daysInMonthCount, dayIso, isWeekend, shiftIso, isFerieExcludedDay,
} from "./constants";

// Vista a griglia (dipendenti sulle righe, giorni del mese sulle colonne)
// pensata per aziende con diversi dipendenti (es. CACI SRL, ~40): la
// precedente semplice lista mensile non dava un colpo d'occhio su chi è
// assente quando, né segnalava sovrapposizioni. `rows` sono le richieste
// APPROVATE del mese già filtrate dal backend (vedi
// leave_request_service.calendar, include anche i tipi in ADMIN_TYPE_LABELS
// perché il backend le tratta in modo generico); `hoursRows` sono le ore
// lavorate dal chiosco di timbratura nello stesso mese (vedi
// attendance_service.calendar); `expectedRows` sono le ore ATTESE da orario
// contrattuale nello stesso mese (vedi attendance_service.expected_hours,
// presenti solo per i dipendenti che hanno compilato anche la fine turno) —
// tutto il resto è calcolato qui. `onChanged` ricarica questi tre dataset
// dopo una modifica fatta dal pannello giorno (DayDetailSheet).
export default function AbsenceCalendarGrid({ employees, month, rows, hoursRows, expectedRows, ferieCountMode, onChanged }) {
  const [viewMode, setViewMode] = useState("mensile");
  const [weekOffset, setWeekOffset] = useState(0);
  const [collapsedGroups, setCollapsedGroups] = useState(() => new Set());
  const [selectedDay, setSelectedDay] = useState(null); // { employeeId, employeeName, date }

  useEffect(() => { setWeekOffset(0); }, [month]);

  const activeEmployees = employees.filter((e) => e.active);

  if (activeEmployees.length === 0) {
    return (
      <div className="bg-white border border-[#E4E4E1] rounded-md p-8 text-center text-[#6B6B72] text-[13px]">
        Nessun dipendente attivo registrato.
      </div>
    );
  }

  const dayCount = daysInMonthCount(month);
  const days = Array.from({ length: dayCount }, (_, i) => i + 1);
  const maxWeekOffset = Math.max(0, Math.ceil(dayCount / 7) - 1);
  const visibleDays = viewMode === "settimanale" ? days.slice(weekOffset * 7, weekOffset * 7 + 7) : days;

  const byEmployee = {};
  rows.forEach((r) => {
    (byEmployee[r.employee_id] ||= []).push(r);
  });
  const covering = (employeeId, iso) =>
    (byEmployee[employeeId] || []).filter((r) => {
      if (r.date_from > iso || r.date_to < iso) return false;
      if (r.type === "ferie" && isFerieExcludedDay(ferieCountMode, iso)) return false;
      return true;
    });

  // Ore lavorate dal chiosco di timbratura (vedi attendance_service.calendar):
  // una mappa "employeeId|data" -> ore, per un accesso O(1) per cella.
  const hoursByKey = {};
  (hoursRows || []).forEach((r) => { hoursByKey[`${r.employee_id}|${r.date}`] = r.hours; });

  // Ore ATTESE da orario contrattuale (vedi attendance_service.expected_hours):
  // stessa mappa, usata per confrontare reale vs atteso sui giorni senza
  // assenza. Solo i giorni odierni/passati vengono evidenziati come
  // scostamento: un giorno futuro ha legittimamente 0 ore reali finché non
  // arriva, non è un allarme.
  const expectedByKey = {};
  (expectedRows || []).forEach((r) => { expectedByKey[`${r.employee_id}|${r.date}`] = r.hours; });
  const now = new Date();
  const todayIso = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;

  const absentCountByDay = days.map((day) => {
    const iso = dayIso(month, day);
    return activeEmployees.filter((e) => covering(e.id, iso).length > 0).length;
  });

  // Raggruppamento per reparto (models.employee.department, testo libero):
  // se nessun dipendente ne ha impostato uno, resta la lista piatta di
  // sempre — niente intestazioni di gruppo per chi non usa questo campo.
  const groupMap = {};
  activeEmployees.forEach((e) => { (groupMap[e.department || ""] ||= []).push(e); });
  const groupKeys = Object.keys(groupMap);
  const hasGroups = groupKeys.length > 1 || (groupKeys.length === 1 && groupKeys[0] !== "");
  const orderedGroupKeys = hasGroups
    ? [...groupKeys].sort((a, b) => (a === "" ? 1 : b === "" ? -1 : a.localeCompare(b)))
    : [""];

  const toggleGroup = (key) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  };

  const monthStartIso = dayIso(month, 1);
  const monthEndIso = dayIso(month, dayCount);

  return (
    <div>
      <div className="flex items-center justify-between mb-3 gap-3 flex-wrap">
        <div className="flex flex-wrap items-center gap-4 text-[11px] text-[#52525B]">
          {Object.entries(ALL_TYPE_LABELS).map(([key, label]) => {
            const Icon = ALL_TYPE_ICONS[key];
            return (
              <div key={key} className="flex items-center gap-1.5">
                <span className="w-3.5 h-3.5 rounded-full inline-flex items-center justify-center" style={{ background: ALL_TYPE_COLORS[key] }}>
                  {Icon ? <Icon className="w-2 h-2 text-white" strokeWidth={3} /> : null}
                </span>
                {label}
              </div>
            );
          })}
          <div className="flex items-center gap-1.5">
            <span className="w-3.5 h-3.5 rounded-full inline-block" style={{ background: PRESENTE_COLOR }} />
            Presente
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3.5 h-3.5 rounded-full inline-block ring-2 ring-violet-500 ring-inset" style={{ background: TYPE_COLORS.ferie }} />
            Sovrapposizione
          </div>
          <div className="flex items-center gap-1.5">
            <span className="font-mono text-[10px] text-red-600">6/8</span>
            Ore reali/attese (se sotto l'orario contrattuale)
          </div>
        </div>
        <div className="flex items-center border border-[#E4E4E1] rounded-md overflow-hidden text-[11px] font-medium shrink-0">
          <button onClick={() => setViewMode("mensile")}
            className={`px-3 py-1.5 ${viewMode === "mensile" ? "bg-[#0A192F] text-white" : "bg-white text-[#52525B] hover:bg-[#F9F9F8]"}`}>
            Mensile
          </button>
          <button onClick={() => setViewMode("settimanale")}
            className={`px-3 py-1.5 border-l border-[#E4E4E1] ${viewMode === "settimanale" ? "bg-[#0A192F] text-white" : "bg-white text-[#52525B] hover:bg-[#F9F9F8]"}`}>
            Settimanale
          </button>
        </div>
      </div>

      {viewMode === "settimanale" && (
        <div className="flex items-center gap-3 mb-3">
          <button onClick={() => setWeekOffset((w) => Math.max(0, w - 1))} disabled={weekOffset === 0}
            className="p-1.5 border border-[#E4E4E1] rounded-md hover:border-[#0A192F] disabled:opacity-30">
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
          <span className="text-[12px] text-[#52525B]">
            {dayIso(month, visibleDays[0])} → {dayIso(month, visibleDays[visibleDays.length - 1])}
          </span>
          <button onClick={() => setWeekOffset((w) => Math.min(maxWeekOffset, w + 1))} disabled={weekOffset === maxWeekOffset}
            className="p-1.5 border border-[#E4E4E1] rounded-md hover:border-[#0A192F] disabled:opacity-30">
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      <div className="overflow-x-auto border border-[#E4E4E1] rounded-md bg-white">
        <table className="border-collapse text-[11px]">
          <thead>
            <tr>
              <th className="sticky left-0 z-10 bg-white border-b border-r border-[#E4E4E1] px-3 py-2 text-left font-mono text-[10px] uppercase tracking-widest text-[#52525B] min-w-[150px]">
                Dipendente
              </th>
              {visibleDays.map((day) => (
                <th key={day}
                  className={`border-b border-[#E4E4E1] w-7 text-center font-mono text-[10px] py-2 ${isWeekend(month, day) ? "bg-[#F9F9F8] text-[#6B6B72]" : "text-[#52525B]"}`}>
                  {day}
                </th>
              ))}
            </tr>
            <tr>
              <th className="sticky left-0 z-10 bg-white border-b border-r border-[#E4E4E1] px-3 py-1 text-left font-mono text-[10px] text-[#6B6B72] whitespace-nowrap">
                Assenti / {activeEmployees.length}
              </th>
              {visibleDays.map((day) => {
                const count = absentCountByDay[day - 1];
                return (
                  <th key={day}
                    className={`border-b border-[#E4E4E1] text-center font-mono text-[10px] py-1 ${count > 0 ? "text-[#B23E00] font-bold" : "text-[#D4D4D1]"}`}>
                    {count || "–"}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {orderedGroupKeys.map((key) => {
              const groupEmployees = hasGroups ? groupMap[key] : activeEmployees;
              const collapsed = hasGroups && collapsedGroups.has(key);
              return (
                <Fragment key={key || "_nessuno"}>
                  {hasGroups && (
                    <tr>
                      <td colSpan={visibleDays.length + 1} className="bg-[#F9F9F8] border-b border-[#E4E4E1] px-3 py-1.5">
                        <button onClick={() => toggleGroup(key)} className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-widest text-[#52525B]">
                          <ChevronDown className={`w-3 h-3 transition-transform ${collapsed ? "-rotate-90" : ""}`} />
                          {key || "Non assegnato"} <span className="text-[#6B6B72]">({groupEmployees.length})</span>
                        </button>
                      </td>
                    </tr>
                  )}
                  {!collapsed && groupEmployees.map((emp) => (
                    <tr key={emp.id}>
                      <td className="sticky left-0 z-10 bg-white border-r border-b border-[#E4E4E1] px-3 py-1 font-medium whitespace-nowrap">
                        {emp.name}
                      </td>
                      {visibleDays.map((day) => {
                        const iso = dayIso(month, day);
                        const matches = covering(emp.id, iso);
                        const weekend = isWeekend(month, day);
                        const hours = hoursByKey[`${emp.id}|${iso}`];
                        const expected = expectedByKey[`${emp.id}|${iso}`];
                        const openDay = () => setSelectedDay({ employeeId: emp.id, employeeName: emp.name, date: iso });
                        // Sotto l'orario contrattuale evidenziato in rosso SOLO
                        // per oggi/giorni passati: un giorno futuro ha
                        // legittimamente 0 ore reali finché non arriva, non è
                        // uno scostamento da segnalare.
                        const shortfall = expected != null && iso <= todayIso && (hours || 0) < expected;

                        if (matches.length === 0) {
                          const content = expected != null ? `${hours || 0}/${expected}` : (hours || null);
                          const cellTitle = expected != null ? `${hours || 0}h reali su ${expected}h attese` : undefined;
                          // Presente = almeno un'ora registrata dal chiosco di
                          // timbratura in questo giorno: riempimento verde come
                          // le celle di assenza, con anello rosso se sotto
                          // l'orario atteso (stesso linguaggio visivo della
                          // sovrapposizione).
                          if (hours) {
                            return (
                              <td key={day} title={cellTitle} onClick={openDay} className="border-b border-[#E4E4E1] w-7 h-7 p-0.5 cursor-pointer">
                                <div className={`w-full h-full rounded-sm flex items-center justify-center ${shortfall ? "ring-2 ring-red-500 ring-inset" : ""}`}
                                  style={{ background: PRESENTE_COLOR }}>
                                  <span className="font-mono text-[8px] text-white/90">{content}</span>
                                </div>
                              </td>
                            );
                          }
                          return (
                            <td key={day} title={cellTitle} onClick={openDay}
                              className={`border-b border-[#E4E4E1] w-7 h-7 text-center cursor-pointer hover:bg-[#F3F3F1] ${weekend ? "bg-[#F9F9F8]" : ""}`}>
                              {content ? (
                                <span className={`font-mono text-[9px] ${shortfall ? "text-red-600 font-bold" : "text-[#52525B]"}`}>{content}</span>
                              ) : null}
                            </td>
                          );
                        }

                        const conflict = matches.length > 1;
                        // Gli straordinari si SOMMANO alle ore lavorate,
                        // non le sostituiscono (vedi build_attendance_workbook
                        // lato export): il tooltip lo rende esplicito invece
                        // di limitarsi a elencare i tipi del giorno.
                        const straordinariHours = matches.filter((m) => m.type === "straordinari").reduce((sum, m) => sum + (m.hours || 0), 0);
                        const title = matches.map((m) => ALL_TYPE_LABELS[m.type] || m.type).join(" + ") + (
                          straordinariHours && hours
                            ? ` · ${hours}h lavorate + ${straordinariHours}h straordinari = ${hours + straordinariHours}h`
                            : hours ? ` · ${hours}h lavorate` : ""
                        );

                        // Un solo tipo di assenza e nessuna presenza quel
                        // giorno: riempimento pieno come prima (caso comune,
                        // comportamento invariato).
                        if (matches.length === 1 && !hours) {
                          return (
                            <td key={day} title={title} onClick={openDay} className="border-b border-[#E4E4E1] w-7 h-7 p-0.5 cursor-pointer">
                              <div className="w-full h-full rounded-sm" style={{ background: ALL_TYPE_COLORS[matches[0].type] }} />
                            </td>
                          );
                        }

                        // Più elementi lo stesso giorno (assenze sovrapposte,
                        // o un'assenza parziale insieme a ore lavorate):
                        // badge colorati impilati invece di un unico
                        // riempimento, per non perdere l'informazione che
                        // sono più cose diverse. L'anello viola segnala
                        // specificamente la sovrapposizione tra assenze.
                        return (
                          <td key={day} title={title} onClick={openDay} className="border-b border-[#E4E4E1] w-7 h-7 p-0.5 cursor-pointer">
                            <div className={`w-full h-full rounded-sm flex flex-wrap items-center justify-center gap-0.5 ${conflict ? "ring-2 ring-violet-500 ring-inset" : ""}`}>
                              {hours ? <span className="w-2 h-2 rounded-full" style={{ background: PRESENTE_COLOR }} /> : null}
                              {matches.map((m) => {
                                const Icon = ALL_TYPE_ICONS[m.type];
                                return (
                                  <span key={m.id} className="w-2.5 h-2.5 rounded-full flex items-center justify-center" style={{ background: ALL_TYPE_COLORS[m.type] }}>
                                    {Icon ? <Icon className="w-1.5 h-1.5 text-white" strokeWidth={3} /> : null}
                                  </span>
                                );
                              })}
                            </div>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      {selectedDay && (
        <DayDetailSheet
          employeeId={selectedDay.employeeId}
          employeeName={selectedDay.employeeName}
          date={selectedDay.date}
          requests={covering(selectedDay.employeeId, selectedDay.date)}
          canGoPrev={selectedDay.date > monthStartIso}
          canGoNext={selectedDay.date < monthEndIso}
          onNavigate={(delta) => setSelectedDay((d) => ({ ...d, date: shiftIso(d.date, delta) }))}
          onClose={() => setSelectedDay(null)}
          onChanged={onChanged}
        />
      )}
    </div>
  );
}

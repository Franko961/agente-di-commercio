import { Palmtree, Clock, Thermometer, Home, Car, Timer, Phone } from "lucide-react";

export const TYPE_LABELS = { ferie: "Ferie", permesso: "Permesso", malattia: "Malattia" };
export const TYPE_COLORS = { ferie: "#B23E00", permesso: "#0A192F", malattia: "#DC2626" };
// Tipi registrabili solo dal responsabile direttamente dal pannello giorno
// (vedi DayDetailSheet.jsx e backend/models/leave_request.py ADMIN_LEAVE_TYPES):
// a differenza di ferie/permesso/malattia non passano da richiesta+approvazione.
export const ADMIN_TYPE_LABELS = { smartworking: "Smartworking", trasferta: "Trasferta", straordinari: "Straordinari", reperibilita: "Reperibilità" };
export const ADMIN_TYPE_COLORS = { smartworking: "#D97706", trasferta: "#78350F", straordinari: "#DB2777", reperibilita: "#6366F1" };
export const ALL_TYPE_LABELS = { ...TYPE_LABELS, ...ADMIN_TYPE_LABELS };
export const ALL_TYPE_COLORS = { ...TYPE_COLORS, ...ADMIN_TYPE_COLORS };
export const ALL_TYPE_ICONS = { ferie: Palmtree, permesso: Clock, malattia: Thermometer, smartworking: Home, trasferta: Car, straordinari: Timer, reperibilita: Phone };
export const PRESENTE_COLOR = "#16A34A";

export function monthKeyToday() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export function daysInMonthCount(monthKey) {
  const [y, m] = monthKey.split("-").map(Number);
  return new Date(y, m, 0).getDate();
}

export function dayIso(monthKey, day) {
  const [y, m] = monthKey.split("-").map(Number);
  return `${y}-${String(m).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

export function isWeekend(monthKey, day) {
  const [y, m] = monthKey.split("-").map(Number);
  const dow = new Date(y, m - 1, day).getDay();
  return dow === 0 || dow === 6;
}

export function shiftIso(iso, delta) {
  const d = new Date(`${iso}T00:00:00`);
  d.setDate(d.getDate() + delta);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

// Algoritmo di Gauss/Meeus per la Pasqua — stesso algoritmo di
// backend/core/italian_holidays.py, duplicato qui apposta: pura matematica
// sulle date, nessuna chiamata API, stesso principio già usato da
// isWeekend() qui sopra.
function easterSunday(year) {
  const a = year % 19, b = Math.floor(year / 100), c = year % 100;
  const d = Math.floor(b / 4), e = b % 4, f = Math.floor((b + 8) / 25);
  const g = Math.floor((b - f + 1) / 3), h = (19 * a + b - d - g + 15) % 30;
  const i = Math.floor(c / 4), k = c % 4;
  const l = (32 + 2 * e + 2 * i - h - k) % 7;
  const m = Math.floor((a + 11 * h + 22 * l) / 451);
  const month = Math.floor((h + l - 7 * m + 114) / 31);
  const day = ((h + l - 7 * m + 114) % 31) + 1;
  return new Date(year, month - 1, day);
}
const ITALIAN_HOLIDAYS_FIXED = [[1, 1], [1, 6], [4, 25], [5, 1], [6, 2], [8, 15], [11, 1], [12, 8], [12, 25], [12, 26]];
export function isItalianHoliday(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  if (ITALIAN_HOLIDAYS_FIXED.some(([hm, hd]) => hm === m && hd === d)) return true;
  const pasquetta = easterSunday(y);
  pasquetta.setDate(pasquetta.getDate() + 1);
  return pasquetta.getFullYear() === y && pasquetta.getMonth() + 1 === m && pasquetta.getDate() === d;
}

// Un giorno di FERIE non va considerato "consumato" in base a
// ferie_count_mode dell'account (Impostazioni > Ferie, stessa logica di
// leave_request_service._days_in_year lato backend): "lavorativi" esclude
// sabato e domenica, "festivita" esclude solo domenica e le festività
// nazionali italiane (sabato incluso). Non si applica ad altri tipi
// (permesso/malattia/ecc. restano sempre a calendario pieno).
export function isFerieExcludedDay(mode, iso) {
  if (mode === "calendario") return false;
  const dow = new Date(`${iso}T00:00:00`).getDay(); // 0=domenica … 6=sabato
  if (mode === "lavorativi") return dow === 0 || dow === 6;
  return dow === 0 || isItalianHoliday(iso);
}

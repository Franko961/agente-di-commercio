import api from "../api";

const FILE_BASE = import.meta.env.VITE_BACKEND_URL;

export async function downloadCsv(path, filename) {
  const res = await fetch(`${FILE_BASE}${path}`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export const exportClients = () => downloadCsv("/api/export/clients.csv", "clienti.csv");
export const exportOffers = () => downloadCsv("/api/export/offers.csv", "offerte.csv");
export const exportCommissions = () => downloadCsv("/api/export/commissions.csv", "provvigioni.csv");
export const exportLeads = () => downloadCsv("/api/export/leads.csv", "lead.csv");
export const exportLeaveRequests = () => downloadCsv("/api/leave-requests/export.csv", "assenze.csv");
export const exportAttendance = (month) => downloadCsv(`/api/attendance/export.xlsx?month=${month}`, `presenze_${month}.xlsx`);
// dateFrom/dateTo opzionali (formato YYYY-MM-DD): se assenti, il backend
// usa come default dal primo giorno del mese corrente a oggi (vedi
// ExportService.export_mandante_report). Il nome del file scaricato lo
// decide SOLO il client (download da un blob: URL, che non porta con sé
// il Content-Disposition della risposta originale) — mandanteName è
// opzionale solo per restare compatibile con eventuali altri chiamanti,
// ma va sempre passato quando disponibile per un nome file leggibile.
export const exportMandanteReport = (mandanteId, dateFrom, dateTo, mandanteName) => {
  const params = new URLSearchParams({ mandante_id: mandanteId });
  if (dateFrom) params.set("date_from", dateFrom);
  if (dateTo) params.set("date_to", dateTo);
  const safeName = mandanteName ? mandanteName.replace(/[^\w-]+/g, "-") : "mandante";
  const filename = `report-${safeName}${dateFrom ? `-${dateFrom}` : ""}${dateTo ? `_${dateTo}` : ""}.pdf`;
  return downloadCsv(`/api/export/mandante-report.pdf?${params}`, filename);
};

// WhatsApp click-to-chat helper
export function whatsappLink(phone, message = "") {
  if (!phone) return null;
  // Strip everything except digits and leading +
  const digits = phone.replace(/[^\d+]/g, "");
  // wa.me requires no '+' prefix
  const clean = digits.startsWith("+") ? digits.substring(1) : digits;
  return `https://wa.me/${clean}${message ? `?text=${encodeURIComponent(message)}` : ""}`;
}

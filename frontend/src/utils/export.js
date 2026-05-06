import api from "../api";

const FILE_BASE = process.env.REACT_APP_BACKEND_URL;

export async function downloadCsv(path, filename) {
  const token = localStorage.getItem("token");
  const res = await fetch(`${FILE_BASE}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
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

// WhatsApp click-to-chat helper
export function whatsappLink(phone, message = "") {
  if (!phone) return null;
  // Strip everything except digits and leading +
  const digits = phone.replace(/[^\d+]/g, "");
  // wa.me requires no '+' prefix
  const clean = digits.startsWith("+") ? digits.substring(1) : digits;
  return `https://wa.me/${clean}${message ? `?text=${encodeURIComponent(message)}` : ""}`;
}

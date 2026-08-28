export const fmt = (n) => new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(n || 0);

export const ORDER_STATUS_LABELS = {
  confermato: "Confermato", in_evasione: "In evasione", spedito: "Spedito",
  consegnato: "Consegnato", annullato: "Annullato", reso: "Reso",
};
export const ORDER_STATUS_COLORS = {
  confermato: "#0A192F", in_evasione: "#B45309", spedito: "#0EA5E9",
  consegnato: "#059669", annullato: "#DC2626", reso: "#DC2626",
};
export const PAYMENT_STATUS_LABELS = { non_pagato: "Non pagato", parziale: "Pagamento parziale", pagato: "Pagato" };
export const PAYMENT_STATUS_COLORS = { non_pagato: "#DC2626", parziale: "#B45309", pagato: "#059669" };

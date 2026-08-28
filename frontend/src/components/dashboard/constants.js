import { IdCard, Truck } from "lucide-react";
import { format, parseISO } from "date-fns";
import { it } from "date-fns/locale";

// Sottoinsieme di backend/core/security.py MODULE_KEYS: solo i moduli
// legati alla vendita vera e propria (i widget di questa dashboard —
// fatturato, pipeline, provvigioni, portafoglio — derivano tutti da
// questi). Se TUTTI sono disattivati per l'account, quella vista non ha
// senso da mostrare: non è un account che usa SalesFly come CRM per
// agenti di commercio (es. CACI SRL, che usa solo i moduli extra
// Personale/Flotta). Documenti, Automazioni e Assistente AI sono
// deliberatamente esclusi: sono strumenti generici che un account del
// genere può comunque voler tenere attivi senza per questo diventare un
// "agente di commercio". Vedi ExtraModulesHome.jsx per cosa vede al posto
// della dashboard di vendita.
export const CORE_MODULE_KEYS = [
  "clienti", "lead", "agenda", "mappa", "offerte", "ordini",
  "provvigioni", "spese", "mandanti", "prodotti",
];

// Allineato a backend/core/security.py EXTRA_MODULE_KEYS.
export const EXTRA_MODULE_META = {
  personale: { label: "Personale", desc: "Anagrafica dipendenti e richieste di ferie, permessi, malattie.", icon: IdCard, to: "/app/personale" },
  flotta: { label: "Flotta", desc: "Anagrafica mezzi, scadenze documentali, costi e carico merce.", icon: Truck, to: "/app/flotta" },
};

export const fmt = (n) => new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(n || 0);
export const EXPENSE_CATEGORY_LABELS = {
  carburante: "Carburante", vitto: "Vitto", alloggio: "Alloggio",
  pedaggio_parcheggio: "Pedaggio/Parcheggio", materiali: "Materiali",
  inps: "INPS", enasarco: "ENASARCO", assicurazione_auto: "Assicurazione auto",
  commercialista: "Commercialista", altro: "Altro",
};
// Colore fisso per categoria, coerente tra grafico mensile e grafico a torta
export const EXPENSE_CATEGORY_COLORS = {
  carburante: "#B23E00", vitto: "#059669", alloggio: "#7C3AED",
  pedaggio_parcheggio: "#0EA5E9", materiali: "#DC2626",
  inps: "#0A192F", enasarco: "#B45309", assicurazione_auto: "#DB2777",
  commercialista: "#65A30D", altro: "#6B6B72",
};
export const PIE_COLORS = ["#0A192F", "#172A45", "#52525B", "#B23E00", "#059669", "#DC2626"];

// "scade venerdì" se entro 6 giorni, altrimenti "scade 24 luglio"
export function formatExpiry(dateStr) {
  if (!dateStr) return "";
  const d = parseISO(dateStr);
  const diffDays = Math.round((d - new Date()) / 86400000);
  return diffDays <= 6 ? format(d, "EEEE", { locale: it }) : format(d, "d MMMM", { locale: it });
}

export function focusClientSentence(focus) {
  if (!focus) return null;
  if (focus.reason === "expiry_and_inactivity") {
    return `Visita prima ${focus.client_name}, perché non effettua ordini da ${focus.days_since_last_order} giorni e l'ultima offerta scade ${formatExpiry(focus.offer_expires_at)}.`;
  }
  if (focus.reason === "expiry_only") {
    return `Visita prima ${focus.client_name}: l'offerta "${focus.offer_title}" scade ${formatExpiry(focus.offer_expires_at)}.`;
  }
  if (focus.reason === "inactivity_only") {
    // days_since_last_visit è null quando il cliente non ha MAI avuto una
    // visita registrata (non solo "da tanti giorni") — vedi
    // dashboard_service.py, max_days == 9999 -> None.
    const daysPart = focus.days_since_last_visit != null
      ? `non lo senti da ${focus.days_since_last_visit} giorni`
      : "non hai ancora registrato nessuna visita con lui";
    return `Contatta ${focus.client_name}: ${daysPart}.`;
  }
  return null;
}

export function projectionSentence(today) {
  const pct = today?.projected_pct_if_expiring_closed;
  const n = today?.offers_expiring || 0;
  if (pct == null || n === 0) return null;
  const offerteLabel = n === 1 ? "l'offerta in scadenza" : `le ${n} offerte in scadenza`;
  return `Se chiudi ${offerteLabel} raggiungeresti il ${pct}% dell'obiettivo mensile.`;
}

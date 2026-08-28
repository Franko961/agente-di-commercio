export const fmt = (n) => new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(n || 0);
export const fmtUsd = (n) => `$${(n ?? 0).toFixed(4)}`;

export const STATUS_COLOR = {
  active: "#059669", trial: "#B23E00", cancelled: "#DC2626", expired: "#6B6B72"
};

// Valori allineati a backend/models/admin.py IMPERSONATION_CATEGORIES.
export const IMPERSONATE_CATEGORIES = [
  { value: "assistenza_richiesta", label: "Assistenza richiesta" },
  { value: "diagnosi_problema", label: "Diagnosi problema" },
  { value: "verifica_configurazione", label: "Verifica configurazione" },
  { value: "controllo_amministrativo", label: "Controllo amministrativo" },
];

// Valori allineati a backend/core/security.py MODULE_KEYS.
export const MODULES = [
  { value: "clienti", label: "Clienti" },
  { value: "lead", label: "Lead & Pipeline" },
  { value: "agenda", label: "Agenda" },
  { value: "mappa", label: "Mappa" },
  { value: "offerte", label: "Offerte" },
  { value: "ordini", label: "Ordini" },
  { value: "provvigioni", label: "Provvigioni" },
  { value: "spese", label: "Spese" },
  { value: "mandanti", label: "Mandanti" },
  { value: "prodotti", label: "Prodotti & Listini" },
  { value: "documenti", label: "Documenti" },
  { value: "automazioni", label: "Automazioni" },
  { value: "ai", label: "Assistente AI" },
];

// Valori allineati a backend/core/security.py EXTRA_MODULE_KEYS: moduli
// verticali costruiti per un cliente specifico (es. CACI SRL), spenti per
// tutti finché non attivati esplicitamente qui — logica opposta a MODULES
// sopra, vedi toggleExtraModule/saveModules in BusinessTab.jsx.
export const EXTRA_MODULES = [
  { value: "personale", label: "Personale (ferie, permessi, presenze)" },
  { value: "flotta", label: "Flotta (mezzi, scadenze, carico merce)" },
];

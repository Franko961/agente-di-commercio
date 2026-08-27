// Costanti/helper condivisi da più di un tab della scheda dipendente — quelli
// usati da un solo tab restano definiti nel file di quel tab.

export const EMPLOYMENT_STATUS_LABELS = { attivo: "Attivo", sospeso: "Sospeso", cessato: "Cessato" };
export const EMPLOYMENT_STATUS_COLORS = { attivo: "#059669", sospeso: "#B23E00", cessato: "#6B6B72" };

export const REQUEST_STATUS_LABELS = { in_attesa: "In attesa", approvata: "Approvata", rifiutata: "Rifiutata" };
export const REQUEST_STATUS_COLORS = { in_attesa: "#B23E00", approvata: "#059669", rifiutata: "#DC2626" };

export const FILE_BASE = import.meta.env.VITE_BACKEND_URL;
export const DOCUMENT_MAX_MB = 50;

// Estrae un messaggio leggibile da un errore API: FastAPI risponde con una
// stringa per un errore applicativo, ma con una LISTA di errori per un 422
// di Pydantic (es. i @model_validator su employee/employee_equipment/
// attendance) — senza questo l'utente vedeva solo un fallback generico e
// non capiva cosa correggere. Il prefisso "Value error, " è aggiunto
// automaticamente da Pydantic quando l'errore arriva da un model_validator
// che solleva ValueError.
export function formatApiError(err, fallback = "Salvataggio non riuscito") {
  const detail = err?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail.map((e) => (e?.msg || "").replace(/^Value error,\s*/, "")).filter(Boolean).join(" · ") || fallback;
  }
  return fallback;
}

import L from "leaflet";

// Etichette leggibili per ogni modalità di partenza, usate sia nel <select>
// sia per riassumere all'utente cosa è stato scelto una volta calcolato il
// giro (plan.start_mode arriva identico dal backend).
export const START_MODE_LABELS = {
  first_client: "Primo cliente selezionato",
  current_location: "La mia posizione attuale",
  home: "Casa",
  office: "Ufficio",
  custom: "Indirizzo personalizzato",
};

// Link universale di Google Maps: funziona su Android (apre l'app se
// installata), iOS (apre l'app Google Maps se installata, altrimenti
// Safari) e desktop (apre maps.google.com) con un'unica URL, senza dover
// distinguere il dispositivo. Le indicazioni vere e proprie — voce, traffico
// in tempo reale, ricalcolo se si sbaglia strada — restano tutte a carico di
// Google Maps: non ha senso provare a ricostruirle dentro SalesFly.
export function navigationUrl(lat, lng) {
  return `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}&travelmode=driving`;
}

// Stesso controllo di LocationPicker.jsx: una coordinata corrotta (fuori dai
// limiti geografici possibili) passata direttamente a Leaflet può portare a
// un crash "Out of Memory" del browser a certi livelli di zoom, invece di
// limitarsi a non mostrare quel marker.
export function isValidCoord(lat, lng) {
  return (
    typeof lat === "number" && typeof lng === "number" &&
    Number.isFinite(lat) && Number.isFinite(lng) &&
    lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180
  );
}

// Custom marker
export const orangeIcon = L.divIcon({
  className: "",
  html: '<div class="custom-pin"></div>',
  iconSize: [28, 28],
  iconAnchor: [14, 28],
});

export function numberedIcon(n) {
  return L.divIcon({
    className: "",
    html: `<div class="custom-pin custom-pin-numbered"><span>${n}</span></div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 28],
  });
}

// Marker distinto per il punto di partenza "virtuale" (posizione attuale,
// casa, ufficio o indirizzo personalizzato): non è una tappa da visitare,
// quindi non deve confondersi con i pin numerati dei clienti.
export const originIcon = L.divIcon({
  className: "",
  html: '<div class="custom-pin" style="background:#0A192F"></div>',
  iconSize: [28, 28],
  iconAnchor: [14, 28],
});

// La pianificazione del giro visita viene tenuta in sessionStorage (non solo
// nello stato del componente): senza questo, uscire dalla pagina Mappa per
// aprire una scheda cliente e poi tornare indietro faceva sparire il piano
// appena calcolato, perché React smonta il componente ad ogni cambio pagina
// e ne riparte da zero. sessionStorage sopravvive alla navigazione tra le
// pagine dell'app (si perde solo chiudendo la scheda/il browser, il che ha
// senso per un piano pensato per "la giornata di oggi").
export const ROUTE_PLAN_STORAGE_KEY = "salesfly:route-plan";

export function loadStoredRoutePlan() {
  try {
    const raw = sessionStorage.getItem(ROUTE_PLAN_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function saveStoredRoutePlan(state) {
  try {
    sessionStorage.setItem(ROUTE_PLAN_STORAGE_KEY, JSON.stringify(state));
  } catch {
    // sessionStorage può non essere disponibile (es. modalità privata con
    // restrizioni) — la pianificazione resta comunque utilizzabile per la
    // sessione corrente, semplicemente non sopravvive alla navigazione.
  }
}

// Data di calendario locale, non new Date().toISOString().slice(0,10): quel
// metodo legge anno/mese/giorno in UTC, che nell'ultima/prima ora o due del
// giorno locale (a seconda del fuso) può differire dalla data dell'utente —
// usato solo come default della data del giro pianificato, mai per salvare
// timestamp.
export const todayIso = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
};

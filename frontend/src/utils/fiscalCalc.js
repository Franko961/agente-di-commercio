// Calcolo di ritenuta d'acconto e contributo ENASARCO su una provvigione
// lorda — unica fonte della formula lato frontend, usata sia dal
// calcolatore "isolato" del blog (RitenutaEnasarcoCalculator.jsx, un
// numero inserito a mano) sia dal riepilogo fiscale reale nella pagina
// Provvigioni (che applica la stessa formula ai totali già calcolati dal
// sistema). Stessa logica, stesse aliquote, del backend
// (services/fiscal_calc.py) — le due copie esistono perché il blog deve
// restare 100% client-side (nessuna chiamata API da un articolo pubblico),
// mentre il riepilogo reale in app lavora su dati già caricati lato
// client: tenerle esplicitamente allineate è più semplice che introdurre
// una chiamata di rete solo per un calcolo aritmetico.
//
// Riferimenti normativi (verificati per l'articolo del blog "ritenuta
// d'acconto e contributi ENASARCO"):
// - Ritenuta d'acconto: art. 25-bis DPR 600/1973, aliquota nominale 23%,
//   su base 50% (ordinaria) o 20% (ridotta, richiede dichiarazione
//   formale al mandante entro il 31/12 dell'anno precedente).
// - Esenzione totale dalla ritenuta per il regime forfettario: L.
//   190/2014, comma 67.
// - Contributo ENASARCO 2026: 17% totale, 8,5% a carico dell'agente,
//   indipendente dal regime fiscale (forfettario incluso).
export const RITENUTA_ALIQUOTA = 0.23;
export const ENASARCO_QUOTA_AGENTE = 0.085;

// Arrotonda a 2 decimali con Math.round (non un semplice toFixed, che
// tronca): tiene i valori restituiti allineati a come li arrotonda il
// gemello Python (services/fiscal_calc.py usa round(x, 2) su ogni campo) —
// senza questo, un confronto diretto tra i due (es. un futuro endpoint che
// espone il calcolo Python allo stesso frontend) potrebbe mostrare un
// centesimo di differenza sullo stesso importo. I nomi dei campi restano
// invece camelCase qui e snake_case lato Python, per convenzione idiomatica
// di ciascun linguaggio — un eventuale endpoint che esponga il calcolo
// Python dovrà comunque tradurli, non è un refuso.
function round2(n) {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

export function computeFiscalBreakdown(lordo, regimeFiscale, baseRitenuta) {
  const lordoSafe = Math.max(0, lordo || 0);
  const baseImponibile =
    regimeFiscale === "ordinario" ? (baseRitenuta === "50" ? 0.5 : 0.2) : 0;
  const ritenuta = lordoSafe * baseImponibile * RITENUTA_ALIQUOTA;
  const enasarco = lordoSafe * ENASARCO_QUOTA_AGENTE;
  return {
    lordo: round2(lordoSafe),
    ritenutaAcconto: round2(ritenuta),
    contributoEnasarco: round2(enasarco),
    netto: round2(lordoSafe - ritenuta - enasarco),
  };
}

export function formatEuro(n) {
  return (n || 0).toLocaleString("it-IT", { style: "currency", currency: "EUR" });
}

// Converte un numero digitato in formato italiano (punto = separatore
// delle migliaia, virgola = decimale) in un float JS. Senza questo,
// parseFloat("15.000".replace(",", ".")) restituisce 15 invece di 15000,
// perché "." è già un punto decimale valido in JS — un refuso di tre
// ordini di grandezza, silenzioso, se l'utente digita l'importo con il
// formato italiano standard (es. "15.000" per quindicimila euro).
export function parseItalianNumber(str) {
  const normalized = String(str ?? "").replace(/\./g, "").replace(",", ".");
  return parseFloat(normalized) || 0;
}

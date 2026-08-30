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

export function computeFiscalBreakdown(lordo, regimeFiscale, baseRitenuta) {
  const lordoSafe = Math.max(0, lordo || 0);
  const baseImponibile =
    regimeFiscale === "ordinario" ? (baseRitenuta === "50" ? 0.5 : 0.2) : 0;
  const ritenuta = lordoSafe * baseImponibile * RITENUTA_ALIQUOTA;
  const enasarco = lordoSafe * ENASARCO_QUOTA_AGENTE;
  return {
    lordo: lordoSafe,
    ritenutaAcconto: ritenuta,
    contributoEnasarco: enasarco,
    netto: lordoSafe - ritenuta - enasarco,
  };
}

export function formatEuro(n) {
  return (n || 0).toLocaleString("it-IT", { style: "currency", currency: "EUR" });
}

export const fmt = (n) => new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(n || 0);
// Mese di calendario locale, non new Date().toISOString().slice(0,7): quel
// metodo legge l'anno/mese in UTC, che nell'ultima/prima ora o due del
// giorno locale (a seconda del fuso) può differire dal mese di calendario
// dell'utente — usato solo per determinare "il mese corrente" (default del
// box e periodo aperto di default), mai per salvare timestamp.
export const currentPeriod = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
};

// Più righe manuali possono coesistere sullo stesso periodo (es. un premio
// per un mandante e una rettifica per un altro nello stesso mese), quindi
// period fa parte della riga come gli altri campi, non è più un selettore
// esterno che determina quale riga stai modificando.
export const emptyManualForm = () => ({
  period: currentPeriod(), amount: "", mandante_id: "", client_id: "", descrizione: "", stato: "maturato", note: "", tipo: "ordinaria",
});

export function periodLabel(key) {
  const [y, m] = (key || "").split("-").map(Number);
  if (!y || !m) return key;
  const label = new Intl.DateTimeFormat("it-IT", { month: "long", year: "numeric" }).format(new Date(y, m - 1, 1));
  return label.charAt(0).toUpperCase() + label.slice(1);
}

// Raggruppa le provvigioni (già filtrate per cliente/stato) per periodo,
// stesso principio del raggruppamento mensile in Spese.jsx: il periodo
// corrente resta aperto di default, i periodi passati partono chiusi
// mostrando solo il totale. manualEntriesByPeriod arriva già filtrato per
// mandante/cliente attivi (vedi visibleManualCommissions) e può contenere
// PIÙ righe per lo stesso periodo (nessun vincolo di unicità lato backend).
export function groupByPeriod(list, manualEntriesByPeriod) {
  const byKey = new Map();
  for (const c of list) {
    const key = c.period || "—";
    if (!byKey.has(key)) byKey.set(key, []);
    byKey.get(key).push(c);
  }
  for (const period of Object.keys(manualEntriesByPeriod)) {
    if (!byKey.has(period)) byKey.set(period, []);
  }
  return [...byKey.entries()]
    .sort((a, b) => (a[0] < b[0] ? 1 : -1))
    .map(([key, items]) => {
      const manualEntries = manualEntriesByPeriod[key] || [];
      const manualSum = manualEntries.reduce((s, m) => s + (m.amount || 0), 0);
      const calculatedTotal = items.reduce((s, c) => s + c.amount, 0);
      return { key, label: periodLabel(key), items, manualEntries, total: calculatedTotal + manualSum };
    });
}

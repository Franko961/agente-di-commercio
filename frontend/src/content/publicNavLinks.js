// Unica fonte di verità per i link della navigazione pubblica — usata sia
// da PublicHeader.jsx (tutte le pagine pubbliche tranne la home) sia da
// Landing.jsx (che ha un proprio header con stile a parte, transizione
// trasparente/solido allo scroll, ma la STESSA lista di link). Prima erano
// due array duplicati che si erano disallineati (Landing.jsx era rimasta
// indietro quando "Chi siamo" era stato aggiunto solo a PublicHeader.jsx) —
// un solo posto da aggiornare elimina la possibilità che riaccada.
export const PUBLIC_NAV_LINKS = [
  { to: "/blog", label: "Blog" },
  { to: "/tour", label: "Tour guidato" },
  { to: "/perche-salesfly", label: "Perché SalesFly" },
  { to: "/contatti", label: "Contatti" },
  { to: "/prezzi", label: "Prezzi" },
  { to: "/chi-siamo", label: "Chi siamo" },
];

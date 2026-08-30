const article = {
  slug: "firr-agenti-commercio-calcolo-indennita",
  title: "FIRR agenti di commercio: calcolo dell'indennità di fine rapporto",
  description:
    "Cos'è il FIRR, chi lo versa, quando spetta e come si calcola con i nuovi scaglioni 2026 (aggiornati per la prima volta dal 1989): guida con calcolatore per mono e plurimandatari.",
  publishedAt: "2026-08-31",
  draft: false,
  blocks: [
    {
      type: "p",
      text: "Il FIRR (Fondo Indennità Risoluzione Rapporto) è l'indennità che spetta all'agente di commercio alla cessazione del mandato — a prescindere da chi lo interrompe e perché. È gestito da ENASARCO, ma è un fondo distinto dai normali contributi previdenziali: accantona, anno per anno, una quota calcolata sulle provvigioni, che l'agente riceve quando il rapporto con quel mandante finisce. Dal 2026 il calcolo è cambiato per la prima volta dal 1989, quindi vale la pena rivederlo da zero.",
    },
    { type: "h2", text: "Chi versa il FIRR e quando spetta all'agente" },
    {
      type: "p",
      text: "È il mandante a versare il FIRR presso ENASARCO, con scadenza al 31 marzo di ogni anno per le somme maturate l'anno precedente — non è un costo o un adempimento a carico dell'agente. Spetta in ogni caso di cessazione del mandato: non serve dimostrare un incremento di fatturato o di clientela, ed è dovuto persino se è l'agente a dimettersi. È proprio questo che lo distingue dalle altre due indennità di fine rapporto (indennità suppletiva di clientela e indennità meritocratica, previste dagli Accordi Economici Collettivi e dall'art. 1751 del Codice Civile): quelle hanno condizioni più restrittive — ad esempio l'indennità suppletiva viene meno se l'agente si dimette senza giusta causa — mentre il FIRR resta la componente più \"garantita\" delle tre.",
    },
    { type: "h2", text: "I nuovi scaglioni 2026 (prima revisione dal 1989)" },
    {
      type: "p",
      text: "L'Accordo Economico Collettivo Commercio, siglato il 4 giugno 2025 da Confcommercio e dalle sigle sindacali di categoria (tra cui FNAARC), ha rivisto al rialzo gli scaglioni provvigionali su cui si calcola il FIRR — fermi dal 1989. Le nuove aliquote si applicano alle provvigioni accantonate dal 1° gennaio 2026: il FIRR maturato fino al 2025 resta calcolato con i vecchi scaglioni, senza effetto retroattivo. Il primo versamento secondo le nuove regole è previsto entro il 31 marzo 2027.",
    },
    {
      type: "ul",
      items: [
        "Plurimandatario (senza esclusiva) — dal 2026: 4% fino a 12.000€, 2% da 12.000,01 a 18.000€, 1% oltre 18.000,01€. Fino al 2025 era: 4% fino a 6.200€, 2% da 6.200,01 a 9.300€, 1% oltre 9.300,01€.",
        "Monomandatario (con esclusiva) — dal 2026: 4% fino a 24.000€, 2% da 24.000,01 a 36.000€, 1% oltre 36.000,01€. Fino al 2025 era: 4% fino a 12.400€, 2% da 12.400,01 a 18.600€, 1% oltre 18.600,01€.",
      ],
    },
    {
      type: "p",
      text: "Attenzione a dove cerchi questi dati: al momento in cui scriviamo, diverse guide online riportano ancora i vecchi scaglioni (quelli fermi al 2025) presentandoli come attuali — probabilmente contenuti non aggiornati dopo la firma dell'accordo. Abbiamo verificato le cifre sopra incrociando più fonti indipendenti, inclusa la federazione di categoria che ha partecipato alla trattativa.",
    },
    { type: "h2", text: "Come si calcola: un esempio" },
    {
      type: "p",
      text: "Il calcolo è a scaglioni progressivi, applicato separatamente per ogni mandante: si applica l'aliquota di ogni fascia solo alla parte di provvigioni che rientra in quella fascia, non all'intero importo. Un agente plurimandatario con 15.000€ di provvigioni nell'anno da un singolo mandante, mandato attivo tutto l'anno: 4% × 12.000€ = 480€, più 2% × (15.000 − 12.000) = 60€. Totale FIRR accantonato per quell'anno su quel mandante: 540€.",
    },
    {
      type: "p",
      text: "Se il mandato è iniziato o terminato a metà anno, gli scaglioni si riducono in proporzione ai mesi di attività effettiva — non si applicano per intero a un rapporto di pochi mesi. E soprattutto: il calcolo è per mandante, non complessivo. Un plurimandatario con 3 mandanti ha 3 accantonamenti FIRR distinti, ciascuno calcolato sulle provvigioni di quel singolo rapporto.",
    },
    {
      type: "calculator",
      name: "firr",
    },
    { type: "h2", text: "Come si riceve materialmente il FIRR" },
    {
      type: "p",
      text: "Alla cessazione del mandato, ENASARCO liquida direttamente all'agente le somme accantonate fino a quel momento per quel mandante — non è il mandante a pagarle di tasca propria in quel momento, semplicemente perché le ha già versate anno per anno durante il rapporto. Fa eccezione la quota dell'ultimo anno, non ancora versata al fondo al momento della cessazione: quella la salda direttamente il mandante. Gli importi accantonati restano comunque consultabili nell'area riservata del sito ENASARCO.",
    },
    {
      type: "cta",
      title: "Le provvigioni per calcolare il tuo FIRR le hai già in SalesFly",
      text: "Il totale annuo delle provvigioni per singolo mandante — il dato che serve per questo calcolo — è esattamente quello che SalesFly traccia automaticamente a ogni ordine.",
      href: "/richiedi-demo",
      cta: "Inizia prova gratuita",
    },
  ],
};

export { article };

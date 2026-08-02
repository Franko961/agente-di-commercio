const article = {
  slug: "spese-deducibili-agente-di-commercio",
  title: "Spese deducibili per un agente di commercio: cosa tracciare e perché",
  description:
    "Guida pratica al tracciamento delle spese per un agente di commercio plurimandatario: quali categorie tenere sotto controllo, perché conservare gli scontrini e come organizzarle mese per mese.",
  publishedAt: "2026-08-01",
  draft: false,
  blocks: [
    {
      type: "p",
      text: "Chi lavora come agente di commercio plurimandatario sostiene, nel corso dell'anno, una quantità di piccole e grandi spese legate all'attività: carburante, pasti fuori sede, pedaggi, materiali, oltre ai contributi previdenziali e alle spese ricorrenti come l'assicurazione auto. Tenerle tracciate con ordine non è solo un adempimento da fine anno per il commercialista: è quello che permette di sapere davvero quanto si guadagna, non solo quanto si fattura in provvigioni.",
    },
    { type: "h2", text: "Perché tracciare le spese non è solo un obbligo fiscale" },
    {
      type: "p",
      text: "Le provvigioni maturate raccontano solo metà della storia: il margine reale di un agente plurimandatario è quello che resta dopo aver coperto i costi di trasferta, i contributi e le spese ricorrenti dell'attività. Senza un tracciamento continuo, questi costi tendono a restare invisibili fino a fine anno — quando è ormai troppo tardi per capire, mese per mese, se una zona o un periodo dell'anno è stato davvero redditizio o se i costi di trasferta hanno eroso gran parte del margine.",
    },
    { type: "h2", text: "Le categorie di spesa più comuni per un agente plurimandatario" },
    {
      type: "p",
      text: "Le voci di spesa di un agente di commercio tendono a ripetersi mese dopo mese, ed è utile classificarle fin da subito in categorie coerenti invece di accumulare scontrini generici:",
    },
    {
      type: "ul",
      items: [
        "Carburante — la voce più frequente per chi copre una zona ampia con più mandanti",
        "Vitto — pasti fuori sede durante le giornate di visita",
        "Alloggio — pernottamenti per trasferte più lunghe o zone distanti",
        "Pedaggio e parcheggio — costi minori ma frequenti, facili da perdere se non annotati subito",
        "Materiali — cataloghi, campionari, cancelleria e altro materiale a supporto delle visite",
      ],
    },
    { type: "h2", text: "INPS, ENASARCO e assicurazione auto: le spese ricorrenti da non dimenticare" },
    {
      type: "p",
      text: "Oltre alle spese di trasferta quotidiane, un agente plurimandatario sostiene costi ricorrenti che è facile trascurare proprio perché non legati a una singola visita: i contributi INPS, quelli ENASARCO versati tramite i mandanti (vedi l'approfondimento dedicato su come funziona ENASARCO), l'assicurazione dell'auto usata per il lavoro e le parcelle del commercialista. Registrarli con la stessa cura delle spese quotidiane, invece di ricostruirli a memoria a fine anno, aiuta ad avere un quadro contributivo aggiornato lungo tutto l'anno.",
    },
    { type: "h2", text: "Documentazione e scontrini: perché conservarli conta più della cifra" },
    {
      type: "p",
      text: "Una spesa senza uno scontrino o una ricevuta collegata è un dato debole: al momento del controllo con il commercialista, o in caso di verifica, è la documentazione a dare valore alla registrazione, non solo l'importo annotato. Allegare una foto o un PDF dello scontrino a ogni spesa nel momento stesso in cui viene sostenuta — invece di accumulare una busta di carta da riordinare dopo — evita sia di perdere i documenti sia di dover ricostruire a memoria dettagli che si dimenticano in fretta.",
    },
    { type: "h2", text: "Guardare le spese mese per mese, non solo a fine anno" },
    {
      type: "p",
      text: "Rivedere le spese raggruppate per mese, invece che come un unico elenco indistinto, rende molto più semplice notare un pattern: un mese di trasferte più costoso della media, una categoria che cresce senza una ragione evidente, o semplicemente il costo reale di coprire una determinata zona. È un controllo che richiede pochi minuti se fatto con regolarità, e diventa via via più difficile più tempo passa tra una spesa e la sua registrazione.",
    },
    {
      type: "p",
      text: "Un'ultima nota: questo articolo parla di come organizzare e tracciare le spese, non di quali siano fiscalmente deducibili e in quale misura — quello dipende dal proprio regime fiscale e da regole che è il commercialista a dover valutare caso per caso. Avere le spese già categorizzate, documentate e organizzate mese per mese è comunque ciò che rende quel confronto rapido, invece di partire da una busta di scontrini a gennaio.",
    },
  ],
};

// CommonJS apposta: leggibile sia da webpack/Babel che da Node in
// scripts/prerender.js senza transpilazione — vedi il commento in
// calcolo-provvigioni-agente-di-commercio.js per il perché.
module.exports = { article };

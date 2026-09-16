const article = {
  slug: "regime-forfettario-agente-di-commercio",
  title: "Regime forfettario per l'agente di commercio: come funziona e quanto si paga",
  description:
    "Coefficiente di redditività, soglie di ricavi, aliquota al 15% o al 5%: come si calcolano davvero le tasse in regime forfettario per un agente di commercio, con le cifre aggiornate al 2026.",
  publishedAt: "2026-09-16",
  draft: false,
  blocks: [
    {
      type: "p",
      text: "Il regime forfettario è la scelta di partenza per la maggior parte degli agenti di commercio che aprono la partita IVA: niente IVA da gestire in fattura, adempimenti contabili ridotti al minimo, e un calcolo delle imposte più semplice di quello ordinario. \"Più semplice\" non vuol dire \"senza regole da capire\", però — il meccanismo del coefficiente di redditività, le soglie di uscita e cosa si può dedurre davvero sono punti che vale la pena chiarire prima, non scoprirli a fine anno con il commercialista.",
    },
    { type: "h2", text: "Il coefficiente di redditività: 62%, non i costi reali" },
    {
      type: "p",
      text: "Nel regime forfettario le imposte non si calcolano sul reddito netto (ricavi meno costi effettivamente sostenuti), come nel regime ordinario, ma su un reddito forfettizzato: ricavi lordi moltiplicati per un coefficiente di redditività che varia per attività. Per gli intermediari del commercio — il gruppo ATECO 46.1x a cui appartiene l'agente di commercio (vedi la guida ai codici ATECO per il tuo settore specifico) — il coefficiente è 62%: il 38% dei ricavi è considerato forfettariamente \"costo\", a prescindere da quanto si è speso davvero. È un coefficiente più favorevole di quello di professioni vicine: un agente assicurativo ha un coefficiente al 78% (ATECO 66.22.00), un agente immobiliare all'86% (ATECO 68.31.00) — più alto il coefficiente, meno ricavi restano fuori dalla base imponibile.",
    },
    { type: "calculator", name: "regimeForfettario" },
    { type: "h2", text: "Le due soglie: 85.000€ e 100.000€" },
    {
      type: "p",
      text: "Il limite di ricavi per restare nel regime forfettario è 85.000€ annui. Superarlo non fa scattare conseguenze immediate identiche in ogni caso: tra 85.000€ e 100.000€ si resta nel forfettario per l'intero anno in corso, ma si perde il diritto ad accedervi dall'anno successivo (si passa al regime ordinario dal 1° gennaio). Oltre 100.000€, invece, l'uscita è immediata nello stesso anno: dal momento in cui si supera la soglia, l'operazione che ha causato lo sforamento e quelle successive scontano l'IVA, e l'intero reddito dell'anno viene tassato con le regole ordinarie, non più con il coefficiente forfettario.",
    },
    { type: "h2", text: "L'aliquota: 15%, o 5% per i primi cinque anni" },
    {
      type: "p",
      text: "L'imposta sostitutiva ordinaria è il 15% del reddito imponibile (ricavi × coefficiente, meno i contributi previdenziali — vedi sotto). Chi avvia una nuova attività può applicare il 5% per i primi cinque anni (l'anno di apertura più i quattro successivi), ma solo se sono rispettate tutte e tre queste condizioni insieme: non aver svolto un'attività artistica, professionale o d'impresa simile nei tre anni precedenti; la nuova attività non deve essere la mera prosecuzione di un lavoro già svolto in precedenza come dipendente o autonomo (fa eccezione il periodo di pratica obbligatoria, dove previsto); se si prosegue un'attività di un altro soggetto (es. un mandato rilevato da un collega), i suoi ricavi dell'anno precedente non devono aver superato il limite di accesso al regime. Senza tutti e tre i requisiti, si applica il 15% fin dal primo anno.",
    },
    { type: "h2", text: "I contributi previdenziali si deducono comunque" },
    {
      type: "p",
      text: "A differenza dei costi normali dell'attività (già \"coperti\" dal coefficiente, quindi non deducibili uno per uno), i contributi previdenziali obbligatori fanno eccezione: l'articolo 10 del TUIR, richiamato dalla Circolare dell'Agenzia delle Entrate n. 10/2016 specifica sul regime forfettario, li rende deducibili dal reddito imponibile anche qui — INPS Gestione Commercianti ed ENASARCO compresi. La deduzione si applica per cassa (nell'anno in cui i contributi sono stati effettivamente versati, non nell'anno a cui si riferiscono) e riduce le imposte da pagare, non l'importo dei contributi stessi, che restano dovuti per intero.",
    },
    { type: "h2", text: "Chi non può accedere: i limiti da conoscere" },
    {
      type: "ul",
      items: [
        "Redditi da lavoro dipendente o pensione nell'anno precedente non superiori a 35.000€ (soglia prorogata anche per il 2026) — oltre questa cifra il regime forfettario non è accessibile, indipendentemente dai ricavi dell'attività di agente.",
        "Spese per personale dipendente o collaboratori non superiori a 20.000€ lordi annui.",
        "Nessuna partecipazione, contemporaneamente, in società di persone, associazioni professionali o srl a responsabilità limitata che svolgono un'attività economicamente riconducibile a quella individuale in regime forfettario.",
      ],
    },
    {
      type: "p",
      text: "Per due argomenti specifici legati al regime forfettario — la deducibilità dell'auto e il funzionamento di ritenuta d'acconto ed ENASARCO in fattura — trovi le guide dedicate, con calcolatore, qui sotto tra gli articoli collegati: questa pagina non li ripete, mette solo in ordine il quadro generale del regime.",
    },
    {
      type: "cta",
      title: "Le provvigioni, pronte per il forfettario",
      text: "SalesFly calcola la provvigione di ogni vendita, mandante per mandante — la base su cui applicare il coefficiente resta sempre a portata di mano, senza ricostruirla a fine anno da un foglio Excel.",
      href: "/richiedi-demo",
      cta: "Inizia prova gratuita",
    },
  ],
};

export { article };

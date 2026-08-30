const article = {
  slug: "pianificare-giro-visite-agente-di-commercio",
  title: "Come pianificare il giro visite di un agente di commercio",
  description:
    "Guida pratica alla pianificazione del giro visite per un agente di commercio plurimandatario: geolocalizzazione dei clienti, scelta del punto di partenza e ottimizzazione del percorso per ridurre i tempi di trasferta.",
  publishedAt: "2026-07-31",
  draft: false,
  blocks: [
    {
      type: "p",
      text: "Per un agente di commercio plurimandatario, decidere ogni mattina quali clienti visitare e in che ordine è spesso un esercizio a occhio: si guarda la zona, si ricorda a memoria chi non si vede da un po', e si parte sperando di non fare percorsi a zig-zag inutili. Un CRM con clienti geolocalizzati e un motore di ottimizzazione del percorso toglie questa parte di improvvisazione.",
    },
    { type: "h2", text: "Vedere i clienti sulla mappa, non solo in elenco" },
    {
      type: "p",
      text: "Il primo passo è avere l'indirizzo di ogni cliente trasformato in una coordinata geografica: una volta geolocalizzati, i clienti compaiono su una mappa invece che in un semplice elenco testuale, ed è immediato vedere quali sono vicini tra loro e quali invece richiederebbero uno spostamento lungo. È la differenza tra decidere il giro leggendo un indirizzo alla volta e vederlo colpo d'occhio su una cartina.",
    },
    { type: "h2", text: "Come funziona l'ottimizzazione del percorso" },
    {
      type: "p",
      text: "Selezionati i clienti da visitare in giornata, il sistema calcola l'ordine di visita che minimizza il percorso complessivo, non limitandosi a seguire l'ordine in cui i clienti sono stati scelti. Quando è disponibile un servizio di routing stradale, le distanze e i tempi usati nel calcolo sono quelli reali su strada; altrimenti viene usata una stima in linea d'aria, segnalata come tale, così è sempre chiaro se i numeri mostrati sono precisi o solo indicativi.",
    },
    {
      type: "p",
      text: "Per ogni tappa il sistema propone anche un orario di arrivo e di partenza stimato, calcolato sommando i tempi di spostamento a una durata di visita fissa impostabile — utile per capire, prima di partire, se il giro pianificato è realistico per la giornata o se conviene togliere qualche tappa.",
    },
    { type: "h2", text: "Da dove far partire il giro" },
    {
      type: "p",
      text: "Il punto di partenza del giro non è per forza il primo cliente della lista: si può far partire il calcolo dalla propria posizione attuale (via geolocalizzazione del telefono/browser), da un indirizzo di casa o ufficio impostato una volta nelle proprie impostazioni, oppure da un punto scelto manualmente. È possibile anche chiedere che il percorso torni al punto di partenza a fine giornata, invece di terminare all'ultimo cliente visitato.",
    },
    { type: "h2", text: "Indirizzi mancanti o dati sospetti" },
    {
      type: "p",
      text: "Un cliente senza un indirizzo geolocalizzato correttamente non può essere incluso nel calcolo del percorso: il sistema lo segnala esplicitamente invece di ometterlo silenziosamente, così si sa subito quale scheda cliente va sistemata. Allo stesso modo, se tra due tappe consecutive risulta una distanza implausibile per un giro nella stessa giornata, viene mostrato un avviso: è quasi sempre il sintomo di un indirizzo geocodificato in modo scorretto (ad esempio su un omonimo in un'altra città), da controllare prima di fidarsi del percorso proposto.",
    },
    { type: "h2", text: "Meno tempo a pianificare, più tempo a vendere" },
    {
      type: "p",
      text: "Per chi gestisce più mandanti e quindi più cataloghi, listini e clienti sparsi sullo stesso territorio, ridurre anche solo i chilometri superflui tra una visita e l'altra si traduce in più tempo utile durante la giornata lavorativa — tempo che può essere dedicato a un cliente in più, invece che al tragitto per raggiungerlo.",
    },
    {
      type: "cta",
      title: "Meno chilometri, più visite",
      text: "Pianifica il giro visite su mappa, con partenza dalla tua posizione reale.",
      href: "/richiedi-demo",
      cta: "Inizia prova gratuita",
    },
  ],
};

export { article };

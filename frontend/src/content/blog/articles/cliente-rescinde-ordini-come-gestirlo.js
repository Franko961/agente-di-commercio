const article = {
  slug: "cliente-rescinde-ordini-come-gestirlo",
  title: "Cliente che rescinde continuamente gli ordini: come gestirlo",
  description:
    "Un annullamento ogni tanto è normale. Il problema è quando diventa un pattern: come distinguere le due situazioni, capire la causa reale, e decidere quando smettere di investirci tempo.",
  publishedAt: "2026-09-12",
  draft: false,
  blocks: [
    {
      type: "p",
      text: "Un cliente che annulla un ordine, ogni tanto, è normale: succede per motivi legittimi, non è un segnale di allarme. Il problema comincia quando diventa un pattern — lo stesso cliente che ordina e rescinde, ordina e rescinde, mentre il tempo speso a preparare offerte, campionature, visite non si trasforma mai in fatturato reale. Come distinguere le due situazioni, e cosa fare quando è davvero un pattern.",
    },
    { type: "h2", text: "Il singolo annullamento non dice niente" },
    {
      type: "p",
      text: "Un cliente può annullare per motivi che non hanno nulla a che fare con te o col tuo mandante: un problema di cassa temporaneo, un cambio di priorità interno, un fornitore alternativo più urgente in quel momento. Reagire al primo annullamento come se fosse un problema strutturale porta a due errori opposti: o si smette di seguire un cliente valido per un episodio isolato, o si continua a investire tempo su un pattern reale scambiandolo per una serie di casi sfortunati. Il punto di partenza è sempre lo storico, non l'ultimo episodio.",
    },
    { type: "h2", text: "Guardare lo storico, non l'ultimo episodio" },
    {
      type: "p",
      text: "In SalesFly ogni ordine ha uno stato — confermato, in evasione, spedito, consegnato, annullato, reso — e quando un ordine passa ad annullato la provvigione collegata viene rimossa automaticamente dal calcolo. Questo significa che lo storico ordini di un cliente, visibile nella sua scheda, è già di per sé la fonte più affidabile per rispondere alla domanda: quanti ordini negli ultimi mesi sono arrivati a consegna, e quanti si sono fermati ad annullato? Un singolo annullamento su dieci ordini è rumore. Tre annullamenti su cinque sono un pattern.",
    },
    { type: "h2", text: "Capire la causa prima di reagire" },
    {
      type: "p",
      text: "Non tutti i pattern di annullamento hanno la stessa causa, e la risposta giusta cambia parecchio a seconda di quale sia.",
    },
    {
      type: "ul",
      items: [
        "Problemi di liquidità ricorrenti: il cliente ordina con l'intenzione reale di comprare, poi rescinde perché non riesce a far quadrare la cassa. Qui il rischio vero non è l'annullamento in sé, ma il credito che si accumulerebbe se gli ordini arrivassero a evasione — un campanello d'allarme da prendere sul serio, non da ignorare perché \"tanto l'ordine è comunque annullato\".",
        "Comportamento opportunistico: il cliente usa l'ordine come leva per testare condizioni migliori altrove, sapendo di poter rescindere senza conseguenze. Qui la domanda da farsi è se le condizioni concordate sono davvero competitive, o se il cliente sta semplicemente confrontando prezzi a costo zero per te.",
        "Un problema nel processo, non nel cliente: tempi di consegna disattesi, prodotto diverso da quanto presentato, comunicazione che arriva tardi. In questo caso il pattern di annullamenti è un sintomo, non la causa — e va segnalato al mandante prima di continuare a portare ordini che si sa già finiranno annullati.",
      ],
    },
    { type: "h2", text: "Quando ha senso smettere di investirci tempo" },
    {
      type: "p",
      text: "Ogni offerta preparata, ogni visita dedicata a un cliente ha un costo reale in tempo — tempo che con un pattern di annullamenti ripetuti non si traduce mai in provvigione. Se il potenziale assegnato a quel cliente in fase di anagrafica (alto, medio, basso) era una stima fatta all'inizio del rapporto, un pattern di annullamenti persistente è il momento giusto per rivederla verso il basso, e per ridurre di conseguenza quanto tempo gli si dedica rispetto ad altri clienti che convertono davvero. Non significa smettere di seguirlo del tutto — significa smettere di trattarlo come se valesse quanto sembrava all'inizio.",
    },
    {
      type: "cta",
      title: "Lo storico ordini di ogni cliente, sempre a portata di mano",
      text: "Stato di ogni ordine, provvigioni aggiornate automaticamente quando qualcosa viene annullato — nessun calcolo manuale da rifare. 14 giorni di prova gratuita, senza carta di credito.",
      href: "/richiedi-demo",
      cta: "Inizia prova gratuita",
    },
  ],
};

export { article };

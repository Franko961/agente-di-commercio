const article = {
  slug: "verifica-partita-iva-vies",
  title: "Verifica Partita IVA VIES: cos'è e quando serve a un agente di commercio",
  description:
    "Cos'è il VIES, perché l'iscrizione non è automatica anche con una Partita IVA attiva, e i due casi reali in cui riguarda un agente di commercio: mandante estero o cliente estero del mandante.",
  publishedAt: "2026-09-02",
  draft: false,
  blocks: [
    {
      type: "p",
      text: "VIES sta per VAT Information Exchange System: è il sistema con cui gli Stati membri dell'Unione Europea si scambiano informazioni sull'IVA, e serve in pratica a una cosa concreta — verificare che la Partita IVA di un'azienda in un altro Paese UE sia valida e abilitata alle operazioni intracomunitarie, prima di fatturare senza applicare l'IVA. Se entrambe le parti di un'operazione B2B tra Paesi UE sono iscritte al VIES, chi vende può emettere fattura senza IVA (la applica l'acquirente nel proprio Paese, secondo il meccanismo del reverse charge); se anche una sola delle due non è iscritta, l'operazione non può essere trattata come intracomunitaria.",
    },
    { type: "h2", text: "I due casi in cui riguarda davvero un agente di commercio" },
    {
      type: "p",
      text: "Non è un tema che coinvolge automaticamente ogni agente di commercio: dipende da dove ha sede il mandante e da chi emette le fatture verso l'estero. Vale la pena distinguere due situazioni molto diverse.",
    },
    {
      type: "ul",
      items: [
        "Il mandante ha sede in un altro Paese UE: qui il coinvolgimento è diretto. La provvigione che l'agente fattura al mandante è essa stessa una prestazione di servizi tra soggetti passivi IVA di due Paesi UE diversi (B2B) — per regola generale, non soggetta a IVA nel Paese dell'agente, con IVA che il mandante applica nel proprio Paese in reverse charge. Per fatturare così, l'agente deve essere lui stesso iscritto al VIES, e conviene verificare che anche la Partita IVA del mandante lo sia.",
        "Il mandante è italiano e vende a clienti B2B di altri Paesi UE tramite l'agente: qui la gestione del VIES riguarda il mandante, non l'agente — è lui a dover essere iscritto per le proprie cessioni di beni, ed è lui (o chi si occupa della sua fatturazione) a dover verificare la Partita IVA del cliente estero. L'agente, in questo caso, non ha un obbligo diretto di iscrizione.",
      ],
    },
    { type: "h2", text: "Perché serve una richiesta esplicita, non basta avere Partita IVA" },
    {
      type: "p",
      text: "Un errore comune: pensare che avere una Partita IVA attiva significhi automaticamente comparire nel VIES. Non è così — l'iscrizione va richiesta esplicitamente, compilando il campo \"Operazioni Intracomunitarie\" nel quadro I del modello AA9 (per imprese individuali e lavoratori autonomi, agenti di commercio inclusi) o AA7, direttamente in fase di apertura della Partita IVA oppure in un momento successivo tramite i servizi telematici dell'Agenzia delle Entrate. La procedura è gratuita: nessuna intermediazione a pagamento è necessaria, ed è bene diffidare di chi la offre a pagamento.",
    },
    {
      type: "p",
      text: "Dopo la richiesta, l'iscrizione non è immediata: l'Agenzia delle Entrate ha 30 giorni per effettuare controlli preliminari e comunicare un eventuale diniego; se non arriva nulla, dal trentunesimo giorno si può operare come iscritti. Non finisce lì — nei 6 mesi successivi possono seguire controlli più approfonditi, e in seguito controlli periodici: in caso di violazioni accertate, l'iscrizione può essere revocata.",
    },
    { type: "h2", text: "Come si verifica una Partita IVA sul VIES" },
    {
      type: "p",
      text: "La verifica si fa sul portale ufficiale della Commissione Europea (VIES VAT number validation), inserendo il Paese e il numero di Partita IVA della controparte: è gratuita, immediata, e restituisce solo un esito di validità — non i dati anagrafici completi dell'azienda (quelli, se servono, richiedono altri strumenti). Vale la regola generale già valida per l'iscrizione: qualunque servizio a pagamento che promette di \"verificare la tua posizione VIES\" per te sta semplicemente rifacendo, a pagamento, un controllo che l'Agenzia delle Entrate e la Commissione Europea offrono gratis.",
    },
    {
      type: "p",
      text: "Conviene verificare prima di fatturare, non dopo: emettere una fattura in reverse charge verso una controparte che risulta poi non iscritta (o mai stata iscritta) al VIES significa aver trattato come intracomunitaria un'operazione che non lo era — con la necessità di correggere la fattura e, nei casi più seri, il rischio di contestazioni sull'IVA non versata.",
    },
    {
      type: "cta",
      title: "Ogni mandante, italiano o estero, in un unico posto",
      text: "Registra i tuoi mandanti e le rispettive provvigioni: calcolate automaticamente, mandante per mandante.",
      href: "/richiedi-demo",
      cta: "Inizia prova gratuita",
    },
  ],
};

export { article };

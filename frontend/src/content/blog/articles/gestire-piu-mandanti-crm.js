const article = {
  slug: "gestire-piu-mandanti-crm",
  title: "Come gestire più mandanti con un CRM",
  description:
    "Guida pratica alla gestione multi-mandato per un agente di commercio plurimandatario: aliquote diverse, cataloghi separati, obiettivi per mandante e provvigioni sempre corrette anche quando i mandanti si sovrappongono.",
  publishedAt: "2026-08-04",
  draft: false,
  blocks: [
    {
      type: "p",
      text: "Chi lavora con più mandanti conosce bene il problema: ogni azienda rappresentata ha la sua aliquota di provvigione, il suo catalogo prodotti, i suoi obiettivi di fatturato — e non è raro che lo stesso cliente compri da più mandanti diversi. Gestire tutto questo con un foglio Excel per mandante, o peggio con un unico foglio che li mescola tutti, rende quasi impossibile rispondere a una domanda semplice: quanto sto guadagnando davvero da ciascuna azienda che rappresento?",
    },
    { type: "h2", text: "Perché un CRM generico non basta per un plurimandatario" },
    {
      type: "p",
      text: "La maggior parte dei CRM è pensata per un'azienda che vende i propri prodotti, non per un agente che rappresenta più aziende contemporaneamente. Manca il concetto stesso di \"mandante\" come entità: senza di esso, ogni cliente, ordine o provvigione finisce in un unico calderone, e isolare i dati di un solo mandante richiede filtri manuali o fogli separati da tenere sincronizzati a mano.",
    },
    { type: "h2", text: "Il mandante come entità a sé, non solo un'etichetta" },
    {
      type: "p",
      text: "In SALESFLY ogni mandante è una scheda a sé, con la propria aliquota di provvigione standard e — quando serve — aliquote differenziate per i clienti nuovi rispetto ai rinnovi. Si possono impostare obiettivi separati (mensile, annuale, numero di clienti target) e una scala premi a scaglioni, per tenere traccia di eventuali bonus legati al superamento di una soglia di fatturato.",
    },
    {
      type: "ul",
      items: [
        "Aliquota di provvigione standard, con eccezioni opzionali per nuovi contratti e rinnovi",
        "Obiettivi mensili, annuali e sul numero di clienti, ciascuno con le proprie note",
        "Scala premi a scaglioni, per i mandanti che prevedono bonus al superamento di soglie di fatturato",
      ],
    },
    { type: "h2", text: "Cambiare vista con un clic: il mandante attivo" },
    {
      type: "p",
      text: "Nella barra laterale è sempre visibile il \"mandante attivo\": un selettore che, cliccato, passa da un mandante all'altro (o a \"tutti\"). Cambiarlo filtra all'istante dashboard, clienti, ordini, offerte e provvigioni sui soli dati di quel mandante — senza dover riaprire un altro file o rifare un filtro da capo ogni volta.",
    },
    { type: "h2", text: "Cataloghi prodotto separati" },
    {
      type: "p",
      text: "Ogni mandante ha il proprio catalogo prodotti, con prezzo e costo indipendenti. Nella pagina Prodotti un filtro dedicato (separato dal mandante attivo scelto in barra laterale) permette di isolare rapidamente il catalogo di uno solo di essi.",
    },
    { type: "h2", text: "Provvigioni corrette anche quando i mandanti si sovrappongono" },
    {
      type: "p",
      text: "Il calcolo delle provvigioni segue automaticamente l'aliquota del mandante associato a ogni ordine — con l'eventuale differenziazione tra cliente nuovo e rinnovo, se impostata — quindi non serve ricalcolare nulla a mano quando i mandanti nello stesso mese sono più di uno. Anche le provvigioni inserite manualmente — per premi, arretrati o accordi particolari che non passano da un ordine — possono essere associate a un mandante specifico: così il totale per mandante resta corretto invece di mescolare voci che appartengono ad aziende diverse.",
    },
    {
      type: "p",
      text: "Un'ultima nota: la scala premi e gli obiettivi per mandante sono strumenti di monitoraggio, pensati per avere sott'occhio a che punto si è rispetto a una soglia o un target — non calcolano automaticamente l'erogazione di un bonus, che resta un accordo tra agente e mandante da verificare caso per caso.",
    },
  ],
};

export { article };

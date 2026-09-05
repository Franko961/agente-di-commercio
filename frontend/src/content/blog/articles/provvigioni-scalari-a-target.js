const article = {
  slug: "provvigioni-scalari-a-target",
  title: "Provvigioni scalari a target: come funzionano e come si calcolano",
  description:
    "Oltre alla percentuale fissa, molti mandanti offrono un premio aggiuntivo al superamento di certe soglie di fatturato. Come funzionano gli scaglioni, come si sommano davvero, e cosa chiarire prima di firmare.",
  publishedAt: "2026-09-05",
  draft: false,
  blocks: [
    {
      type: "p",
      text: "Non tutte le provvigioni sono una semplice percentuale fissa sul venduto. Molti mandanti strutturano un premio aggiuntivo — una scala premi — che scatta quando si superano certe soglie di fatturato in un periodo. L'idea è semplice: motivare a vendere di più, non solo a vendere. Il dettaglio che spesso sfugge è come questi scaglioni si sommano davvero tra loro, ed è proprio lì che nascono le sorprese quando arriva il conteggio.",
    },
    { type: "h2", text: "Come funziona in pratica: gli scaglioni" },
    {
      type: "p",
      text: "Un esempio tipico: 2.000€ di fatturato danno diritto a un premio di 500€, 3.000€ a un premio di 360€, 5.000€ a un premio di 600€. Sembra intuitivo pensare che, raggiunti i 5.000€, si sommino tutti e tre i premi (500+360+600 = 1.460€). Nella pratica più comune, però, non funziona così.",
    },
    { type: "h2", text: "Il dettaglio che conta davvero: come si sommano gli scaglioni" },
    {
      type: "p",
      text: "Lo schema più diffuso è: il primo scaglione (la soglia più bassa) resta fisso e si somma sempre, una volta raggiunto. Tra gli scaglioni successivi, invece, non si sommano tra loro — conta solo il premio dello scaglione più alto raggiunto, sommato al primo. Nell'esempio sopra: raggiunti i 5.000€, si paga 500€ (il primo scaglione) + 600€ (il più alto tra gli altri) = 1.100€, non 1.460€. Il premio da 360€ del secondo scaglione non si aggiunge, perché è stato superato da uno scaglione più alto.",
    },
    {
      type: "p",
      text: "Non è l'unico modo possibile di strutturare una scala premi — alcuni mandanti sommano davvero ogni scaglione raggiunto, altri pagano solo l'ultimo scaglione toccato senza nessuna soglia fissa. Il punto è che la logica va sempre verificata nel testo del contratto o dell'accordo commerciale, non assunta per analogia con un altro mandante: due scale premi che sembrano simili sui numeri possono dare risultati molto diversi a fine anno a seconda di come si sommano.",
    },
    { type: "h2", text: "Su cosa si misura la soglia: il fatturato, non la provvigione già incassata" },
    {
      type: "p",
      text: "Un secondo dettaglio tecnico da chiarire: la soglia si misura tipicamente sul fatturato generato (il valore degli ordini), non sulla provvigione già percepita su quegli ordini. È una distinzione che conta soprattutto quando le aliquote variano — una vendita da 10.000€ con aliquota all'8% genera un fatturato di 10.000€ ai fini della soglia, indipendentemente dagli 800€ di provvigione che ne derivano. E il premio scala stesso, una volta liquidato, di norma non rientra nel fatturato che serve a raggiungere gli scaglioni successivi (altrimenti il calcolo si autoalimenterebbe).",
    },
    {
      type: "ul",
      items: [
        "Come si sommano gli scaglioni: tutti insieme, solo il più alto, o solo il primo + il più alto? Va scritto esplicitamente, non assunto.",
        "Su quale base si misura la soglia: fatturato lordo degli ordini o provvigione netta?",
        "Il periodo di riferimento: mensile, trimestrale, annuale — cambia molto la strategia con cui pianificare le vendite verso la soglia successiva.",
        "Cosa succede se il fatturato scende sotto una soglia già raggiunta in un periodo successivo: il premio già pagato resta acquisito, o va restituito?",
        "Quando viene liquidato il premio: insieme alla provvigione ordinaria, o con un conteggio separato a fine periodo?",
      ],
    },
    {
      type: "cta",
      title: "La scala premi, calcolata automaticamente per ogni mandante",
      text: "In SalesFly imposti gli scaglioni di ciascun mandante una volta sola: il sistema calcola da solo quali sono raggiunti e quanto spetta, con la stessa logica di somma (primo scaglione fisso + il più alto tra gli altri) applicata in automatico a ogni provvigione registrata.",
      href: "/richiedi-demo",
      cta: "Inizia prova gratuita",
    },
  ],
};

export { article };

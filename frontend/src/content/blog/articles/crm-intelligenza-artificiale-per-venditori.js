const article = {
  slug: "crm-intelligenza-artificiale-per-venditori",
  title: "CRM con intelligenza artificiale per venditori: cosa cercare davvero",
  description:
    "\"Intelligenza artificiale\" è ormai su ogni pagina prodotto di ogni CRM, ma dietro l'etichetta si nascondono cose molto diverse. Quattro domande concrete per capire cosa stai davvero comprando, prima di scegliere.",
  publishedAt: "2026-08-23",
  draft: false,
  blocks: [
    {
      type: "p",
      text: "Non esiste più un CRM che non scriva \"intelligenza artificiale\" da qualche parte nella propria homepage. Il problema è che l'etichetta copre cose molto diverse: da un chatbot che riassume ciò che già vedi a schermo, a un assistente che può davvero leggere e modificare i tuoi dati. Prima di scegliere in base a quella parola, vale la pena farsi quattro domande concrete.",
    },
    { type: "h2", text: "1. Può solo rispondere, o può anche agire?" },
    {
      type: "p",
      text: "La forma più comune di \"AI nel CRM\" è un chatbot che risponde a domande sui dati che hai già inserito: \"quanti clienti ho contattato questo mese?\", \"qual è il mio cliente più importante?\". Utile, ma è pur sempre un motore di ricerca con un'interfaccia conversazionale — tu hai comunque inserito tutto a mano prima. Una differenza più rara, e più utile per chi lavora sul campo, è un assistente che può anche scrivere: registrare un cliente, un appuntamento, un'offerta, una nota, mentre sei ancora in macchina dopo una visita, con un comando vocale o testuale invece di aprire un modulo e compilarlo campo per campo.",
    },
    { type: "h2", text: "2. Chi controlla le azioni che toccano soldi?" },
    {
      type: "p",
      text: "Se un assistente può scrivere dati, la domanda successiva è cosa succede quando quel dato è un'offerta accettata o una spesa: un comando vocale trascritto male (\"1.500\" sentito come \"15.000\") non deve poter generare un record economico senza che tu lo riveda. Un CRM serio con AI che scrive dovrebbe sempre interporre una conferma esplicita prima di salvare qualunque cosa tocchi provvigioni, importi o fatturato — non eseguire e basta perché \"ha capito bene\" nella maggior parte dei casi.",
    },
    { type: "h2", text: "3. Ha memoria, o riparte da zero ogni volta?" },
    {
      type: "p",
      text: "Un assistente senza memoria della conversazione ti costringe a ripetere il contesto ogni volta che lo apri: chi sei, cosa stavi facendo, di quale cliente stavi parlando. Un assistente che conserva lo storico delle conversazioni precedenti permette invece di riprendere il filo — \"quel cliente di cui parlavamo ieri\" ha senso solo se il sistema se lo ricorda davvero, non solo se il modello linguistico sotto è bravo.",
    },
    { type: "h2", text: "4. È incluso, o è un componente aggiuntivo a parte?" },
    {
      type: "p",
      text: "Molti CRM vendono le funzioni AI come un add-on separato, spesso riservato ai piani più alti o a un costo a consumo indipendente dall'abbonamento base. Vale la pena controllare se la funzione che ti interessa davvero (scrivere dati, non solo rispondere) è compresa nel prezzo che stai già valutando, o se scoprirai il costo reale solo dopo aver iniziato a usarla.",
    },
    { type: "h2", text: "Come risponde SalesFly a questi quattro punti" },
    {
      type: "p",
      text: "L'assistente AI di SalesFly non si limita a rispondere: può registrare direttamente clienti, appuntamenti, lead, note, offerte, ordini, spese, provvigioni manuali, dipendenti e mezzi — dietro conferma esplicita dell'utente per ogni azione che genera un record economico (offerte accettate, spese, ordini, provvigioni), proprio per il motivo del punto 2: un comando vocale impreciso non deve mai poter scrivere un numero sbagliato senza che tu lo riveda prima.",
    },
    {
      type: "p",
      text: "Mantiene memoria delle conversazioni precedenti, così non devi reintrodurre il contesto ogni volta che lo riapri. Ed è incluso nel prezzo base, non un componente separato: il piano Base (€6/mese) include fino a 100 messaggi al mese, il piano Pro (€11/mese) li rende illimitati — nessun costo a consumo nascosto, nessun piano \"AI\" a parte da aggiungere.",
    },
    {
      type: "p",
      text: "Il modo più diretto per verificarlo è provarlo: 14 giorni di prova gratuita su entrambi i piani, senza carta di credito richiesta.",
    },
  ],
};

// CommonJS apposta: leggibile sia da webpack/Babel che da Node in
// scripts/prerender.js senza transpilazione — vedi il commento in
// calcolo-provvigioni-agente-di-commercio.js per il perché.
module.exports = { article };

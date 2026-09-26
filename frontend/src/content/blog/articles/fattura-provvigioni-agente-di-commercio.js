const article = {
  slug: "fattura-provvigioni-agente-di-commercio",
  title: "Fattura delle provvigioni: come la emette un agente di commercio (con esempio)",
  description:
    "Quando fatturare una provvigione, cosa scrivere in fattura, come si espongono ritenuta d'acconto ed ENASARCO e cosa cambia in regime forfettario: la fattura passo per passo, con un esempio numerico.",
  publishedAt: "2026-09-21",
  draft: false,
  blocks: [
    {
      type: "p",
      text: "Le regole su ritenuta d'acconto e contributo ENASARCO sono già chiare a molti agenti. Il punto dove si sbaglia più spesso è un altro: mettere tutto insieme in una fattura vera. Quale importo diventa imponibile, dove compare la ritenuta, in che modo si indica ENASARCO, cosa si scrive se si è forfettari, e soprattutto quando la fattura va emessa. Qui la fattura delle provvigioni viene ricostruita riga per riga, con un esempio numerico.",
    },
    { type: "h2", text: "Quando si emette: al pagamento, non alla maturazione" },
    {
      type: "p",
      text: "L'articolo 6 del DPR 633/1972 stabilisce che le prestazioni di servizi si considerano effettuate all'atto del pagamento del corrispettivo. Per un agente questo significa che l'obbligo di fatturare non nasce quando la provvigione matura, ma quando il mandante la paga. La prassi consolidata è emettere la fattura al momento dell'incasso (o subito prima), di solito dopo aver ricevuto l'estratto conto delle provvigioni maturate. Due conseguenze pratiche: una provvigione maturata a dicembre e pagata a gennaio si fattura nell'anno nuovo; e un anticipo ricevuto (o una fattura emessa in anticipo) rende l'operazione effettuata per quell'importo, quindi la fattura va emessa comunque.",
    },
    { type: "h2", text: "Cosa contiene la fattura" },
    {
      type: "ul",
      items: [
        "I dati soliti di una fattura: numero, data, dati dell'agente e del mandante, descrizione della prestazione (ad esempio \"Provvigioni maturate nel trimestre, come da estratto conto n. …\").",
        "L'imponibile: l'importo complessivo delle provvigioni, non ridotto né di ritenuta né di ENASARCO.",
        "L'IVA, se dovuta: aliquota ordinaria del 22% in regime ordinario, calcolata sull'intero imponibile.",
        "La ritenuta d'acconto, se dovuta: 23% applicato sulla base ridotta (50% della provvigione, oppure 20% con la dichiarazione dei collaboratori), indicata in basso come importo da sottrarre.",
        "Il contributo ENASARCO a carico dell'agente, esposto in basso come voce negativa, con una dicitura del tipo \"Contributo ENASARCO 8,50% a carico agente, non soggetto a IVA, esposto per trasparenza e trattenuto dal committente ai fini del versamento all'ente\".",
        "Il netto a pagare, che è il totale dopo tutte le trattenute.",
      ],
    },
    {
      type: "p",
      text: "Due dettagli che generano errori. Primo: ENASARCO non riduce la base su cui si calcola l'IVA, perché non è un corrispettivo ma una trattenuta operata dal mandante. Secondo: ritenuta ed ENASARCO sono importi che il mandante versa per conto dell'agente (il fisco e l'ente previdenziale), quindi si sottraggono dal totale in basso, non dall'imponibile. Le aliquote e le condizioni della base ridotta sono spiegate nell'[articolo dedicato alla ritenuta d'acconto](/blog/ritenuta-acconto-contributi-enasarco-fattura).",
    },
    { type: "h2", text: "Un esempio: provvigione di 1.000 euro in regime ordinario" },
    {
      type: "ul",
      items: [
        "Provvigioni (imponibile): 1.000,00 €",
        "IVA 22%: 220,00 €",
        "Totale fattura: 1.220,00 €",
        "Ritenuta d'acconto (23% del 50% di 1.000): − 115,00 €",
        "Contributo ENASARCO a carico agente (8,5%): − 85,00 €",
        "Netto a pagare da parte del mandante: 1.020,00 €",
      ],
    },
    {
      type: "p",
      text: "L'agente incassa 1.020 euro, ma il ricavo su cui pagherà le imposte resta 1.000: la ritenuta di 115 euro è un acconto sull'imposta dell'anno, si recupera in dichiarazione, e l'IVA di 220 euro entra nelle liquidazioni IVA. Il calcolatore nell'[articolo sulla ritenuta](/blog/ritenuta-acconto-contributi-enasarco-fattura) permette di provare importi diversi.",
    },
    { type: "h2", text: "In regime forfettario: una fattura più leggera" },
    {
      type: "p",
      text: "Con la stessa provvigione di 1.000 euro, in regime forfettario la fattura non riporta IVA e non applica ritenuta d'acconto. Resta il contributo ENASARCO (8,5%, quindi 85 euro), sempre dovuto e sempre esposto: il netto è 915 euro. Se l'importo supera 77,47 euro, sulla fattura va assolta l'imposta di bollo da 2 euro, di norma addebitata al mandante in fattura. Vanno inoltre inserite le diciture di legge sul regime e sull'esenzione dalla ritenuta, riportate nell'[articolo sulla ritenuta d'acconto](/blog/ritenuta-acconto-contributi-enasarco-fattura).",
    },
    { type: "h2", text: "Sempre in formato elettronico" },
    {
      type: "p",
      text: "La fattura tra un agente e un mandante italiano è una fattura elettronica emessa tramite il Sistema di Interscambio. Dal 1° gennaio 2024 l'obbligo riguarda anche tutti i forfettari, senza soglie di reddito. Le voci di ritenuta ed ENASARCO hanno campi dedicati nel tracciato XML, ma i codici da utilizzare dipendono dal software di fatturazione: è il punto in cui conviene affidarsi al proprio gestionale o al commercialista, invece di compilarli a mano.",
    },
    { type: "h2", text: "Cosa non copre questa guida" },
    {
      type: "p",
      text: "Mandanti esteri, operazioni con inversione contabile e casi particolari di regime (ad esempio forfettari con soglie superate nell'anno) seguono regole diverse: per quei casi la verifica con il proprio commercialista non è opzionale.",
    },
    {
      type: "cta",
      title: "Sapere in anticipo quanto incassi davvero",
      text: "SalesFly calcola le provvigioni per ogni mandante e mostra il netto stimato dopo ritenuta ed ENASARCO, così sai quanto aspettarti prima ancora di emettere la fattura. 14 giorni di prova gratuita, senza carta di credito.",
      href: "/richiedi-demo",
      cta: "Inizia prova gratuita",
    },
  ],
};

export { article };

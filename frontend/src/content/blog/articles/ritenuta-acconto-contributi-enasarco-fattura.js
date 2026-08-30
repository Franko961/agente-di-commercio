const article = {
  slug: "ritenuta-acconto-contributi-enasarco-fattura",
  title: "Come calcolare la ritenuta d'acconto e i contributi ENASARCO in fattura (guida + calcolatore)",
  description:
    "Aliquota, base imponibile ordinaria e ridotta, l'esenzione per chi è in regime forfettario e il contributo ENASARCO a carico dell'agente: la guida con un calcolatore per capire cosa resta netto da ogni provvigione.",
  publishedAt: "2026-08-30",
  draft: false,
  blocks: [
    {
      type: "p",
      text: "Ogni volta che un agente di commercio emette fattura per una provvigione, sulla stessa cifra si intrecciano due trattenute diverse per natura: la ritenuta d'acconto, che è un anticipo sulle imposte sul reddito, e il contributo ENASARCO, che è previdenza. Sono regole scritte in norme diverse, con eccezioni diverse — ed è facile confondersi tra le due, soprattutto quando cambia il regime fiscale. Questa guida le separa con chiarezza, con le aliquote 2026, e in fondo trovi un calcolatore per vedere subito cosa resta netto da una provvigione.",
    },
    { type: "h2", text: "La ritenuta d'acconto: cos'è e chi la applica" },
    {
      type: "p",
      text: "La ritenuta d'acconto sulle provvigioni degli agenti di commercio è disciplinata dall'art. 25-bis del DPR 600/1973: è il mandante, in qualità di sostituto d'imposta, a trattenerla al momento del pagamento e a versarla per conto dell'agente — un anticipo sulle tasse che l'agente dovrà comunque pagare a fine anno, non un costo aggiuntivo. L'aliquota nominale è il 23% (il primo scaglione IRPEF), ma non si applica sull'intero importo della provvigione: si applica solo su una base imponibile ridotta, il cui valore dipende dalla situazione dell'agente.",
    },
    { type: "h2", text: "Base ordinaria (50%) o base ridotta (20%): la differenza reale" },
    {
      type: "ul",
      items: [
        "Base ordinaria — 50% della provvigione: è il caso standard, quello che si applica per default a chi non ha comunicato nulla di diverso al mandante. Aliquota effettiva sull'intera provvigione: 23% × 50% = 11,5%.",
        "Base ridotta — 20% della provvigione: riservata a chi dichiara di avvalersi in via continuativa dell'opera di dipendenti o di terzi nella propria attività (con una soglia, se sono terzi: i relativi costi devono superare il 30% delle provvigioni percepite nell'anno precedente). Aliquota effettiva: 23% × 20% = 4,6%.",
      ],
    },
    {
      type: "p",
      text: "La base ridotta non è automatica: va comunicata formalmente al mandante — per raccomandata A/R o PEC — entro il 31 dicembre dell'anno precedente a quello in cui deve valere. Senza questa comunicazione, il mandante applica la base ordinaria (11,5%), a prescindere da come è effettivamente organizzata l'attività dell'agente.",
    },
    { type: "h2", text: "L'eccezione che cambia tutto: il regime forfettario" },
    {
      type: "p",
      text: "Chi fattura in regime forfettario non subisce la ritenuta d'acconto: è un'esenzione prevista dalla Legge 190/2014 (comma 67), non una scelta del mandante. Per farla valere, la fattura deve riportare la dicitura corretta — tipicamente \"Regime forfettario – Operazione effettuata ai sensi dell'articolo 1, commi da 54 a 89, della Legge n. 190/2014 – Regime forfettario, non soggetta a ritenuta d'acconto ai sensi dell'articolo 1, comma 67, della medesima Legge\" — e la condizione va comunicata al mandante, che altrimenti può applicare la ritenuta comunque. Se in futuro si passa al regime ordinario, l'obbligo di ritenuta torna ad applicarsi da quel momento.",
    },
    { type: "h2", text: "Il contributo ENASARCO: previdenza, non imposta" },
    {
      type: "p",
      text: "Il contributo ENASARCO segue una logica completamente diversa dalla ritenuta d'acconto — è previdenza, non un anticipo d'imposta — e per questo si applica indipendentemente dal regime fiscale: forfettario compreso. L'aliquota complessiva 2026 è il 17% della provvigione, ripartita in parti uguali tra mandante e agente: 8,5% a testa. È la quota dell'8,5% a carico dell'agente quella che riduce l'incasso netto — l'altro 8,5% è un costo del mandante e non passa dalla fattura dell'agente. Per i massimali e i minimali contributivi 2026, distinti tra rapporto plurimandatario e monomandatario, trovi tutti i valori aggiornati nell'articolo dedicato qui sotto.",
    },
    {
      type: "p",
      text: "Una differenza pratica da tenere a mente: in regime forfettario il contributo ENASARCO resta dovuto per intero, ma — a differenza del regime ordinario — non è deducibile dal reddito imponibile ai fini del calcolo delle imposte, perché nel forfettario le imposte si calcolano su un coefficiente di redditività applicato al fatturato lordo, non sul reddito al netto dei costi reali.",
    },
    {
      type: "calculator",
      name: "ritenutaEnasarco",
    },
    { type: "h2", text: "Riepilogo: cosa trattenere in base alla propria situazione" },
    {
      type: "ul",
      items: [
        "Regime forfettario: nessuna ritenuta d'acconto (con dicitura corretta in fattura), ma ENASARCO all'8,5% a carico dell'agente resta dovuto per intero.",
        "Regime ordinario, base standard: ritenuta d'acconto all'11,5% + ENASARCO 8,5% a carico dell'agente.",
        "Regime ordinario, con dichiarazione di base ridotta comunicata entro il 31 dicembre dell'anno precedente: ritenuta d'acconto al 4,6% + ENASARCO 8,5% a carico dell'agente.",
      ],
    },
    {
      type: "cta",
      title: "Le provvigioni le calcola SalesFly, non un foglio Excel",
      text: "Ogni vendita genera automaticamente la provvigione giusta per il mandante e l'aliquota corretta — la fattura e le trattenute restano al commercialista, ma il calcolo di partenza non lo rifai a mano ogni volta.",
      href: "/richiedi-demo",
      cta: "Inizia prova gratuita",
    },
  ],
};

export { article };

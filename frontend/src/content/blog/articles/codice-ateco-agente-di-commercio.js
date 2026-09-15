const article = {
  slug: "codice-ateco-agente-di-commercio",
  title: "Codice ATECO per l'agente di commercio: quale scegliere in base al settore",
  description:
    "Non esiste un unico codice ATECO per 'agente di commercio': dipende dal prodotto che rappresenti. La guida ai codici giusti per settore, le eccezioni (auto ed energia) e la novità ATECO 2025.",
  publishedAt: "2026-09-15",
  draft: false,
  blocks: [
    {
      type: "p",
      text: "\"Qual è il codice ATECO dell'agente di commercio?\" è una domanda che, posta così, non ha una risposta unica — ed è per questo che genera tanta confusione a chi sta per aprire la partita IVA. Il motivo è semplice una volta capito: l'ATECO non classifica la qualifica professionale (\"agente di commercio\" in sé), ma l'attività economica svolta — e per un intermediario del commercio quell'attività dipende dal tipo di prodotto che rappresenta. Un agente che vende macchinari industriali e uno che vende prodotti alimentari sono entrambi \"agenti di commercio\" a tutti gli effetti (stesso contratto di agenzia, stesso obbligo ENASARCO), ma hanno due codici ATECO diversi.",
    },
    { type: "h2", text: "Il gruppo giusto: 46.1, Intermediari del commercio" },
    {
      type: "p",
      text: "La maggior parte degli agenti di commercio rientra nella divisione 46 (\"Commercio all'ingrosso\"), gruppo 46.1: \"Attività di servizi di intermediazione per il commercio all'ingrosso\" — la categoria pensata proprio per chi fa da tramite tra chi vende e chi compra, a fronte di una provvigione, senza mai diventare proprietario della merce trattata. Da qui si scende di livello in base al settore merceologico:",
    },
    {
      type: "ul",
      items: [
        "46.11 — materie prime agricole, animali vivi, materie prime tessili e semilavorati",
        "46.12 — combustibili, minerali, metalli e prodotti chimici",
        "46.13 — legname e materiali da costruzione",
        "46.14 — macchinari, impianti industriali, navi e aeromobili",
        "46.15 — mobili, articoli per la casa e ferramenta",
        "46.16 — prodotti tessili, abbigliamento, pellicce, calzature e articoli in pelle",
        "46.17 — prodotti alimentari, bevande e tabacco",
        "46.18 — altri prodotti specifici (tra cui, con un proprio sotto-codice, i prodotti farmaceutici e cosmetici)",
        "46.19 — vari prodotti, senza prevalenza di alcuno",
      ],
    },
    {
      type: "p",
      text: "Ogni gruppo si divide poi in codici più specifici a sei cifre (es. 46.15.01 per mobili in legno e metallo, 46.15.02 per ferramenta e bricolage): quello giusto per la tua attività va individuato con il commercialista al momento dell'iscrizione, ma sapere già il gruppo corretto evita l'errore più comune — cercare un codice \"agente di commercio\" generico che semplicemente non esiste.",
    },
    { type: "h2", text: "Le due eccezioni che confondono di più: auto ed energia" },
    {
      type: "p",
      text: "Due categorie molto comuni tra chi cerca il proprio codice ATECO non rientrano affatto nel gruppo 46.1, ed è per questo che restano introvabili a chi si aspetta un 46.1x: gli agenti che rappresentano autovetture e veicoli leggeri usano il codice 45.11.02 (la divisione 45 è dedicata specificamente al commercio di autoveicoli, tenuta separata dal resto del commercio all'ingrosso), mentre chi vende energia elettrica e gas per conto di un fornitore usa il codice 35.14.00 — che appartiene addirittura a una divisione diversa (la 35, fornitura di energia), non al commercio. Due eccezioni da conoscere prima di perdere tempo a cercarle nel gruppo sbagliato.",
    },
    { type: "h2", text: "Rappresenti prodotti di settori diversi? Il codice 46.19.00" },
    {
      type: "p",
      text: "Chi lavora con più mandanti — la normalità per un plurimandatario — spesso rappresenta prodotti che non rientrano in un'unica categoria merceologica. Per questo caso esiste il codice 46.19.00, \"Intermediari del commercio di vari prodotti senza prevalenza di alcuno\": pensato esattamente per chi non ha un settore prevalente ma lavora su più fronti. Con la revisione ATECO 2025 questo codice ha anche assorbito e sostituito quattro codici precedenti che erano tenuti separati (agenti e rappresentanti, procacciatori d'affari, mediatori e gruppi d'acquisto \"di vari prodotti senza prevalenza\"), semplificando una distinzione che nella pratica creava più confusione che chiarezza.",
    },
    { type: "h2", text: "La novità 2025: riclassificazione automatica, ma da verificare" },
    {
      type: "p",
      text: "Dal 1° gennaio 2025 è in vigore la nuova classificazione ATECO 2025, adottata operativamente dai Registri Imprese delle Camere di Commercio a partire dal 1° aprile 2025: un aggiornamento della tabella ATECO 2007 (già rivista nel 2022) per riflettere meglio le attività economiche attuali. La transizione è stata pensata per non generare adempimenti a carico delle imprese già attive: la riclassificazione dal vecchio al nuovo codice è avvenuta in automatico. Resta comunque consigliabile controllare, tramite il cassetto digitale della propria Camera di Commercio, quale codice risulta assegnato dopo la migrazione — soprattutto per chi aveva uno dei codici \"senza prevalenza\" confluiti ora nel 46.19.00, o per chi si iscrive oggi per la prima volta.",
    },
    { type: "h2", text: "Una buona notizia per il regime forfettario" },
    {
      type: "p",
      text: "Ai fini del regime forfettario, la scelta tra i vari sotto-codici del gruppo 46.1 non cambia il calcolo delle tasse: tutti i codici che iniziano con 46.1 condividono lo stesso coefficiente di redditività, il 62% (il reddito imponibile è il 62% dei ricavi incassati, su cui si applica l'imposta sostitutiva del 15%, o 5% per i primi anni di attività in determinate condizioni). Che tu venda mobili, alimentari o macchinari industriali, il trattamento fiscale in forfettario è identico — la scelta del codice giusto serve per la classificazione dell'attività, non cambia quanto pagherai.",
    },
    {
      type: "cta",
      title: "Provvigioni per mandante, sempre chiare",
      text: "Che tu abbia un codice ATECO o dieci mandanti in settori diversi, SalesFly tiene provvigioni, ritenuta e contributi ENASARCO separati per ciascuno. 14 giorni di prova gratuita, senza carta di credito.",
      href: "/richiedi-demo",
      cta: "Inizia prova gratuita",
    },
  ],
};

export { article };

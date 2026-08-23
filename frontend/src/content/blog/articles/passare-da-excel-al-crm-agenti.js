const article = {
  slug: "passare-da-excel-al-crm-agenti",
  title: "Come passare da Excel al CRM per agenti di commercio (senza perdere tutto il lavoro fatto)",
  description:
    "Molti agenti di commercio restano su Excel non perché funzioni bene, ma per paura di dover reinserire a mano anni di clienti e dati. Cosa si rompe davvero con un foglio di calcolo, e come si migra senza ripartire da zero.",
  publishedAt: "2026-08-23",
  draft: false,
  blocks: [
    {
      type: "p",
      text: "Quasi ogni agente di commercio che usa Excel sa già che non è la soluzione ideale — eppure ci resta, spesso per un motivo molto pratico: il timore di perdere anni di clienti e dati inseriti, e dover ricominciare da zero su un altro strumento. È un timore ragionevole, ma superabile. Prima vediamo cosa si rompe davvero con un foglio di calcolo quando il lavoro cresce, poi come si passa a un CRM senza reinserire tutto a mano.",
    },
    { type: "h2", text: "Il problema silenzioso: le formule di provvigione che si rompono" },
    {
      type: "p",
      text: "Un foglio con le formule di provvigione funziona bene finché non cambia qualcosa: un mandante che rivede un'aliquota, uno scaglione premio aggiunto, una riga inserita nel posto sbagliato che sposta un riferimento di cella. Il problema è che Excel non ti avvisa quando succede — il totale sembra plausibile, e l'errore si scopre solo mesi dopo, se va bene. Un sistema che applica le regole di calcolo direttamente (aliquota per mandante, scaglioni, differenza tra nuovo e rinnovo) invece di lasciarle scritte in una formula che chiunque può alterare per sbaglio, elimina proprio questa categoria di errore.",
    },
    { type: "h2", text: "Non è pensato per il telefono" },
    {
      type: "p",
      text: "Un agente di commercio lavora prevalentemente fuori ufficio, ma un foglio Excel su smartphone è scomodo da consultare e quasi impossibile da aggiornare in movimento — così tutto viene rimandato a sera, quando i dettagli della giornata sono già più sfumati nella memoria. Uno strumento pensato per essere usato davvero da telefono, tra un cliente e l'altro, elimina questo rimando sistematico.",
    },
    { type: "h2", text: "Nessun collegamento tra i dati" },
    {
      type: "p",
      text: "In Excel, clienti, ordini, provvigioni e spese vivono spesso in fogli (o file) separati, senza un collegamento reale tra loro: per sapere quale ordine ha generato quale provvigione, o quanto ha comprato un cliente nell'ultimo anno, serve incrociare manualmente più fonti. In un CRM, un ordine genera automaticamente la provvigione collegata — un solo posto da controllare, non tre.",
    },
    { type: "h2", text: "Un solo file, tante versioni" },
    {
      type: "p",
      text: "Un file su un computer, magari sincronizzato (o no) su un altro, aggiornato su entrambi in momenti diversi: prima o poi arriva il conflitto, la versione persa, la modifica sovrascritta senza accorgersene. Uno strumento web, con un'unica fonte di verità sempre aggiornata, elimina questo rischio a monte — non c'è \"la versione giusta\" da cercare, ce n'è solo una.",
    },
    { type: "h2", text: "Nessun promemoria automatico" },
    {
      type: "p",
      text: "Un foglio Excel non ti avvisa se un cliente non ordina da 90 giorni, se un'offerta sta per scadere o se un lead è rimasto senza risposta per settimane — a meno di controllarlo manualmente ogni volta, cosa che con decine di clienti e più mandanti diventa presto impraticabile.",
    },
    { type: "h2", text: "Come si passa davvero, senza reinserire tutto a mano" },
    {
      type: "p",
      text: "Il punto che frena di più la migrazione è l'idea di dover ridigitare a mano l'intero elenco clienti accumulato in anni. Con SalesFly non serve: l'importazione clienti legge direttamente il file CSV o Excel che hai già, mostra a schermo come le colonne del tuo file corrispondono ai campi del CRM e lascia correggere eventuali abbinamenti prima di confermare — non un semplice caricamento alla cieca, ma un passaggio guidato pensato apposta per chi arriva da un foglio di calcolo reale, non da un file di esempio perfetto.",
    },
    {
      type: "p",
      text: "Da lì in poi, le provvigioni si calcolano da sole in base alle aliquote di ogni mandante, il giro visite si pianifica su mappa, e i promemoria per clienti inattivi o offerte in scadenza arrivano da soli. Si può provare con 14 giorni di prova gratuita, senza carta di credito, per vedere se il proprio elenco clienti si importa davvero senza sorprese prima di decidere.",
    },
  ],
};

// CommonJS apposta: leggibile sia da webpack/Babel che da Node in
// scripts/prerender.js senza transpilazione — vedi il commento in
// calcolo-provvigioni-agente-di-commercio.js per il perché.
module.exports = { article };

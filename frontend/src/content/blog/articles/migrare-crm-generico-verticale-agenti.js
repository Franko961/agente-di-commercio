const article = {
  slug: "migrare-crm-generico-verticale-agenti",
  title: "Migrare da un CRM generico a uno verticale per agenti: cosa succede davvero",
  description:
    "Chi lavora già su Salesforce, Pipedrive, HubSpot o Zoho non parte da un foglio Excel disordinato: la domanda è diversa. Cosa si porta dietro davvero, cosa si perde, e quando ha senso cambiare.",
  publishedAt: "2026-09-09",
  draft: false,
  blocks: [
    {
      type: "p",
      text: "Chi lavora già su un CRM generico — Salesforce, Pipedrive, HubSpot, Zoho — non ha il problema di chi parte da un foglio Excel disordinato: i dati sono già strutturati, puliti, con uno storico. La domanda che conta è un'altra: vale la pena spostarli su uno strumento verticale, pensato per un agente plurimandatario, o è solo il rischio di rompere qualcosa che oggi funziona? Vediamo cosa si porta dietro davvero, cosa si perde, e quando la risposta è sì.",
    },
    { type: "h2", text: "Cosa si esporta senza problemi" },
    {
      type: "p",
      text: "L'esportazione dell'anagrafica clienti in CSV o Excel è una funzione standard su tutti i CRM generalisti principali — Salesforce, Pipedrive, HubSpot e Zoho la offrono tutti dalle rispettive impostazioni, senza bisogno di supporto tecnico o richieste particolari. Nome azienda, referente, email, telefono, indirizzo, città: questi campi si portano dietro senza attrito, nella quasi totalità dei casi con un semplice export/import.",
    },
    { type: "h2", text: "Il vero collo di bottiglia: il mandante non esiste nel CRM che stai lasciando" },
    {
      type: "p",
      text: "Qui sta la differenza pratica rispetto a una migrazione da Excel. Un CRM generico non ha il concetto di \"mandante\" — l'azienda che rappresenti e per cui quel cliente genera provvigione — semplicemente perché non è pensato per un agente plurimandatario. Nell'export, quell'informazione o non esiste, oppure è infilata a forza in un campo personalizzato, una pipeline diversa, o un tag. In SalesFly il mandante è un'entità di prima classe fin dall'inizio: l'importazione clienti in blocco legge il file CSV/Excel (fino a 2000 righe in un colpo solo, più che sufficiente per il portafoglio di un singolo agente) e per ogni cliente accetta il nome del mandante direttamente in una colonna — risolto automaticamente lato server, senza dover conoscere id interni. Ma quella colonna, chi migra da un CRM generico, deve compilarla lui: nessun sistema può indovinare da un export di Pipedrive quale dei tuoi clienti appartiene a quale mandante, se quell'informazione lì non è mai stata tracciata come tale.",
    },
    { type: "h2", text: "Cosa si perde davvero (mettiamolo per iscritto)" },
    {
      type: "p",
      text: "Va detto senza girarci intorno: nessuna migrazione tra CRM diversi porta con sé tutto. Lo storico delle attività (chiamate registrate, note collegate a una fase specifica della trattativa, cronologia email nel CRM), le automazioni configurate, le dashboard personalizzate — questo resta indietro, ed è vero migrando verso SalesFly come sarebbe vero migrando tra due CRM generalisti qualsiasi. Quello che si porta dietro senza perdite è il dato strutturale: anagrafica clienti, contatti, e — con un minimo di lavoro manuale sulla colonna mandante — la relazione commerciale di fondo. Chi ha anni di note dettagliate cliente per cliente e ci tiene, farà bene ad esportarle e tenerle da parte come archivio consultabile, non aspettarsi che confluiscano automaticamente in un sistema nuovo.",
    },
    { type: "h2", text: "Quando ha senso migrare, quando no" },
    {
      type: "p",
      text: "Ha senso se lavori da solo o in una struttura molto piccola, rappresenti più mandanti con aliquote e cataloghi diversi, e oggi ricostruisci quella logica a mano con campi personalizzati in un CRM che non la conosce nativamente — è esattamente lo scenario in cui il tempo risparmiato da un calcolo automatico delle provvigioni per mandante supera il costo di reinserire manualmente pochi mandanti sulle righe già esportate. Ha meno senso se lavori in un team con pipeline condivisa tra più commerciali, reportistica aggregata a livello di organizzazione, o processi di vendita complessi con più fasi di approvazione: SalesFly è pensato per l'agente plurimandatario che lavora principalmente da solo, non per sostituire un CRM aziendale multi-utente con logiche di team.",
    },
    {
      type: "cta",
      title: "Prova prima con il tuo export reale",
      text: "L'importazione clienti legge direttamente il CSV o Excel esportato dal tuo CRM attuale — 14 giorni di prova gratuita, senza carta di credito, per vedere se i tuoi dati entrano senza sorprese.",
      href: "/richiedi-demo",
      cta: "Inizia prova gratuita",
    },
  ],
};

export { article };

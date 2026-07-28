// Contenuti del Centro assistenza in-app (/app/aiuto). A differenza degli
// articoli del blog pubblico (content/blog/), qui ogni articolo è pensato
// per essere letto in meno di un minuto: una sola risposta pratica a una
// domanda concreta, non una guida estesa. Il campo `icon` è solo una
// stringa (nome dell'icona lucide-react) risolta nel componente, per non
// far dipendere questo file dalla libreria di icone.
export const HELP_CATEGORIES = [
  {
    id: "iniziare",
    label: "Iniziare",
    icon: "Rocket",
    articles: [
      {
        title: "Da dove iniziare con SalesFly",
        body: "Il primo passo è creare almeno un Mandante (Mandanti → Nuovo), con la sua aliquota di provvigione e, se vuoi, una scala premi. Poi aggiungi i tuoi clienti, uno alla volta o importando un file da Clienti → Importa. Da lì puoi già fissare il primo appuntamento in Agenda, preparare un'offerta, o semplicemente aprire l'Assistente AI e chiedergli di farlo al posto tuo, scrivendo o parlando in linguaggio naturale. Imposta anche i tuoi obiettivi mensili in Impostazioni → Obiettivi: la Dashboard li userà per calcolare quanto ti manca ogni giorno.",
      },
    ],
  },
  {
    id: "clienti",
    label: "Clienti",
    icon: "Users",
    articles: [
      {
        title: "Come organizzare la tua anagrafica clienti",
        body: "Ogni cliente ha zona, settore merceologico e potenziale (basso/medio/alto): usali per filtrare velocemente il portafoglio. Se aggiungi indirizzo o posizione sulla mappa, il cliente compare anche in Mappa e può entrare nel pianificatore giro visite. Nella scheda cliente trovi lo storico ordini, offerte, appuntamenti e documenti collegati in un unico posto. Puoi importare più clienti insieme da un file Excel/CSV da Clienti → Importa, oppure aggiungerli uno a uno chiedendo all'Assistente AI.",
      },
    ],
  },
  {
    id: "lead",
    label: "Lead",
    icon: "KanbanSquare",
    articles: [
      {
        title: "Come funziona la pipeline lead",
        body: "Ogni lead passa attraverso le colonne Nuovo → Contattato → Qualificato → Trattativa → Vinto/Perso: trascinalo da una colonna all'altra man mano che la trattativa avanza. Registra ogni contatto avuto (chiamata, email, visita) per tenere traccia di quando hai sentito l'ultima volta un lead — è anche il dato che l'automazione 'lead inattivo' usa per avvisarti se resta fermo troppo a lungo. Quando chiudi un lead come vinto, trasformalo in un cliente vero e proprio.",
      },
    ],
  },
  {
    id: "agenda",
    label: "Agenda",
    icon: "CalendarDays",
    articles: [
      {
        title: "Come gestire appuntamenti e promemoria",
        body: "L'Agenda mostra la settimana corrente con gli appuntamenti pianificati per ogni giorno. Puoi collegare ogni appuntamento a un cliente, e se hai collegato Google Calendar (Impostazioni → Integrazioni) la sincronizzazione è automatica nei due sensi. Il briefing mattutino dell'Assistente AI ti ricorda quanti appuntamenti hai oggi e tra quanti minuti è il prossimo, senza che tu debba controllare l'agenda.",
      },
    ],
  },
  {
    id: "ordini",
    label: "Ordini",
    icon: "ShoppingCart",
    articles: [
      {
        title: "Come registrare un ordine",
        body: "Un ordine nasce quasi sempre da un'offerta accettata o firmata: SalesFly lo crea automaticamente, con numero progressivo e provvigione già calcolata, senza bisogno di inserirlo a mano. Puoi anche crearne uno direttamente da Ordini → Nuovo se non parte da un'offerta. Ogni ordine ha uno stato (confermato, evaso, annullato...) e uno stato di pagamento, entrambi modificabili in qualsiasi momento dalla sua scheda.",
      },
    ],
  },
  {
    id: "provvigioni",
    label: "Provvigioni",
    icon: "Coins",
    articles: [
      {
        title: "Come funziona il calcolo delle provvigioni",
        body: "Ogni mandante ha una propria aliquota base, che può essere diversa per vendita 'nuovo' o 'rinnovo'. Quando un ordine viene confermato, la provvigione si calcola da sola sul totale, con l'aliquota giusta per quel mandante e quel tipo di vendita. Se un mandante ha anche una scala premi (soglie di fatturato mensile con bonus a scaglioni), SalesFly verifica automaticamente quali soglie hai raggiunto e aggiunge il bonus dovuto, senza calcoli manuali.",
      },
    ],
  },
  {
    id: "ai",
    label: "AI",
    icon: "Sparkles",
    articles: [
      {
        title: "Cosa può fare l'Assistente AI",
        body: "Puoi scrivere o parlare in linguaggio naturale per aggiungere clienti, appuntamenti, offerte, ordini e note: l'assistente capisce cosa vuoi fare e lo esegue, chiedendoti conferma prima di ogni azione che modifica davvero i tuoi dati. Ogni mattina ti apre anche con un riepilogo della giornata (visite, offerte in scadenza, quanto manca all'obiettivo), senza che tu debba chiedere nulla.",
      },
    ],
  },
  {
    id: "automazioni",
    label: "Automazioni",
    icon: "Zap",
    articles: [
      {
        title: "Come creare un'automazione",
        body: "Un'automazione è composta da un trigger (es. 'cliente senza ordini da 90 giorni', 'offerta in scadenza', 'nuovo cliente inserito') e un'azione che scatta quando la condizione si verifica (promemoria, task, email). Da Automazioni → Nuova regola scegli i due, imposta eventuali parametri (giorni, orario) e attiva la regola: da quel momento il sistema controlla da solo, senza bisogno di ricordartene tu.",
      },
    ],
  },
  {
    id: "giro-visite",
    label: "Giro visite",
    icon: "Navigation",
    articles: [
      {
        title: "Come ottimizzare il giro visite",
        body: "Da Mappa → Pianifica giornata seleziona i clienti da visitare oggi: SalesFly calcola l'ordine di visita più efficiente. Puoi far partire il giro dalla tua posizione GPS, da casa, dall'ufficio o da un indirizzo qualsiasi, e includere il ritorno finale al punto di partenza. Una volta calcolato, puoi salvare tutte le tappe come appuntamenti in Agenda con un solo clic.",
      },
    ],
  },
  {
    id: "gdpr",
    label: "GDPR",
    icon: "ShieldCheck",
    articles: [
      {
        title: "I tuoi diritti sui dati (GDPR)",
        body: "Da Impostazioni → Privacy e dati puoi scaricare in ogni momento una copia completa di tutti i tuoi dati (diritto alla portabilità, art. 20), oppure richiedere la cancellazione definitiva e irreversibile del tuo account e di tutto ciò che contiene (diritto all'oblio, art. 17). La cancellazione richiede la tua password per conferma ed è immediata: non è annullabile.",
      },
    ],
  },
];

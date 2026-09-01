const article = {
  slug: "crm-italiano-agenti-di-commercio",
  title: "CRM italiano per agenti di commercio: cosa significa davvero",
  description:
    "Non basta l'interfaccia tradotta in italiano: un CRM italiano per agenti di commercio dovrebbe capire ENASARCO, FIRR e provvigioni multi-mandante senza doverli reinventare a mano con campi personalizzati.",
  publishedAt: "2026-09-01",
  draft: false,
  blocks: [
    {
      type: "p",
      text: "Chi cerca un \"CRM italiano\" di solito non intende solo l'interfaccia in italiano — quella ce l'hanno anche i grandi CRM internazionali. Intende un CRM che capisca davvero come funziona il lavoro in Italia: ENASARCO, FIRR, provvigioni divise per mandante, ritenuta d'acconto. Concetti che per un'azienda americana o tedesca semplicemente non esistono, e che un CRM generico tradotto non conosce — al massimo li ricostruisci a mano con campi personalizzati, sperando di non sbagliare qualcosa.",
    },
    { type: "h2", text: "Il problema non è la lingua, è il mestiere" },
    {
      type: "p",
      text: "Un CRM come Salesforce o HubSpot è tradotto benissimo in italiano — pulsanti, menu, notifiche, tutto localizzato. Ma \"tradotto\" non vuol dire \"pensato per te\": il concetto di mandante come entità con la propria aliquota di provvigione, la differenza tra provvigione maturata e incassata, il calcolo del FIRR a scaglioni, l'esenzione da ritenuta d'acconto per chi è in regime forfettario — sono tutte cose che quei CRM non modellano nativamente, perché sono nati per un mercato dove semplicemente non esistono. Il risultato è quello che abbiamo già raccontato confrontando SalesFly con i CRM generalisti più diffusi: funzionano, ma vanno riadattati con campi personalizzati e automazioni fatte in casa — tempo e competenza tecnica che un agente non ha, e non dovrebbe dover avere.",
    },
    { type: "h2", text: "Cosa intendiamo, concretamente, per \"italiano\" in SalesFly" },
    {
      type: "ul",
      items: [
        "Nato dal mestiere, non adattato al mestiere: SalesFly è stato costruito da chi ha lavorato vent'anni come agente di commercio, non da un team che ha guardato il settore da fuori — ne parliamo nella pagina Chi siamo.",
        "Mandante come concetto nativo, non un campo aggiunto: ogni mandante ha la propria aliquota di provvigione, la propria scala premi, il proprio catalogo — non va ricostruito con automazioni personalizzate.",
        "Le regole italiane sono già dentro il prodotto: il calcolo automatico di ritenuta d'acconto e contributo ENASARCO sulle provvigioni reali (con le aliquote 2026 corrette per regime ordinario e forfettario) non è un'aggiunta pensata per un mercato generico — è nato leggendo le norme italiane specifiche.",
        "Supporto in italiano, con chi il mestiere lo conosce — non un centralino internazionale che smista il ticket a chi capita.",
      ],
    },
    { type: "h2", text: "Una nota onesta sul cloud" },
    {
      type: "p",
      text: "\"Italiano\" non vuol dire che i server sono fisicamente in Italia: SalesFly, come la maggior parte dei software SaaS moderni — inclusi molti concorrenti che si dicono \"100% italiani\" — si appoggia a infrastruttura cloud internazionale, con le garanzie GDPR previste per legge quando il trattamento avviene fuori dallo Spazio Economico Europeo (dettagli nella Privacy Policy). Se il criterio che cerchi è la localizzazione fisica dei server in Italia, è giusto saperlo prima di scegliere — quello che offriamo è un prodotto pensato da zero per il mestiere italiano dell'agente di commercio, non la promessa di un data center a Roma.",
    },
    {
      type: "cta",
      title: "Un CRM che il tuo mestiere lo conosce già",
      text: "Mandanti, provvigioni, ENASARCO: non li devi spiegare tu al software, li capisce già.",
      href: "/richiedi-demo",
      cta: "Inizia prova gratuita",
    },
  ],
};

export { article };

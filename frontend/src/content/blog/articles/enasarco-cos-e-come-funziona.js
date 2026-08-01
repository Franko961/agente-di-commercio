const article = {
  slug: "enasarco-cos-e-come-funziona",
  title: "ENASARCO: cos'è e come funziona per l'agente di commercio",
  description:
    "Guida pratica a ENASARCO per l'agente di commercio plurimandatario: chi deve iscriversi, come funzionano i contributi, cos'è il FIRR e le scadenze di versamento.",
  publishedAt: "2026-07-31",
  draft: false,
  blocks: [
    {
      type: "p",
      text: "Chi lavora come agente o rappresentante di commercio ha, tra i tanti adempimenti da conoscere, un ente previdenziale specifico a cui fare riferimento: ENASARCO. Capire come funziona è importante non solo per essere in regola, ma anche per verificare che i mandanti versino correttamente quanto dovuto.",
    },
    { type: "h2", text: "Cos'è ENASARCO" },
    {
      type: "p",
      text: "ENASARCO (Ente Nazionale Assistenza Agenti e Rappresentanti di Commercio) è la fondazione che gestisce la previdenza complementare e alcune forme di assistenza per gli agenti e rappresentanti di commercio in Italia. Non sostituisce l'INPS — a cui un agente resta comunque iscritto come lavoratore autonomo — ma si affianca ad esso con contributi e tutele pensate specificamente per questa categoria.",
    },
    { type: "h2", text: "Chi deve iscriversi" },
    {
      type: "p",
      text: "L'iscrizione a ENASARCO è obbligatoria per chiunque operi in base a un contratto di agenzia, sia come persona fisica sia come società. L'obbligo riguarda sia l'agente sia ciascun mandante con cui collabora: per un agente plurimandatario, questo significa avere una posizione contributiva alimentata da più case mandanti contemporaneamente, una per ciascun rapporto di agenzia in corso.",
    },
    { type: "h2", text: "Come funzionano i contributi" },
    {
      type: "p",
      text: "Il contributo previdenziale ENASARCO si calcola in percentuale sulle provvigioni maturate ed è ripartito tra mandante e agente, con quote diverse a carico dell'uno e dell'altro. È il mandante a versarlo trimestralmente all'ente, trattenendo la quota a carico dell'agente direttamente dalle provvigioni liquidate.",
    },
    {
      type: "ul",
      items: [
        "Il contributo si calcola entro un tetto massimo annuo (il cosiddetto massimale provvigionale), oltre il quale non è più dovuto",
        "Le aliquote e i massimali vengono aggiornati periodicamente da ENASARCO: vale sempre la pena verificare i valori in vigore sul sito ufficiale o con il proprio commercialista",
        "Con più mandanti, ogni rapporto ha una propria base di calcolo separata",
      ],
    },
    { type: "h2", text: "Il FIRR: l'indennità di fine rapporto" },
    {
      type: "p",
      text: "Oltre alla previdenza, ENASARCO gestisce il FIRR (Fondo Indennità Risoluzione Rapporto): un accantonamento, versato dal mandante, che si trasforma in un'indennità corrisposta all'agente quando il rapporto di agenzia termina — concettualmente simile al TFR di un lavoratore dipendente, ma calcolato con regole proprie legate alle provvigioni maturate nel corso del rapporto.",
    },
    { type: "h2", text: "Le scadenze di versamento" },
    {
      type: "p",
      text: "I versamenti ENASARCO seguono una cadenza trimestrale, con termini fissati dall'ente per ciascun trimestre solare. Un ritardo nei versamenti da parte del mandante può incidere sulla posizione previdenziale dell'agente, motivo in più per tenere sotto controllo — trimestre dopo trimestre — che i versamenti dei propri mandanti risultino regolari.",
    },
    {
      type: "p",
      text: "Tenere traccia dei contributi ENASARCO versati, insieme alle altre spese personali e aziendali (INPS, assicurazione auto, commercialista), aiuta ad avere un quadro chiaro della propria posizione contributiva nel tempo — è uno degli usi più comuni che gli agenti fanno della sezione Spese di SalesFly, con la categoria ENASARCO già pronta all'uso. Per un agente plurimandatario, indicare il mandante di riferimento nella descrizione o nelle note della spesa aiuta a distinguere i versamenti di ciascuno.",
    },
  ],
};

// CommonJS apposta: leggibile sia da webpack/Babel che da Node in
// scripts/prerender.js senza transpilazione — vedi il commento in
// calcolo-provvigioni-agente-di-commercio.js per il perché.
module.exports = { article };

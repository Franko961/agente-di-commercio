const article = {
  slug: "software-calcolo-percorso-ottimizzato-agenti",
  title: "Percorso ottimizzato per agenti di commercio: come funziona l'algoritmo",
  description:
    "Cosa succede davvero dietro al pulsante \"ottimizza il percorso\": perché il percorso perfetto è impossibile da calcolare in tempo utile, e come un'euristica arriva comunque vicinissima al risultato migliore.",
  publishedAt: "2026-09-02",
  draft: false,
  blocks: [
    {
      type: "p",
      text: "Quando un software propone l'ordine di visita \"ottimizzato\" per una lista di clienti, cosa sta calcolando davvero, e quanto ci si può fidare? Non è un dettaglio da addetti ai lavori: capire come funziona l'algoritmo aiuta a capire perché il risultato è affidabile anche senza essere, in senso stretto, il percorso matematicamente perfetto. Di come pianificare in pratica il giro visite — punto di partenza, orari stimati, indirizzi sospetti — parliamo nell'articolo dedicato qui sotto; qui ci concentriamo su un solo punto: cosa succede dietro al pulsante \"ottimizza\".",
    },
    { type: "h2", text: "Perché il percorso \"perfetto\" è impossibile da calcolare" },
    {
      type: "p",
      text: "Trovare l'ordine di visita più breve tra un insieme di punti è un problema noto in informatica come il problema del commesso viaggiatore, ed è uno dei casi più citati di problema NP-difficile: il numero di percorsi possibili cresce fattorialmente col numero di tappe. Con 5 clienti ci sono 12 percorsi diversi da confrontare — gestibile. Con 15 clienti diventano oltre 43 miliardi. Con 20, si superano i 60 milioni di miliardi. Nessun computer, per quanto potente, può provarli tutti uno per uno in un tempo ragionevole: serve un metodo diverso da \"controlla ogni possibilità\".",
    },
    { type: "h2", text: "L'euristica: non il percorso perfetto, ma vicinissimo" },
    {
      type: "p",
      text: "La soluzione pratica, usata da qualunque software serio di questo tipo (non solo per il giro visite — lo stesso principio sta dietro alla logistica di consegne, ai droni, ai robot che ottimizzano un magazzino), è rinunciare alla perfezione matematica in cambio di un risultato quasi ottimale calcolato in millisecondi. In SalesFly il calcolo avviene in due passaggi distinti.",
    },
    {
      type: "ul",
      items: [
        "Nearest-neighbor: partendo dal punto di partenza, sceglie ogni volta il cliente più vicino a quello appena inserito. Veloce, ma miope: può lasciare un cliente isolato che va recuperato con una deviazione lunga alla fine, semplicemente perché era il più vicino al momento sbagliato.",
        "2-opt: un secondo passaggio che scandaglia il percorso trovato e prova a scambiare coppie di tappe, tenendo lo scambio solo se accorcia il tragitto totale. Ripete finché nessuno scambio migliora più nulla. È questa fase che elimina gli incroci e le \"andata e ritorno\" che il primo passaggio lascia indietro.",
      ],
    },
    {
      type: "p",
      text: "Per il numero di visite reale di una giornata di un agente — tipicamente sotto le 20-30 tappe — questa combinazione converge in un tempo trascurabile e produce risultati che gli studi sul problema del commesso viaggiatore collocano in genere entro pochi punti percentuali dall'ottimo teorico. Non è una promessa di perfezione: è una scelta di ingegneria deliberata, che privilegia un risultato quasi ottimale istantaneo rispetto a un calcolo esatto che, oltre poche decine di tappe, richiederebbe più tempo dell'età dell'universo.",
    },
    { type: "h2", text: "Cosa \"ottimizza\", esattamente" },
    {
      type: "p",
      text: "L'algoritmo minimizza la somma delle distanze tra le tappe nell'ordine scelto — ma quella somma è significativa solo se le distanze di partenza sono realistiche. Ottimizzare un percorso calcolato su distanze in linea d'aria può produrre un ordine di visita che sembra efficiente sulla carta e che nella realtà, tra sensi unici e strade da aggirare, non lo è affatto. Per questo l'algoritmo lavora, quando possibile, su distanze e tempi reali di percorrenza stradale — non è un dettaglio secondario, è la differenza tra un'ottimizzazione che vale qualcosa e una che è solo geometria.",
    },
    {
      type: "cta",
      title: "L'ordine di visita, calcolato per te",
      text: "Nearest-neighbor più 2-opt su distanze reali su strada — non un risultato indovinato a occhio.",
      href: "/richiedi-demo",
      cta: "Inizia prova gratuita",
    },
  ],
};

export { article };

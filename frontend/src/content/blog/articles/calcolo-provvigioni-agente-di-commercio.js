// Bozza di esempio per validare la struttura della sezione blog.
// draft: true => pagina raggiungibile via URL diretto ma con <meta name="robots" content="noindex">
// e nascosta dalla lista su /blog. Passa a draft: false quando il testo è
// stato rivisto ed è pronto per essere indicizzato — sitemap.xml e le
// pagine prerenderizzate si aggiornano da sole al build successivo
// (scripts/prerender.js), non serve più toccarli a mano.
const article = {
  slug: "come-calcolare-provvigioni-agente-di-commercio",
  title: "Come si calcolano le provvigioni di un agente di commercio",
  description:
    "Guida pratica al calcolo delle provvigioni per un agente di commercio plurimandatario: provvigione maturata e liquidata, scala provvigionale, note di credito.",
  publishedAt: "2026-07-21",
  draft: false,
  blocks: [
    {
      type: "p",
      text: "Chi lavora come agente di commercio plurimandatario ha spesso a che fare con più mandanti, ognuno con le proprie regole di calcolo delle provvigioni. Capire bene come funziona questo meccanismo è fondamentale non solo per prevedere il proprio guadagno, ma anche per verificare che gli estratti conto ricevuti dalle case mandanti siano corretti.",
    },
    { type: "h2", text: "Provvigione maturata e provvigione liquidata" },
    {
      type: "p",
      text: "La provvigione matura nel momento in cui l'affare viene concluso grazie all'attività dell'agente, ma diventa esigibile — cioè effettivamente dovuta e pagabile — solo quando il preponente ha eseguito o avrebbe dovuto eseguire la prestazione secondo l'accordo con il cliente. Questa distinzione è al centro di molte contestazioni tra agenti e mandanti, soprattutto quando un ordine viene evaso solo in parte.",
    },
    { type: "h2", text: "Come si calcola l'importo" },
    {
      type: "p",
      text: "Nella maggior parte dei casi la provvigione è una percentuale fissa applicata al valore netto della vendita, al netto di IVA, sconti e resi. La percentuale viene stabilita nel contratto di agenzia o nell'accordo economico collettivo di riferimento, e può variare da mandante a mandante o persino da linea di prodotto a linea di prodotto presso lo stesso mandante.",
    },
    {
      type: "ul",
      items: [
        "Percentuale fissa sul fatturato netto generato",
        "Percentuale variabile per fasce di prodotto o cliente",
        "Scala provvigionale a soglie, con percentuali crescenti al superamento di determinati obiettivi",
      ],
    },
    { type: "h2", text: "La scala provvigionale (o \"scala premi\")" },
    {
      type: "p",
      text: "Molti mandanti applicano una scala premi: superata una certa soglia di fatturato in un periodo di riferimento, la percentuale di provvigione aumenta — a volte solo sulla parte eccedente la soglia, altre volte retroattivamente sull'intero importo. È una delle clausole contrattuali che vale la pena leggere con più attenzione, perché cambia sensibilmente il conto a fine anno.",
    },
    { type: "h2", text: "Note di credito e storni" },
    {
      type: "p",
      text: "Se un cliente restituisce la merce o l'ordine viene stornato, la provvigione già maturata su quella vendita viene normalmente recuperata dal mandante tramite una nota di credito che riduce le provvigioni del periodo successivo. Tenere traccia di questi storni separatamente dalle nuove vendite è essenziale per capire il proprio andamento reale, invece di vedere solo il saldo netto in busta.",
    },
    {
      type: "cta",
      title: "Provvigioni calcolate automaticamente",
      text: "Aliquota per mandante, scaglioni e storni tracciati da soli — mai più ricalcoli a mano.",
      href: "/richiedi-demo",
      cta: "Inizia prova gratuita",
    },
  ],
};

// export ESM standard (non più CommonJS dopo la migrazione a Vite, che
// richiede moduli ESM nativi nel browser): letto sia da webpack/Vite
// (import { article } from "./articles/...") sia da scripts/prerender.js
// (import() dinamico, non require() — vedi il commento lì). Prima
// prerender.js leggeva questo file con delle regex invece che con un
// import reale, fragile verso template literal, stringhe multilinea,
// apostrofi al posto delle virgolette doppie o valori non letterali.
export { article };

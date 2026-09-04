// Sistema di categorizzazione degli articoli del blog — copertina (Unsplash),
// categoria puntuale ed etichetta "macro" (cluster tematico grossolano).
// Estratto da BlogIndex.jsx (che lo usava solo per le copertine e il filtro)
// perché ora serve anche a BlogPost.jsx, per collegare ogni articolo ad
// altri dello stesso cluster invece che semplicemente ai più recenti in
// assoluto — un'unica fonte evita che le due pagine finiscano con logiche
// di categorizzazione divergenti nel tempo.
//
// Categoria a tema per slug, in ordine dal più specifico al più generico — i
// sotto-temi ENASARCO (rimborso tasse, bonus scolastico) vanno controllati
// prima del fallback generico "enasarco". IMPORTANTE: ogni nuovo articolo
// aggiunto al blog va accoppiato a una regola qui — senza, ricade sul tema
// generico DEFAULT_THEME, e più articoli scoperti in questo modo finiscono
// per avere la stessa identica copertina (è esattamente il problema che ha
// motivato questa lista) ed essere raggruppati nello stesso cluster anche
// se non c'entrano nulla tra loro.
export const THEME_RULES = [
  [(s) => s.includes("rimborso-tasse") || s.includes("universita"), "STUDIO", "1541339907198-e08756dedf3f", "Fisco"],
  [(s) => s.includes("bonus-scolastico"), "FAMIGLIA", "1603367563698-67012943fd67", "Fisco"],
  [(s) => s.includes("ritenuta-acconto"), "RITENUTA", "1554224154-26032ffc0d07", "Fisco"],
  [(s) => s.includes("firr"), "INDENNITÀ", "1707157284454-553ef0a4ed0d", "Fisco"],
  [(s) => s.includes("deducibilita-fiscale-auto"), "AUTO", "1616805111996-e39d9a19e35c", "Fisco"],
  [(s) => s.includes("verifica-partita-iva-vies"), "FISCO UE", "1608817576136-0f3a56922823", "Fisco"],
  [(s) => s.includes("scadenze-fiscali"), "SCADENZE", "1611988615248-5d4f0b9ac31e", "Fisco"],
  [(s) => s.includes("ferie-malattia"), "TUTELE", "1599634764228-10b0ee8cafae", "Fisco"],
  // Va prima della regola generica "enasarco" qui sotto, altrimenti le due
  // finiscono con la stessa foto (è successo, vedi il commento sopra).
  [(s) => s.includes("minimali-massimali"), "MASSIMALI", "1633158829585-23ba8f7c8caf", "Fisco"],
  // Va prima della regola generica "enasarco" qui sotto, stesso motivo di
  // "minimali-massimali": lo slug contiene "enasarco" come sottostringa.
  [(s) => s.includes("iscrizione-enasarco"), "ISCRIZIONE", "1554252116-ed7971ea7623", "Fisco"],
  [(s) => s.includes("pensione-enasarco"), "PENSIONE", "1522016480855-67a9f8416d98", "Fisco"],
  [(s) => s.includes("enasarco"), "ENASARCO", "1637763723578-79a4ca9225f7", "Fisco"],
  [(s) => s.includes("spese"), "SPESE", "1649209979970-f01d950cc5ed", "Fisco"],
  [(s) => s.includes("annunci-agenti"), "ANNUNCI", "1504711434969-e33886168f5c", "Guide"],
  [(s) => s.includes("organizzare-settimana"), "AGENDA", "1531346852511-e39bf96dc721", "Vendita"],
  [(s) => s.includes("diventare-agente-di-commercio-requisiti"), "REQUISITI", "1562564055-71e051d33c19", "Guide"],
  [(s) => s.includes("differenza-agente-commercio-agente-sportivo"), "PROFESSIONI", "1533073526757-2c8ca1df9f1c", "Guide"],
  [(s) => s.includes("contratto"), "CONTRATTI", "1450101499163-c8848c66ca85", "Guide"],
  [(s) => s.includes("excel"), "MIGRAZIONE", "1487017159836-4e23ece2e4cf", "Guide"],
  [(s) => s.includes("due-minuti"), "SETUP", "1449247709967-d4461a6a6103", "Guide"],
  [(s) => s.includes("storno-provvigioni"), "PROVVIGIONI", "1638262052640-82e94d64664a", "Vendita"],
  [(s) => s.includes("catalogo-digitale"), "CATALOGO", "1700165644892-3dd6b67b25bc", "Vendita"],
  [(s) => s.includes("percorso-ottimizzato"), "PERCORSO", "1461183479101-6c14cd5299c4", "Vendita"],
  // "come-calcolare-provvigioni" va prima: senza questa regola dedicata
  // non veniva intercettato da nessun'altra ("calcolo-provvigioni" ≠
  // "calcolare-provvigioni") e ricadeva sul tema generico.
  [(s) => s.includes("come-calcolare-provvigioni"), "PROVVIGIONI", "1580048915913-4f8f5cb481c4", "Vendita"],
  [(s) => s.includes("aumentare-provvigioni") || s.includes("calcolo-provvigioni"), "PROVVIGIONI", "1560221328-12fe60f83ab8", "Vendita"],
  [(s) => s.includes("giro-visite"), "TERRITORIO", "1684836571999-f3dc511935e7", "Vendita"],
  [(s) => s.includes("mandanti"), "MANDANTI", "1672380135241-c024f7fbfa13", "Vendita"],
  [(s) => s.includes("crm-italiano"), "CRM ITALIANO", "1536140012599-830a641c27e6", "Tecnologia"],
  [(s) => s.includes("hubspot"), "CONFRONTO", "1616279468745-de6fdbad0262", "Tecnologia"],
  [(s) => s.includes("migliori-crm"), "CONFRONTO", "1539992190939-08f22d7ebaad", "Tecnologia"],
  // "come-ai-e-crm" va prima della regola generica "ai-crm" qui sotto:
  // "ai-e-crm" non contiene "ai-crm" come sottostringa esatta.
  [(s) => s.includes("come-ai-e-crm"), "AI", "1600087626120-062700394a01", "Tecnologia"],
  [(s) => s.includes("intelligenza-artificiale") || s.includes("ai-crm"), "AI", "1674027444485-cec3da58eef4", "Tecnologia"],
  [(s) => s.includes("telefono"), "MOBILE", "1511707171634-5f897ff02aa9", "Tecnologia"],
  [(s) => s.includes("mobile"), "MOBILE", "1592890288564-76628a30a657", "Tecnologia"],
];
export const DEFAULT_THEME = { category: "GUIDA", photoId: "1612367980327-7454a7276aa7", macro: "Guide" };

// Filtro in testa alla pagina blog: 4 macro-categorie editoriali più
// "Tutti", deliberatamente poche (non una per ogni THEME_RULES) — sono
// anche il livello usato per collegare articoli tra loro in "Leggi anche"
// (vedi BlogPost.jsx): abbastanza grossolano da avere quasi sempre almeno
// 2 articoli per cluster, abbastanza specifico da essere un collegamento
// tematico reale (es. non manda un lettore di un articolo ENASARCO a uno
// sul confronto tra CRM).
export const MACROS = ["Tutti", "Vendita", "Fisco", "Tecnologia", "Guide"];

export function themeForSlug(slug) {
  const match = THEME_RULES.find(([test]) => test(slug));
  return match ? { category: match[1], photoId: match[2], macro: match[3] } : DEFAULT_THEME;
}

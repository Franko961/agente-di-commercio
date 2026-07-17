/**
 * Ripulisce un testo (che può contenere Markdown) prima di darlo in pasto alla
 * sintesi vocale (SpeechSynthesis), così non vengono letti simboli come "#", "*",
 * "`" ecc. (es. "cancelletto cancelletto" per le intestazioni "## Titolo").
 *
 * A differenza di una semplice rimozione dei caratteri non-ASCII, questa funzione
 * preserva le lettere accentate italiane (à, è, é, ì, ò, ù) per una pronuncia corretta.
 */
export function cleanForSpeech(text) {
  if (!text) return "";
  return text
    // blocchi di codice ```...```
    .replace(/```[\s\S]*?```/g, " ")
    // intestazioni markdown: "## Titolo" -> "Titolo"
    .replace(/^#{1,6}\s+/gm, "")
    // grassetto/corsivo/barrato: **, *, __, _, ~~
    .replace(/(\*\*\*|\*\*|\*|___|__|_|~~)/g, "")
    // codice inline `testo` -> testo
    .replace(/`([^`]+)`/g, "$1")
    // link markdown [testo](url) -> testo
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    // elenchi puntati/numerati a inizio riga
    .replace(/^\s*[-*+]\s+/gm, "")
    .replace(/^\s*\d+\.\s+/gm, "")
    // linee orizzontali ---
    .replace(/^-{3,}\s*$/gm, "")
    // emoji e simboli pittografici comuni (mantiene lettere accentate italiane)
    .replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{2190}-\u{21FF}\u2705\u274C\u26A0\uFE0F]/gu, "")
    // newline multipli -> pausa parlata
    .replace(/\n+/g, ". ")
    .replace(/\s{2,}/g, " ")
    .trim();
}

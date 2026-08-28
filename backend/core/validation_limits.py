# Limiti applicativi superiori per campi che altrimenti non ne avrebbero
# uno: nessuno di questi è una regola di business vera e propria, sono
# guardrail generosi contro dati palesemente errati (es. una quantità o un
# prezzo con uno zero di troppo digitato per sbaglio), payload
# sproporzionati e i relativi costi (storage, banda, e per i campi
# testuali passati all'assistente AI, token/costo della chiamata).
# Centralizzati qui invece che duplicati in ogni modello, per poterli
# aggiustare in un punto solo se si rivelano troppo stretti/larghi in uso
# reale.

# --- Testo ---
SHORT_TEXT_MAX_LENGTH = 200  # nomi, titoli, città, SKU, P.IVA, telefono, ecc.
MEDIUM_TEXT_MAX_LENGTH = 500  # indirizzi, URL
LONG_TEXT_MAX_LENGTH = (
    5000  # note, descrizioni, messaggi, messaggio contatti, prompt AI
)
PHOTO_MAX_LENGTH = 700_000  # foto profilo come data URL base64 (~500KB binari): va ridimensionata/compressa lato client prima dell'upload

# --- Numeri ---
MAX_QUANTITY = 1_000_000  # quantità di una riga offerta/ordine
MAX_UNIT_PRICE = (
    10_000_000  # prezzo/costo unitario (riga offerta/ordine o a listino prodotto)
)
MAX_EXPENSE_AMOUNT = 1_000_000  # importo di una singola spesa
MAX_MONETARY_TARGET = (
    100_000_000  # obiettivi di fatturato/provvigioni, valore stimato di un lead
)
MAX_COUNT = 100_000  # conteggi (nuovi clienti/visite obiettivo, ecc.)
MAX_VISIT_MINUTES = 480  # durata assunta di una singola visita (8 ore)

# --- Liste ---
MAX_LINE_ITEMS = 500  # righe di una singola offerta/ordine
MAX_TAGS = 30  # tag su un documento
MAX_MANDANTI_PER_CLIENT = 500  # mandanti collegabili a un singolo cliente
MAX_BULK_IMPORT_ITEMS = (
    2000  # righe in un import CSV/Excel in blocco (clienti o prodotti)
)

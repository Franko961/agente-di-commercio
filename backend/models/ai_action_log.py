# Stati possibili di una voce del registro azioni AI (audit log).
#
# - "eseguita": tool che scrive subito (add_client, add_appointment, add_lead,
#   add_note_to_client) ed è stato eseguito senza bisogno di conferma.
# - "in_attesa": tool economico (add_offer, o add_expense sopra soglia) proposto
#   dall'AI e mostrato come scheda di conferma, non ancora scritto sul DB.
# - "in_esecuzione": stato transitorio, impostato atomicamente subito prima di
#   eseguire davvero l'azione confermata. Serve solo a impedire che due
#   richieste concorrenti sullo stesso log_id (doppio clic, retry di rete)
#   possano eseguire l'azione due volte; non dovrebbe mai essere visibile per
#   più di una frazione di secondo, salvo un crash del server a metà.
# - "confermata": l'utente ha confermato (eventualmente modificando) l'azione
#   "in_attesa" e il record è stato scritto davvero.
# - "annullata": l'utente ha annullato l'azione "in_attesa" dalla scheda di
#   conferma, nessun record è stato scritto.
# - "fallita": tentativo di esecuzione (diretta o dopo conferma) terminato con
#   un errore di validazione o di sistema.
AI_ACTION_STATUSES = ["eseguita", "in_attesa", "in_esecuzione", "confermata", "annullata", "fallita"]

# Etichette leggibili dei tool, usate lato backend solo se serve normalizzare;
# il frontend ha la propria mappa per la visualizzazione.
AI_ACTION_TOOL_NAMES = [
    "add_client",
    "add_appointment",
    "add_lead",
    "add_note_to_client",
    "add_offer",
    "add_expense",
]

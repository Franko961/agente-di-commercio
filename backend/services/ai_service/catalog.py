import re
from datetime import datetime
from typing import Optional

from models.expense import EXPENSE_CATEGORIES
from models.vehicle import VEHICLE_TYPES
from models.order import ORDER_STATUSES, PAYMENT_STATUSES

# Tool che generano un record economico (offerte/vendite, spese sopra una certa
# soglia): non vengono MAI eseguiti direttamente dall'AI, nemmeno se il modello
# li invoca con sicurezza. Vengono solo "preparati" (nomi risolti, importo
# calcolato) e mostrati come scheda di conferma; l'esecuzione reale avviene solo
# dopo un'azione esplicita dell'utente su /api/ai/execute-action. Questo protegge
# soprattutto dal canale vocale, dove una trascrizione imprecisa di un importo
# (es. "1.500" sentito come "15.000") non deve poter creare un record economico
# senza che l'utente lo riveda.
EXPENSE_CONFIRM_THRESHOLD = 100.0

# Se un'azione resta in 'in_esecuzione' più a lungo di così, il server è
# quasi certamente crashato (o è stato riavviato) esattamente tra la
# transizione atomica e il salvataggio del risultato: la marchiamo 'fallita'
# invece di lasciarla bloccata per sempre. 5 minuti è ampiamente sufficiente
# per un'esecuzione normale (scrittura DB + calcolo commissione), che dura
# tipicamente pochi millisecondi.
STUCK_EXECUTION_THRESHOLD_SECONDS = 5 * 60

# Tool che scrivono dati sul CRM (a differenza della ricerca web o della
# semplice lettura del contesto). L'account demo condiviso può usare la chat
# per farsi consigliare, ma non deve poter creare/modificare nulla di reale:
# add_offer e add_expense sopra soglia sono già protetti perché passano dalla
# scheda di conferma su /api/ai/execute-action (che usa forbid_demo_write);
# gli altri tool venivano invece eseguiti subito dentro il ciclo della chat,
# senza alcun controllo demo.
CRM_WRITE_TOOLS = {
    "add_client",
    "add_appointment",
    "add_lead",
    "add_note_to_client",
    "add_offer",
    "add_expense",
    "add_employee",
    "add_vehicle",
    "add_order",
    "add_commission",
}

# A quale modulo (vedi core.security.MODULE_KEYS) appartiene ciascun tool:
# un modulo disattivato per l'utente deve bloccare anche l'omologa azione
# via assistente AI/vocale, non solo il form web — altrimenti disattivare
# "Provvigioni" lascerebbe comunque possibile generarne una parlando con
# l'assistente (add_offer con accepted=true crea anche la provvigione).
TOOL_MODULE = {
    "add_client": "clienti",
    "add_note_to_client": "clienti",
    "search_clients": "clienti",
    "add_appointment": "agenda",
    "add_lead": "lead",
    "add_offer": "offerte",
    "search_offers": "offerte",
    "add_expense": "spese",
    "add_employee": "personale",
    "add_vehicle": "flotta",
    "add_order": "ordini",
    "add_commission": "provvigioni",
}


def _safe_float(value, default: float = 0.0) -> float:
    """Converte in float in modo sicuro un valore che può arrivare dall'AI
    (quindi potenzialmente testuale, mancante o malformato: es. un numero
    scritto in lettere, una stringa vuota, None) o da una modifica manuale
    nella scheda di conferma. Normalizza anche i formati numerici italiani
    più comuni prima di convertire: simbolo di valuta e spazi ('€ 120'),
    virgola come separatore decimale ('45,90'), punto come separatore delle
    migliaia insieme alla virgola decimale ('1.500,50'). Non solleva mai
    eccezioni: in caso di valore non convertibile restituisce il default
    invece di far fallire il salvataggio o la formattazione a valle.

    Nota: un valore con SOLO il punto e senza virgola (es. '1.500') viene
    interpretato come notazione anglosassone (1.5), non come separatore delle
    migliaia italiano (1500): senza un secondo segnale (la virgola decimale)
    non c'è modo di distinguere i due casi in modo affidabile."""
    if value is None or value == "":
        return default
    if isinstance(value, str):
        value = value.strip().replace("€", "").replace(" ", "")
        if "," in value:
            value = value.replace(".", "").replace(",", ".")
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _validate_expense_date(value: str) -> Optional[str]:
    """Valida la data di una spesa, che può arrivare dall'AI (quindi
    potenzialmente in linguaggio naturale: 'domani', '21 luglio') o da un
    resolved_input modificato dal browser prima di /execute-action. Accetta
    solo il formato AAAA-MM-DD (quello usato dall'input <input type="date">
    della scheda di conferma) e rifiuta anche date sintatticamente simili ma
    calendaristicamente inesistenti (es. '2026-15-80'), che strptime già
    intercetta.

    Va chiamata solo quando `value` non è vuoto: la gestione del default
    (data odierna, quando l'AI non specifica una data) resta al chiamante,
    così il valore restituito da questa funzione ha un solo significato:
    None = valore presente ma non è una data valida."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except (TypeError, ValueError):
        return None


def _validate_commission_period(value: str) -> Optional[str]:
    """Valida il periodo (mese di competenza) di una provvigione manuale,
    stesso formato AAAA-MM richiesto da ManualCommissionIn.period. Va
    chiamata solo quando `value` non è vuoto, stesso principio di
    _validate_expense_date."""
    if value and re.match(r"^\d{4}-(0[1-9]|1[0-2])$", value):
        return value
    return None


# Definizione tools CRM per l'AI
CRM_TOOLS = [
    {
        "name": "add_client",
        "description": "Aggiunge un nuovo cliente al CRM. Usare quando l'utente chiede di aggiungere/creare un cliente.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {"type": "string", "description": "Nome azienda o cliente"},
                "contact_name": {"type": "string", "description": "Nome del referente"},
                "email": {"type": "string", "description": "Email"},
                "phone": {"type": "string", "description": "Telefono"},
                "vat_number": {"type": "string", "description": "Partita IVA"},
                "address": {"type": "string", "description": "Indirizzo (via e numero civico)"},
                "city": {"type": "string", "description": "Città"},
                "province": {"type": "string", "description": "Provincia (sigla, es. BO, MI)"},
                "zone": {"type": "string", "description": "Zona o regione commerciale"},
                "sector": {"type": "string", "description": "Settore merceologico"},
                "potential": {"type": "string", "description": "Potenziale commerciale: basso, medio o alto", "enum": ["basso", "medio", "alto"]},
                "lat": {"type": "number", "description": "Latitudine della sede, se nota (es. da un indirizzo geocodificato)"},
                "lng": {"type": "number", "description": "Longitudine della sede, se nota"},
                "notes": {"type": "string", "description": "Note aggiuntive"},
            },
            "required": ["company_name"]
        }
    },
    {
        "name": "add_appointment",
        "description": "Aggiunge un nuovo appuntamento in agenda. Usare quando l'utente chiede di aggiungere/fissare un appuntamento o una visita.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Titolo appuntamento"},
                "start": {"type": "string", "description": "Data e ora ISO8601, es: 2026-05-15T10:00:00"},
                "client_name": {"type": "string", "description": "Nome cliente (per trovarlo nel CRM)"},
                "location": {"type": "string", "description": "Luogo"},
                "description": {"type": "string", "description": "Note"},
            },
            "required": ["title", "start"]
        }
    },
    {
        "name": "add_lead",
        "description": "Aggiunge un nuovo lead/prospect alla pipeline. Usare quando l'utente chiede di aggiungere un lead o un prospect.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {"type": "string", "description": "Nome azienda"},
                "contact_name": {"type": "string", "description": "Nome referente"},
                "email": {"type": "string", "description": "Email"},
                "phone": {"type": "string", "description": "Telefono"},
                "value": {"type": "number", "description": "Valore stimato opportunità"},
                "notes": {"type": "string", "description": "Note"},
            },
            "required": ["company_name"]
        }
    },
    {
        "name": "add_note_to_client",
        "description": "Aggiunge una nota a un cliente esistente.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "description": "Nome del cliente"},
                "note": {"type": "string", "description": "Testo della nota da aggiungere"},
            },
            "required": ["client_name", "note"]
        }
    },
    {
        "name": "add_offer",
        "description": "Registra una vendita/offerta per un cliente e un mandante. Usare quando l'utente chiede di registrare una vendita o un'offerta, anche se non ancora conclusa (una bozza/preventivo). Se l'utente dice che la vendita è già conclusa/confermata, imposta accepted a true: in quel caso viene generata automaticamente anche la provvigione, secondo l'aliquota del mandante (che può differire tra vendite nuove e rinnovi). Se l'utente parla esplicitamente di un 'ordine' già ricevuto/confermato (non di una vendita/offerta), usa invece add_order.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "description": "Nome del cliente (per trovarlo nel CRM)"},
                "mandante_name": {"type": "string", "description": "Nome del mandante (per trovarlo nel CRM)"},
                "title": {"type": "string", "description": "Titolo/oggetto della vendita, es: 'Fornitura materiali maggio'"},
                "product_names": {"type": "array", "items": {"type": "string"}, "description": "Nomi dei prodotti venduti, se noti"},
                "quantities": {"type": "array", "items": {"type": "number"}, "description": "Quantità per ciascun prodotto, stesso ordine di product_names"},
                "unit_prices": {"type": "array", "items": {"type": "number"}, "description": "Prezzo unitario per ciascun prodotto; se omesso viene usato il prezzo di listino del prodotto"},
                "total_amount": {"type": "number", "description": "Importo totale della vendita, da usare solo se non si conoscono i singoli prodotti/prezzi"},
                "accepted": {"type": "boolean", "description": "True se la vendita è già confermata/conclusa (genera anche la provvigione), false se è solo un preventivo/bozza"},
                "sale_type": {"type": "string", "enum": ["nuovo", "rinnovo"], "description": "Tipo di vendita: 'nuovo' per un nuovo cliente/contratto, 'rinnovo' per il rinnovo di uno esistente. Determina quale aliquota di provvigione del mandante viene applicata. Default 'nuovo' se non specificato."},
            },
            "required": ["client_name", "mandante_name"]
        }
    },
    {
        "name": "add_order",
        "description": "Registra un ordine per un cliente e un mandante. A differenza di add_offer, un ordine è già un fatto compiuto (non una bozza/proposta): usalo quando l'utente dice che ha ricevuto, fatto o chiuso un ordine, non per una vendita ancora da confermare (in quel caso usa add_offer). La provvigione viene generata automaticamente alla creazione, secondo l'aliquota del mandante (che può differire tra vendite nuove e rinnovi), a meno che lo stato dell'ordine sia 'annullato' o 'reso'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "description": "Nome del cliente (per trovarlo nel CRM)"},
                "mandante_name": {"type": "string", "description": "Nome del mandante (per trovarlo nel CRM)"},
                "product_names": {"type": "array", "items": {"type": "string"}, "description": "Nomi dei prodotti ordinati, se noti"},
                "quantities": {"type": "array", "items": {"type": "number"}, "description": "Quantità per ciascun prodotto, stesso ordine di product_names"},
                "unit_prices": {"type": "array", "items": {"type": "number"}, "description": "Prezzo unitario per ciascun prodotto; se omesso viene usato il prezzo di listino del prodotto"},
                "total_amount": {"type": "number", "description": "Importo totale dell'ordine, da usare solo se non si conoscono i singoli prodotti/prezzi"},
                "sale_type": {"type": "string", "enum": ["nuovo", "rinnovo"], "description": "Tipo di vendita: 'nuovo' per un nuovo cliente/contratto, 'rinnovo' per il rinnovo di uno esistente. Determina quale aliquota di provvigione del mandante viene applicata. Default 'nuovo' se non specificato."},
                "status": {"type": "string", "enum": ORDER_STATUSES, "description": "Stato dell'ordine. Default 'confermato' se non specificato."},
                "payment_status": {"type": "string", "enum": PAYMENT_STATUSES, "description": "Stato del pagamento. Default 'non_pagato' se non specificato."},
                "notes": {"type": "string", "description": "Note aggiuntive"},
            },
            "required": ["client_name", "mandante_name"]
        }
    },
    {
        "name": "add_expense",
        "description": "Registra una spesa personale/aziendale dell'agente (carburante, vitto, alloggio, INPS, ENASARCO, assicurazione auto, commercialista, ecc.). Usare quando l'utente chiede di registrare/aggiungere/segnare una spesa. Non impatta provvigioni o fatturato: è solo tracciamento.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Data della spesa in formato ISO YYYY-MM-DD. Se non specificata, usa la data odierna."},
                "category": {"type": "string", "enum": EXPENSE_CATEGORIES, "description": "Categoria della spesa."},
                "description": {"type": "string", "description": "Breve descrizione della spesa"},
                "amount": {"type": "number", "description": "Importo in euro"},
                "client_name": {"type": "string", "description": "Cliente collegato alla spesa, se presente (es. una spesa sostenuta durante una visita)"},
                "notes": {"type": "string", "description": "Note aggiuntive"},
            },
            "required": ["category", "amount"]
        }
    },
    {
        "name": "add_commission",
        "description": "Registra una provvigione manuale, per un accordo concluso fuori dal normale flusso ordini del CRM (es. un premio, una rettifica, un bonus concordato a parte). Non usare per una vendita/ordine normale: in quei casi la provvigione va generata automaticamente tramite add_offer (accettata) o add_order, non inserita qui a mano.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "description": "Mese di competenza in formato AAAA-MM (es. 2026-08). Se non specificato, usa il mese corrente."},
                "amount": {"type": "number", "description": "Importo della provvigione in euro"},
                "mandante_name": {"type": "string", "description": "Nome del mandante collegato, se presente (per trovarlo nel CRM)"},
                "client_name": {"type": "string", "description": "Nome del cliente collegato, se presente (per trovarlo nel CRM)"},
                "descrizione": {"type": "string", "description": "Breve descrizione della provvigione"},
                "stato": {"type": "string", "enum": ["maturato", "incassato"], "description": "Stato della provvigione. Default 'maturato' se non specificato."},
                "tipo": {"type": "string", "enum": ["ordinaria", "bonus", "rettifica"], "description": "Tipo di provvigione. Default 'ordinaria' se non specificato."},
                "note": {"type": "string", "description": "Note aggiuntive"},
            },
            "required": ["amount"]
        }
    },
    {
        "name": "add_employee",
        "description": "Aggiunge un nuovo dipendente al modulo Personale (nome, cognome, ruolo, contatti). Usare quando l'utente chiede di aggiungere/registrare un dipendente o collaboratore. Genera anche il link personale per le richieste di assenza, mostrato solo nella scheda del dipendente in SalesFly (mai qui in chat, per sicurezza — è un token da mostrare una sola volta).",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Nome del dipendente"},
                "surname": {"type": "string", "description": "Cognome del dipendente, se fornito"},
                "role": {"type": "string", "description": "Ruolo o mansione, es. Autista, Magazziniere, Impiegata"},
                "email": {"type": "string", "description": "Email di contatto, se fornita"},
                "phone": {"type": "string", "description": "Telefono di contatto, se fornito"},
            },
            "required": ["name"]
        }
    },
    {
        "name": "add_vehicle",
        "description": "Aggiunge un nuovo mezzo al modulo Flotta (targa, modello, tipo). Usare quando l'utente chiede di aggiungere/registrare un furgone, camion o auto aziendale.",
        "input_schema": {
            "type": "object",
            "properties": {
                "plate": {"type": "string", "description": "Targa del mezzo"},
                "model": {"type": "string", "description": "Modello, es. Fiat Ducato"},
                "type": {"type": "string", "enum": list(VEHICLE_TYPES), "description": "Tipo di mezzo. Default 'furgone' se non specificato."},
            },
            "required": ["plate"]
        }
    },
    {
        "name": "search_clients",
        "description": (
            "Cerca/filtra i clienti nel CRM con criteri precisi. USA SEMPRE questo tool, invece di "
            "rispondere a memoria dai DATI ATTUALI nel contesto, quando l'utente chiede di elencare, "
            "contare o filtrare clienti in base a: da quanto tempo non fanno un ordine (es. 'clienti che "
            "non acquistano da tre mesi'), in quale mese sono stati visitati (es. 'clienti visitati a "
            "maggio'), zona o potenziale commerciale — i DATI ATTUALI mostrano solo un riassunto parziale "
            "(i primi 20 clienti) e NON bastano per rispondere con precisione a query di questo tipo. "
            "Non scrive nulla sul CRM: è di sola lettura."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "min_days_since_last_order": {
                    "type": "number",
                    "description": "Filtra i clienti il cui ultimo ordine risale ad almeno N giorni fa, o che non hanno mai ordinato. Es. 90 per 'non acquistano da tre mesi'.",
                },
                "visited_month": {
                    "type": "string",
                    "description": "Filtra i clienti con almeno un appuntamento nel mese indicato, formato AAAA-MM (es. 2026-05 per 'maggio' dell'anno corrente).",
                },
                "zone": {"type": "string", "description": "Filtra per zona/area geografica."},
                "potential": {"type": "string", "enum": ["basso", "medio", "alto"], "description": "Filtra per potenziale commerciale."},
            },
            "required": []
        }
    },
    {
        "name": "search_offers",
        "description": (
            "Cerca/filtra le offerte/vendite nel CRM con criteri precisi. USA SEMPRE questo tool, invece "
            "di rispondere a memoria dai DATI ATTUALI nel contesto, quando l'utente chiede di elencare, "
            "contare o filtrare offerte per importo minimo/massimo o stato (es. 'offerte sopra 5000 euro') "
            "— i DATI ATTUALI mostrano solo le ultime 10 offerte e NON bastano per rispondere con "
            "precisione a query di questo tipo. Non scrive nulla sul CRM: è di sola lettura."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "min_amount": {"type": "number", "description": "Importo minimo in euro (es. 5000 per 'sopra 5000 euro')."},
                "max_amount": {"type": "number", "description": "Importo massimo in euro."},
                "status": {"type": "string", "enum": ["bozza", "inviata", "accettata", "rifiutata", "scaduta"], "description": "Filtra per stato dell'offerta."},
            },
            "required": []
        }
    },
]

# Parole chiave per rilevare quale azione CRM l'utente ha richiesto.
# Usate come rete di sicurezza: se il modello non chiama davvero il tool
# corrispondente entro la fine del turno, lo forziamo con tool_choice.
ACTION_INTENT_KEYWORDS = {
    "add_client": ["aggiungi cliente", "aggiungi questo cliente", "crea cliente",
                   "nuovo cliente", "inserisci cliente", "aggiungi al crm"],
    "add_appointment": ["fissa appuntamento", "fissa un appuntamento", "aggiungi appuntamento",
                        "crea appuntamento", "prenota una visita", "segna appuntamento"],
    "add_lead": ["aggiungi lead", "nuovo lead", "crea lead", "aggiungi prospect"],
    "add_note_to_client": ["aggiungi nota", "segna una nota", "aggiungi una nota"],
    "add_offer": ["registra vendita", "registra offerta",
                  "aggiungi offerta", "aggiungi vendita"],
    "add_order": ["registra ordine", "aggiungi ordine", "nuovo ordine",
                  "crea ordine", "inserisci ordine"],
    "add_expense": ["aggiungi spesa", "registra spesa", "segna spesa", "nuova spesa",
                     "inserisci spesa", "ho speso"],
    "add_commission": ["registra provvigione", "aggiungi provvigione", "provvigione manuale",
                        "inserisci provvigione", "nuova provvigione"],
}


def detect_intended_tool(message: str) -> Optional[str]:
    """Ritorna il nome del tool CRM che il messaggio dell'utente sembra richiedere, se c'è."""
    m = (message or "").lower()
    for tool_name, keywords in ACTION_INTENT_KEYWORDS.items():
        if any(kw in m for kw in keywords):
            return tool_name
    return None

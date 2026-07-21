import os
import json
import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from fastapi import HTTPException

from core.utils import gen_id, now_iso
from repositories.ai_repository import ai_repository
from repositories.client_repository import client_repository
from repositories.appointment_repository import appointment_repository
from repositories.lead_repository import lead_repository
from repositories.offer_repository import offer_repository
from repositories.commission_repository import commission_repository
from repositories.mandante_repository import mandante_repository
from repositories.product_repository import product_repository
from repositories.expense_repository import expense_repository
from repositories.ai_action_log_repository import ai_action_log_repository
from models.expense import EXPENSE_CATEGORIES
from services.commission_service import calc_offer_total, get_commission_rate
from services.order_service import order_service
from services.dashboard_service import dashboard_service

logger = logging.getLogger(__name__)

AI_MODEL = "claude-haiku-4-5-20251001"

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
                "city": {"type": "string", "description": "Città"},
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
        "description": "Registra una vendita/offerta per un cliente e un mandante. Usare quando l'utente chiede di registrare una vendita, un ordine o un'offerta. Se l'utente dice che la vendita è già conclusa/confermata, imposta accepted a true: in quel caso viene generata automaticamente anche la provvigione, secondo l'aliquota del mandante (che può differire tra vendite nuove e rinnovi).",
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
    "add_offer": ["registra vendita", "registra offerta", "registra ordine",
                  "aggiungi offerta", "aggiungi vendita"],
    "add_expense": ["aggiungi spesa", "registra spesa", "segna spesa", "nuova spesa",
                     "inserisci spesa", "ho speso"],
}


def detect_intended_tool(message: str) -> Optional[str]:
    """Ritorna il nome del tool CRM che il messaggio dell'utente sembra richiedere, se c'è."""
    m = (message or "").lower()
    for tool_name, keywords in ACTION_INTENT_KEYWORDS.items():
        if any(kw in m for kw in keywords):
            return tool_name
    return None


class AiService:
    def __init__(
        self,
        repo=ai_repository,
        client_repo=client_repository,
        appointment_repo=appointment_repository,
        lead_repo=lead_repository,
        offer_repo=offer_repository,
        commission_repo=commission_repository,
        mandante_repo=mandante_repository,
        product_repo=product_repository,
        expense_repo=expense_repository,
        action_log_repo=ai_action_log_repository,
    ):
        self.repo = repo
        self.client_repo = client_repo
        self.appointment_repo = appointment_repo
        self.lead_repo = lead_repo
        self.offer_repo = offer_repo
        self.commission_repo = commission_repo
        self.mandante_repo = mandante_repo
        self.product_repo = product_repo
        self.expense_repo = expense_repo
        self.action_log_repo = action_log_repo

    async def get_history(self, user_id: str) -> list:
        """Restituisce gli ultimi 30 messaggi della cronologia AI."""
        return await self.repo.find_history(user_id, limit=30)

    async def clear_history(self, user_id: str) -> None:
        """Cancella tutta la cronologia AI dell'utente."""
        await self.repo.delete_all(user_id)

    async def gather_context(self, user_id: str) -> str:
        clients = await self.client_repo.find_many(user_id, {})
        offers = await self.offer_repo.find_many(user_id)
        appts = await self.appointment_repo.find_many(user_id)
        commissions = await self.commission_repo.find_many(user_id)
        expenses = await self.expense_repo.find_many(user_id)

        # Clients with no recent visit
        today = datetime.now(timezone.utc)
        last_visit_map: Dict[str, datetime] = {}
        for a in appts:
            try:
                d = datetime.fromisoformat(a["start"].replace("Z", "+00:00"))
                cid = a.get("client_id")
                if cid and (cid not in last_visit_map or d > last_visit_map[cid]):
                    last_visit_map[cid] = d
            except Exception:
                pass

        summary = []
        summary.append(f"Numero clienti: {len(clients)}, offerte: {len(offers)}, appuntamenti: {len(appts)}")
        summary.append("\nClienti (max 20):")
        for c in clients[:20]:
            last = last_visit_map.get(c["id"])
            days_ago = (today - last).days if last else "mai"
            summary.append(f"- {c['company_name']} ({c.get('zone','')}, potenziale {c.get('potential','medio')}) ultima visita: {days_ago}gg")
        summary.append("\nOfferte recenti:")
        for o in offers[-10:]:
            summary.append(f"- {o.get('title')} importo {o.get('total',0)}€ stato {o.get('status')}")

        current_month = today.strftime("%Y-%m")
        month_expenses = [e for e in expenses if (e.get("date") or "").startswith(current_month)]
        total_month_expenses = sum(e.get("amount", 0) for e in month_expenses)
        summary.append(f"\nSpese del mese corrente: {round(total_month_expenses,2)}€ ({len(month_expenses)} voci)")
        summary.append("Spese recenti (max 10):")
        for e in expenses[-10:]:
            summary.append(f"- {e.get('date')} {e.get('category')} {e.get('amount',0)}€ {e.get('description','')}".strip())

        return "\n".join(summary)

    async def _log_action(
        self, user_id: str, channel: str, raw_input: str, tool_name: str,
        proposed_params: dict, status: str, resolved_params: Optional[dict] = None,
        result: Optional[str] = None,
    ) -> dict:
        """Registra una voce nel registro azioni AI (audit log): chi (user_id),
        con cosa (comando testuale o trascritto dal canale voce/chat), quale
        tool, con quali parametri, ed esito. Non solleva mai: un errore nel
        logging non deve mai far fallire l'azione CRM vera e propria."""
        doc = {
            "id": gen_id(), "user_id": user_id,
            "channel": channel or "chat",
            "raw_input": raw_input or "",
            "tool_name": tool_name,
            "proposed_params": proposed_params or {},
            "resolved_params": resolved_params,
            "final_params": None,
            "status": status,
            "result": result,
            "created_at": now_iso(),
            "confirmed_at": None,
        }
        try:
            return await self.action_log_repo.insert(doc)
        except Exception as e:
            logger.error(f"AI action log insert error: {e}")
            return doc

    async def cancel_pending_action(self, user: dict, log_id: Optional[str]) -> dict:
        """Segna come annullata una voce 'in_attesa' del registro azioni,
        quando l'utente rifiuta la scheda di conferma senza registrare nulla.
        La transizione è atomica e condizionata allo stato attuale: se il log
        non è più 'in_attesa' (perché già confermato, annullato o in corso di
        esecuzione altrove) l'annullamento viene ignorato, così non si rischia
        di sovrascrivere l'esito reale di un'azione già elaborata."""
        if log_id:
            try:
                await self.action_log_repo.transition(
                    log_id, user["id"], "in_attesa",
                    {"status": "annullata", "confirmed_at": now_iso()},
                )
            except Exception as e:
                logger.error(f"AI action log cancel error: {e}")
        return {"ok": True}

    async def list_actions(
        self, user_id: str, tool_name: Optional[str] = None, status: Optional[str] = None,
        date_from: Optional[str] = None, date_to: Optional[str] = None, limit: int = 200,
    ) -> list:
        """Elenco filtrabile del registro azioni AI, per la pagina 'Registro AI'."""
        return await self.action_log_repo.find_many(
            user_id, tool_name=tool_name, status=status,
            date_from=date_from, date_to=date_to, limit=limit,
        )

    async def reclaim_stuck_executions(self) -> int:
        """Segna come 'fallita' le azioni rimaste bloccate in 'in_esecuzione'
        da più di STUCK_EXECUTION_THRESHOLD_SECONDS (vedi
        AiActionLogRepository.reclaim_stale_executions per il motivo:
        tipicamente un crash del server a metà dell'esecuzione confermata).
        Chiamato periodicamente da startup_service, non da una richiesta
        utente. Non riesegue mai l'azione: potrebbe essere già stata scritta
        sul CRM prima del crash."""
        threshold_iso = (
            datetime.now(timezone.utc) - timedelta(seconds=STUCK_EXECUTION_THRESHOLD_SECONDS)
        ).isoformat()
        return await self.action_log_repo.reclaim_stale_executions(
            threshold_iso,
            "Esecuzione interrotta (probabile riavvio del server): verificare "
            "manualmente se l'operazione è stata registrata prima di ripeterla.",
        )

    async def list_pending_actions(self, user_id: str, limit: int = 50) -> list:
        """Azioni economiche (add_offer, add_expense sopra soglia) proposte
        dall'AI e non ancora confermate né annullate, nel formato già atteso
        dal componente AIActionConfirm (tool_name, resolved_input, log_id).

        Serve a recuperare le schede di conferma quando l'utente chiude il
        pannello, ricarica la pagina, cambia schermata o riapre l'app: prima
        di questo endpoint le azioni 'in_attesa' esistevano solo nella
        risposta della singola chiamata a /chat che le aveva create, e
        andavano perse non appena lo stato locale del componente veniva
        azzerato (es. chiudendo il pannello vocale)."""
        logs = await self.action_log_repo.find_many(user_id, status="in_attesa", limit=limit)
        pending = []
        for log in logs:
            resolved = log.get("resolved_params")
            if not resolved:
                # Difesa in profondità: non dovrebbe succedere (un log
                # 'in_attesa' viene sempre creato con resolved_params), ma
                # se capitasse non mostriamo una scheda senza dati.
                continue
            pending.append({
                "log_id": log["id"],
                "tool_name": log["tool_name"],
                "resolved_input": resolved,
                "channel": log.get("channel", "chat"),
                "raw_input": log.get("raw_input", ""),
                "created_at": log.get("created_at"),
            })
        return pending

    async def execute_crm_tool(self, tool_name: str, tool_input: dict, user_id: str) -> str:
        """Esegue un tool CRM e restituisce il risultato come stringa."""
        try:
            if tool_name == "add_client":
                doc = {
                    "id": gen_id(), "user_id": user_id,
                    "company_name": tool_input.get("company_name", ""),
                    "contact_name": tool_input.get("contact_name", ""),
                    "email": tool_input.get("email", ""),
                    "phone": tool_input.get("phone", ""),
                    "city": tool_input.get("city", ""),
                    "address": tool_input.get("address", ""),
                    "province": tool_input.get("province", ""),
                    "zone": tool_input.get("zone", ""),
                    "sector": tool_input.get("sector", ""),
                    "vat_number": tool_input.get("vat_number", ""),
                    "potential": tool_input.get("potential", "medio"),
                    "notes": tool_input.get("notes", ""),
                    "mandante_ids": [],
                    "lat": None, "lng": None,
                    "segment": "prospect", "status": "attivo",
                    "created_at": now_iso(),
                }
                await self.client_repo.insert(doc)
                return f"✅ Cliente '{doc['company_name']}' aggiunto con successo al CRM."

            elif tool_name == "add_appointment":
                client_id = ""
                client_name = tool_input.get("client_name", "")
                if client_name:
                    cli = await self.client_repo.find_by_name_regex(user_id, client_name)
                    if cli:
                        client_id = cli["id"]

                doc = {
                    "id": gen_id(), "user_id": user_id,
                    "title": tool_input.get("title", ""),
                    "start": tool_input.get("start", ""),
                    "client_id": client_id,
                    "location": tool_input.get("location", ""),
                    "description": tool_input.get("description", ""),
                    "status": "pianificato",
                    "created_at": now_iso(),
                }
                await self.appointment_repo.insert(doc)
                return f"✅ Appuntamento '{doc['title']}' fissato per {doc['start'][:10]} alle {doc['start'][11:16]}."

            elif tool_name == "add_lead":
                doc = {
                    "id": gen_id(), "user_id": user_id,
                    "company_name": tool_input.get("company_name", ""),
                    "contact_name": tool_input.get("contact_name", ""),
                    "email": tool_input.get("email", ""),
                    "phone": tool_input.get("phone", ""),
                    "value": tool_input.get("value", 0),
                    "notes": tool_input.get("notes", ""),
                    "stage": "nuovo", "status": "aperto",
                    "created_at": now_iso(),
                }
                await self.lead_repo.insert(doc)
                return f"✅ Lead '{doc['company_name']}' aggiunto alla pipeline."

            elif tool_name == "add_note_to_client":
                client_name = tool_input.get("client_name", "")
                note = tool_input.get("note", "")
                cli = await self.client_repo.find_by_name_regex(user_id, client_name)
                if not cli:
                    return f"❌ Cliente '{client_name}' non trovato nel CRM."
                existing_notes = cli.get("notes", "")
                new_notes = f"{existing_notes}\n[{now_iso()[:10]}] {note}".strip()
                await self.client_repo.update(cli["id"], user_id, {"notes": new_notes})
                return f"✅ Nota aggiunta al cliente '{cli['company_name']}'."

            elif tool_name == "add_offer":
                prepared = await self.prepare_add_offer(tool_input, user_id)
                if "error" in prepared:
                    return f"❌ {prepared['error']}"
                return await self._finalize_offer(user_id, prepared["resolved_input"])

            elif tool_name == "add_expense":
                prepared = await self.prepare_add_expense(tool_input, user_id)
                if "error" in prepared:
                    return f"❌ {prepared['error']}"
                return await self._finalize_expense(user_id, prepared["resolved_input"])

            return f"❌ Tool '{tool_name}' non riconosciuto."
        except Exception as e:
            logger.error(f"CRM tool error: {e}")
            return f"❌ Errore durante l'operazione: {str(e)[:200]}"

    async def prepare_add_offer(self, tool_input: dict, user_id: str) -> dict:
        """Risolve nomi cliente/mandante/prodotti e calcola il totale, SENZA
        scrivere nulla sul DB. Usato per mostrare la scheda di conferma prima
        di registrare una vendita/offerta."""
        client_name = tool_input.get("client_name", "")
        mandante_name = tool_input.get("mandante_name", "")

        cli = await self.client_repo.find_by_name_regex(user_id, client_name)
        if not cli:
            return {"error": f"Cliente '{client_name}' non trovato nel CRM."}

        mand = await self.mandante_repo.find_by_name_regex(user_id, mandante_name)
        if not mand:
            return {"error": f"Mandante '{mandante_name}' non trovato nel CRM."}

        product_names = tool_input.get("product_names") or []
        quantities = tool_input.get("quantities") or []
        unit_prices = tool_input.get("unit_prices") or []

        items = []
        if product_names:
            for i, pname in enumerate(product_names):
                prod = await self.product_repo.find_by_name_regex(user_id, mand["id"], pname)
                qty = _safe_float(quantities[i] if i < len(quantities) else None, 1)
                if qty <= 0:
                    qty = 1
                default_price = prod.get("price", 0) if prod else 0
                price = _safe_float(unit_prices[i] if i < len(unit_prices) else None, default_price)
                if price < 0:
                    price = default_price
                items.append({
                    "product_id": prod["id"] if prod else None,
                    "description": prod["name"] if prod else pname,
                    "quantity": qty, "unit_price": price, "discount": 0,
                })
        else:
            total_amount = _safe_float(tool_input.get("total_amount"), 0)
            items.append({
                "product_id": None,
                "description": tool_input.get("title", "Vendita"),
                "quantity": 1, "unit_price": total_amount, "discount": 0,
            })

        total = calc_offer_total(items)
        if total <= 0:
            return {"error": "L'importo della vendita deve essere maggiore di zero. Specifica un importo o dei prezzi validi."}

        accepted = bool(tool_input.get("accepted", False))
        sale_type = tool_input.get("sale_type", "nuovo")
        if sale_type not in ("nuovo", "rinnovo"):
            sale_type = "nuovo"
        title = tool_input.get("title") or f"Vendita {cli['company_name']}"

        return {
            "tool_name": "add_offer",
            "summary": {
                "client_name": cli["company_name"],
                "mandante_name": mand["name"],
                "title": title,
                "amount": total,
                "status": "accettata" if accepted else "bozza",
                "sale_type": sale_type,
            },
            "resolved_input": {
                "client_id": cli["id"], "client_name": cli["company_name"],
                "mandante_id": mand["id"], "mandante_name": mand["name"],
                "title": title, "items": items, "amount": total,
                "accepted": accepted, "sale_type": sale_type,
            },
        }

    async def _finalize_offer(self, user_id: str, resolved: dict) -> str:
        """Scrive davvero l'offerta/vendita sul DB, a partire da un
        resolved_input già risolto da prepare_add_offer (eventualmente
        modificato dall'utente nella scheda di conferma, es. importo).
        Il payload può arrivare anche direttamente da /api/ai/execute-action,
        quindi va validato di nuovo qui: non ci si può fidare che sia sempre
        passato prima da prepare_add_offer."""
        items = resolved.get("items") or []
        # Difesa in profondità: anche se items arriva già "pulito" da
        # prepare_add_offer, ri-sanitizziamo quantità/prezzi prima di scrivere,
        # nel caso il payload arrivi direttamente dall'endpoint di conferma.
        items = [
            {
                "product_id": it.get("product_id"),
                "description": it.get("description", "Vendita"),
                "quantity": max(_safe_float(it.get("quantity"), 1), 0.01),
                "unit_price": max(_safe_float(it.get("unit_price"), 0), 0),
                "discount": max(_safe_float(it.get("discount"), 0), 0),
            }
            for it in items
        ]
        amount = resolved.get("amount")
        title = resolved.get("title") or "Vendita"
        # Se l'utente ha modificato l'importo in fase di conferma rispetto a
        # quello calcolato dai prodotti, sostituiamo gli item con una riga
        # unica coerente col nuovo importo, invece di lasciare un totale che
        # non corrisponde più alla somma delle righe originali.
        if amount is not None and amount != "":
            amount_f = _safe_float(amount, None)
            if amount_f is not None and (not items or round(calc_offer_total(items), 2) != round(amount_f, 2)):
                items = [{"product_id": None, "description": title, "quantity": 1, "unit_price": amount_f, "discount": 0}]

        total = calc_offer_total(items)
        if total <= 0:
            return "❌ L'importo deve essere maggiore di zero: vendita non registrata."

        accepted = bool(resolved.get("accepted", False))
        status = "accettata" if accepted else "bozza"
        sale_type = resolved.get("sale_type", "nuovo")
        if sale_type not in ("nuovo", "rinnovo"):
            sale_type = "nuovo"

        mand = await self.mandante_repo.find_one(resolved["mandante_id"], user_id)
        if not mand:
            return "❌ Mandante non più trovato nel CRM."

        offer_doc = {
            "id": gen_id(), "user_id": user_id,
            "client_id": resolved["client_id"], "mandante_id": resolved["mandante_id"],
            "title": title, "items": items, "total": total,
            "expires_at": None, "status": status, "sale_type": sale_type, "notes": "",
            "created_at": now_iso(),
        }
        await self.offer_repo.insert(offer_doc)

        msg = f"✅ Vendita registrata: {resolved.get('client_name','')} - {mand['name']} - €{total:.2f} ({sale_type}), stato: {status}."

        if accepted:
            order = await order_service.create_from_offer({"id": user_id}, offer_doc)
            rate = get_commission_rate(mand, sale_type)
            comm_amount = round(order.get("total", 0) * rate / 100, 2)
            msg += f" Ordine registrato e provvigione generata: €{comm_amount:.2f} ({rate}%)."

        return msg

    async def prepare_add_expense(self, tool_input: dict, user_id: str) -> dict:
        """Normalizza i campi di una spesa SENZA scrivere sul DB. Usato per
        mostrare la scheda di conferma quando l'importo è elevato (o sempre,
        se il canale è voce).

        Se è indicato un cliente (es. "spesa di 40 euro con Rossi"), lo
        risolve qui server-side, come già avviene per client_name in
        prepare_add_offer: il browser non riceve mai la possibilità di
        scegliere client_id (non è tra gli ALLOWED_CONFIRM_EDITS), quindi una
        richiesta manomessa non può collegare la spesa a un cliente diverso
        da quello che l'utente ha realmente nominato in questo turno.

        A differenza delle offerte, un cliente non trovato non blocca la
        spesa: il collegamento è opzionale ("solo tracciamento", come da
        descrizione del tool), quindi la spesa viene comunque preparata,
        semplicemente senza client_id, con un avviso nel messaggio finale."""
        category = tool_input.get("category") or "altro"
        if category not in EXPENSE_CATEGORIES:
            category = "altro"
        amount = _safe_float(tool_input.get("amount"), 0)
        if amount <= 0:
            return {"error": "L'importo della spesa deve essere maggiore di zero."}
        raw_date = tool_input.get("date")
        if raw_date:
            date_ = _validate_expense_date(raw_date)
            if date_ is None:
                return {"error": "Data della spesa non valida: usa il formato AAAA-MM-DD."}
        else:
            date_ = now_iso()[:10]
        description = tool_input.get("description", "")
        notes = tool_input.get("notes", "")

        client_id = None
        client_name = None
        client_not_found = None
        requested_client_name = tool_input.get("client_name")
        if requested_client_name:
            cli = await self.client_repo.find_by_name_regex(user_id, requested_client_name)
            if cli:
                client_id = cli["id"]
                client_name = cli["company_name"]
            else:
                client_not_found = requested_client_name

        return {
            "tool_name": "add_expense",
            "summary": {
                "category": category, "amount": amount, "date": date_, "description": description,
                "client_name": client_name,
            },
            "resolved_input": {
                "category": category, "amount": amount, "date": date_, "description": description,
                "notes": notes, "client_id": client_id, "client_name": client_name,
                "client_not_found": client_not_found,
            },
        }

    async def _finalize_expense(self, user_id: str, resolved: dict) -> str:
        """Scrive davvero la spesa sul DB, a partire da un resolved_input già
        preparato da prepare_add_expense (eventualmente modificato
        dall'utente nella scheda di conferma). Il payload può arrivare anche
        direttamente da /api/ai/execute-action, quindi l'importo va validato
        di nuovo qui e non solo in prepare_add_expense."""
        category = resolved.get("category") or "altro"
        if category not in EXPENSE_CATEGORIES:
            category = "altro"
        amount = _safe_float(resolved.get("amount"), 0)
        if amount <= 0:
            return "❌ L'importo deve essere maggiore di zero: spesa non registrata."
        raw_date = resolved.get("date")
        if raw_date:
            date_ = _validate_expense_date(raw_date)
            if date_ is None:
                return "❌ Data della spesa non valida (usa il formato AAAA-MM-DD): spesa non registrata."
        else:
            date_ = now_iso()[:10]
        doc = {
            "id": gen_id(), "user_id": user_id,
            "date": date_,
            "category": category,
            "description": resolved.get("description", ""),
            "amount": amount,
            "client_id": resolved.get("client_id"),
            "notes": resolved.get("notes", ""),
            "receipt_document_id": None,
            "created_at": now_iso(),
        }
        await self.expense_repo.insert(doc)
        msg = f"✅ Spesa registrata: {category} - €{doc['amount']:.2f} ({doc['date']})."
        if resolved.get("client_name"):
            msg += f" Collegata al cliente {resolved['client_name']}."
        elif resolved.get("client_not_found"):
            msg += f" Cliente '{resolved['client_not_found']}' non trovato: spesa registrata senza collegamento."
        return msg

    # Campi che la scheda di conferma (AIActionConfirm.jsx) permette davvero
    # di modificare per ciascun tool economico — riflette esattamente cosa
    # espone l'interfaccia (importo/stato per le offerte; importo/categoria/
    # data/descrizione per le spese). Ogni altro campo del resolved_input
    # inviato dal browser (client_id, mandante_id, items/prodotti, title,
    # ecc.) viene ignorato: execute_confirmed_action lo recupera sempre dal
    # registro azioni (calcolato server-side al momento della proposta),
    # così una richiesta manomessa non può far scrivere un cliente, un
    # mandante o dei prodotti diversi da quelli che l'utente ha realmente
    # visto sulla scheda.
    ALLOWED_CONFIRM_EDITS = {
        "add_offer": {"amount", "accepted", "sale_type"},
        "add_expense": {"amount", "category", "date", "description"},
    }

    def requires_confirmation(self, tool_name: str, tool_input: dict, channel: str = "chat") -> bool:
        """True se il tool genera un record economico e va sempre mostrato
        come scheda di conferma prima di essere eseguito davvero: le vendite/
        offerte sempre, le spese solo sopra EXPENSE_CONFIRM_THRESHOLD (le
        piccole spese di routine, es. un rifornimento, restano immediate) —
        tranne quando il comando arriva dal canale vocale, dove una
        trascrizione imprecisa dell'importo può creare una spesa senza che
        l'utente l'abbia davvero rivista: in quel caso la conferma è sempre
        richiesta, indipendentemente dall'importo."""
        if tool_name == "add_offer":
            return True
        if tool_name == "add_expense":
            amount = _safe_float(tool_input.get("amount"), 0)
            return channel == "voice" or amount >= EXPENSE_CONFIRM_THRESHOLD
        return False

    async def execute_confirmed_action(self, user: dict, payload: dict) -> dict:
        """Esegue un'azione economica (vendita/offerta o spesa) dopo che
        l'utente l'ha confermata (eventualmente modificata) sulla scheda di
        conferma mostrata in chat. Non richiama mai il modello: i dati sono
        già quelli che l'utente ha rivisto e approvato.

        Prima di eseguire, verifica che il log_id esista, appartenga
        all'utente, sia ancora "in_attesa" e corrisponda al tool richiesto;
        poi lo sposta atomicamente a "in_esecuzione" (compare-and-swap sullo
        stato). Solo la richiesta che vince questa transizione procede
        davvero: un doppio clic, un retry di rete o una richiesta duplicata
        con lo stesso log_id ricevono un 409 invece di generare due volte la
        stessa offerta/ordine/provvigione/spesa.

        Il resolved_input inviato dal browser non viene mai usato così com'è:
        il backend parte dal resolved_params salvato nel log (calcolato
        server-side da prepare_add_offer/prepare_add_expense al momento della
        proposta) e vi sovrascrive solo i campi che ALLOWED_CONFIRM_EDITS
        permette di modificare per quel tool. Cliente, mandante e prodotti
        arrivano quindi sempre dal registro, mai dal payload del browser: una
        richiesta manomessa (es. un client_id di un altro utente, o un
        mandante diverso) non può alterare cosa viene effettivamente scritto
        sul CRM."""
        tool_name = payload.get("tool_name")
        browser_input = payload.get("resolved_input") or {}
        log_id = payload.get("log_id")

        if tool_name not in ("add_offer", "add_expense"):
            raise HTTPException(400, "Tipo di azione non valido o non richiede conferma.")
        if not log_id:
            raise HTTPException(400, "Azione non tracciata: log_id mancante.")

        log = await self.action_log_repo.find_one(log_id, user["id"])
        if not log:
            raise HTTPException(404, "Azione non trovata.")
        if log.get("tool_name") != tool_name:
            raise HTTPException(400, "Il tipo di azione non corrisponde al registro.")
        if log.get("status") != "in_attesa":
            raise HTTPException(409, "Azione già elaborata.")

        claimed = await self.action_log_repo.transition(
            log_id, user["id"], "in_attesa",
            {"status": "in_esecuzione", "execution_started_at": now_iso()},
            extra_match={"tool_name": tool_name},
        )
        if not claimed:
            # Un'altra richiesta concorrente ha vinto la transizione tra il
            # find_one sopra e questo punto (finestra di race condition):
            # questa richiesta non esegue nulla.
            raise HTTPException(409, "Azione già elaborata.")

        # Base fidata: i dati che il server aveva già risolto e mostrato
        # nella scheda di conferma. Il payload del browser può modificare
        # solo i campi esplicitamente concessi per questo tool.
        resolved = dict(log.get("resolved_params") or {})
        allowed = self.ALLOWED_CONFIRM_EDITS.get(tool_name, set())
        for key in allowed:
            if key in browser_input:
                resolved[key] = browser_input[key]

        if tool_name == "add_offer" and (not resolved.get("client_id") or not resolved.get("mandante_id")):
            await self.action_log_repo.update_by_id(log_id, user["id"], {
                "status": "fallita",
                "result": "Dati mancanti per registrare la vendita.",
                "confirmed_at": now_iso(),
            })
            raise HTTPException(400, "Dati mancanti per registrare la vendita.")

        if tool_name == "add_offer":
            message = await self._finalize_offer(user["id"], resolved)
        else:
            message = await self._finalize_expense(user["id"], resolved)

        try:
            await self.action_log_repo.update_by_id(log_id, user["id"], {
                "status": "fallita" if message.startswith("❌") else "confermata",
                "final_params": resolved,
                "result": message,
                "confirmed_at": now_iso(),
            })
        except Exception as e:
            logger.error(f"AI action log confirm error: {e}")

        return {"message": message}

    async def chat(self, user: dict, payload) -> dict:
        import anthropic as anthropic_sdk
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise HTTPException(500, "ANTHROPIC_API_KEY mancante")

        context = await self.gather_context(user["id"])
        system = (
            "Sei un assistente commerciale italiano per agenti di commercio. "
            "Aiuti l'agente a decidere quali clienti visitare, analizzare le vendite, "
            "suggerire azioni concrete. Puoi anche modificare il CRM: aggiungere clienti, "
            "appuntamenti, lead, note, vendite/offerte e spese personali/aziendali "
            "(carburante, INPS, ENASARCO, assicurazione auto, commercialista, ecc.). "
            "Quando l'utente ti chiede di fare "
            "un'azione sul CRM, usa i tool disponibili. Se l'utente chiede informazioni "
            "aggiornate o esterne al CRM (es. un'azienda, un prezzo, una notizia recente), "
            "usa la ricerca web. Rispondi sempre in italiano, in modo conciso e pratico, "
            "con elenchi puntati quando possibile. Usa i dati forniti.\n\n"
            "REGOLA IMPORTANTE: non dichiarare MAI un'azione sul CRM come completata "
            "(es. 'cliente aggiunto', 'appuntamento fissato') se non hai realmente invocato "
            "il tool corrispondente in questo turno e ricevuto conferma dal risultato. "
            "Se hai bisogno di informazioni aggiuntive (es. tramite ricerca web) prima di "
            "eseguire un'azione richiesta, esegui prima la ricerca e poi, nella stessa "
            "conversazione, richiama SEMPRE il tool CRM appropriato con i dati raccolti, "
            "prima di confermare il completamento. Se non riesci a completare l'azione, dillo onestamente.\n\n"
            "REGOLA SU VENDITE/OFFERTE E SPESE ELEVATE: i tool add_offer e (per importi "
            "elevati) add_expense NON vengono eseguiti subito quando li chiami: l'operazione "
            "viene solo preparata e mostrata all'utente in una scheda di conferma, per evitare "
            "che un importo frainteso (specialmente da un comando vocale) venga registrato senza "
            "controllo. Dopo aver chiamato uno di questi tool, NON dire che l'operazione è stata "
            "'registrata' o 'creata': di' che è pronta ed è in attesa della conferma dell'utente "
            "nella scheda che vedrà a schermo.\n\n"
            f"DATI ATTUALI:\n{context}"
        )

        history = await self.repo.find_recent_for_context(user["id"], limit=10)

        messages = []
        for h in history:
            messages.append({"role": "user", "content": h["message"]})
            messages.append({"role": "assistant", "content": h["response"]})
        messages.append({"role": "user", "content": payload.message})

        all_tools = CRM_TOOLS + [{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}]
        crm_tool_names = {t["name"] for t in CRM_TOOLS}
        intended_tool = detect_intended_tool(payload.message)
        channel = getattr(payload, "channel", None) or "chat"

        try:
            client_ai = anthropic_sdk.Anthropic(api_key=api_key)
            actions_performed = []
            tools_invoked = set()

            # Primo turno — potrebbe usare tool
            message = client_ai.messages.create(
                model=AI_MODEL,
                max_tokens=1024,
                system=system,
                tools=all_tools,
                messages=messages,
            )

            # Gestisci tool use in loop
            forced_attempt_used = False
            pending_actions = []
            while True:
                if message.stop_reason == "tool_use":
                    tool_results = []
                    for block in message.content:
                        if block.type == "tool_use":
                            tools_invoked.add(block.name)
                            if self.requires_confirmation(block.name, block.input, channel):
                                if block.name == "add_offer":
                                    prepared = await self.prepare_add_offer(block.input, user["id"])
                                else:
                                    prepared = await self.prepare_add_expense(block.input, user["id"])
                                if "error" in prepared:
                                    result = f"❌ {prepared['error']}"
                                    await self._log_action(
                                        user["id"], channel, payload.message, block.name,
                                        block.input, status="fallita", result=prepared["error"],
                                    )
                                else:
                                    log_entry = await self._log_action(
                                        user["id"], channel, payload.message, block.name,
                                        block.input, status="in_attesa",
                                        resolved_params=prepared["resolved_input"],
                                    )
                                    prepared["log_id"] = log_entry.get("id")
                                    pending_actions.append(prepared)
                                    result = "⏳ Operazione preparata, in attesa di conferma dell'utente prima di essere registrata."
                            elif user.get("is_demo") and block.name in CRM_WRITE_TOOLS:
                                result = (
                                    "🔒 Nell'account demo puoi provare l'assistente, "
                                    "ma non modificare i dati."
                                )
                                await self._log_action(
                                    user["id"], channel, payload.message, block.name, block.input,
                                    status="fallita", result=result,
                                )
                            else:
                                result = await self.execute_crm_tool(block.name, block.input, user["id"])
                                actions_performed.append(result)
                                await self._log_action(
                                    user["id"], channel, payload.message, block.name, block.input,
                                    status="fallita" if result.startswith("❌") else "eseguita",
                                    result=result,
                                )
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result,
                            })

                    messages = messages + [
                        {"role": "assistant", "content": message.content},
                        {"role": "user", "content": tool_results},
                    ]
                    message = client_ai.messages.create(
                        model=AI_MODEL,
                        max_tokens=1024,
                        system=system,
                        tools=all_tools,
                        messages=messages,
                    )
                    continue

                # Il modello ha smesso di usare tool. Se l'utente aveva chiesto
                # un'azione CRM specifica e quel tool non è mai stato chiamato
                # davvero (es. il modello ha solo "raccontato" di averlo fatto
                # dopo una ricerca web), lo forziamo una volta sola.
                if (
                    intended_tool
                    and intended_tool in crm_tool_names
                    and intended_tool not in tools_invoked
                    and not forced_attempt_used
                ):
                    forced_attempt_used = True
                    messages = messages + [{"role": "assistant", "content": message.content}]
                    message = client_ai.messages.create(
                        model=AI_MODEL,
                        max_tokens=1024,
                        system=system,
                        tools=all_tools,
                        tool_choice={"type": "tool", "name": intended_tool},
                        messages=messages,
                    )
                    continue

                break

            response = " ".join(
                block.text for block in message.content if hasattr(block, "text")
            )

            # Ultima rete di sicurezza: se nonostante tutto l'azione richiesta
            # non risulta eseguita, non lasciamo passare un testo che sembra
            # una conferma di successo senza che lo sia davvero.
            if intended_tool and intended_tool not in tools_invoked:
                logger.warning(
                    f"AI intent '{intended_tool}' rilevato ma mai eseguito per user {user['id']}"
                )
                if not response.strip():
                    response = (
                        "⚠️ Non sono riuscito a completare l'azione richiesta. "
                        "Puoi riprovare specificando meglio i dati del cliente/appuntamento?"
                    )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"AI error: {e}")
            raise HTTPException(500, f"Errore AI: {str(e)[:200]}")

        log = {"id": gen_id(), "user_id": user["id"], "message": payload.message,
               "response": response, "created_at": now_iso()}
        await self.repo.insert_log(log)
        return {"response": response, "actions": actions_performed, "pending_actions": pending_actions}

    async def get_morning_briefing(self, user: dict) -> dict:
        """Saluto proattivo dell'assistente AI ('Buongiorno Franco. Hai: ...'),
        mostrato all'apertura della pagina Assistente AI invece di aspettare
        passivamente un comando. Puramente calcolato (stessi dati già
        aggregati per la sezione 'Oggi' della dashboard): nessuna chiamata al
        modello, quindi istantaneo e senza costo API."""
        brief = await dashboard_service.get_today_brief(user)
        text = dashboard_service.format_morning_briefing(brief, user.get("name"))
        return {"text": text, "data": brief}

    async def suggestions(self, user: dict) -> dict:
        import anthropic as anthropic_sdk
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return {"suggestions": []}
        context = await self.gather_context(user["id"])
        system = (
            "Sei un consulente vendite italiano. Sulla base dei dati, suggerisci in italiano i 5 clienti "
            "più importanti da visitare questa settimana. Rispondi SOLO in JSON puro senza markdown, "
            "con questa struttura: {\"suggestions\":[{\"client\":\"nome\",\"reason\":\"motivo breve\",\"priority\":\"alta|media|bassa\"}]}"
        )
        try:
            client_ai = anthropic_sdk.Anthropic(api_key=api_key)
            message = client_ai.messages.create(
                model=AI_MODEL,
                max_tokens=1024,
                system=system,
                messages=[{"role": "user", "content": f"DATI:\n{context}\n\nSuggerisci 5 clienti da visitare."}],
            )
            response = message.content[0].text
            m = re.search(r'\{.*\}', response, re.DOTALL)
            if m:
                data = json.loads(m.group(0))
                return data
        except Exception as e:
            logger.error(f"AI suggestions error: {e}")
        return {"suggestions": []}


ai_service = AiService()

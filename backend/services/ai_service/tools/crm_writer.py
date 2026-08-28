import logging

from core.utils import gen_id, local_wallclock_to_utc_iso, now_iso
from models.employee import EmployeeIn
from models.vehicle import VehicleIn
from services.ai_service.tools.search import search_clients, search_offers
from services.employee_service import employee_service
from services.vehicle_service import vehicle_service

logger = logging.getLogger(__name__)


async def _add_client(client_repo, tool_input: dict, user_id: str) -> str:
    doc = {
        "id": gen_id(),
        "user_id": user_id,
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
        "lat": tool_input.get("lat"),
        "lng": tool_input.get("lng"),
        "segment": "prospect",
        "status": "attivo",
        "created_at": now_iso(),
    }
    await client_repo.insert(doc)
    return f"✅ Cliente '{doc['company_name']}' aggiunto con successo al CRM."


async def _add_appointment(
    client_repo, appointment_repo, tool_input: dict, user_id: str
) -> str:
    client_id = ""
    client_name = tool_input.get("client_name", "")
    if client_name:
        cli = await client_repo.find_by_name_regex(user_id, client_name)
        if cli:
            client_id = cli["id"]

    raw_start = tool_input.get("start", "")
    try:
        # Il modello fornisce l'orario "a muro" in ora italiana
        # (naive, senza offset — vedi la descrizione del tool più
        # sopra). Va convertito in un vero istante UTC prima di
        # salvarlo, altrimenti risulterebbe incompatibile con gli
        # appuntamenti creati dal form web (che sono UTC veri).
        start_utc = local_wallclock_to_utc_iso(raw_start) if raw_start else ""
    except (ValueError, TypeError):
        start_utc = raw_start  # meglio salvare così com'è che far fallire il tool

    doc = {
        "id": gen_id(),
        "user_id": user_id,
        "title": tool_input.get("title", ""),
        "start": start_utc,
        "client_id": client_id,
        "location": tool_input.get("location", ""),
        "description": tool_input.get("description", ""),
        "status": "pianificato",
        "created_at": now_iso(),
    }
    await appointment_repo.insert(doc)
    # Il messaggio di conferma mostra l'orario così come richiesto
    # (raw_start, già in ora italiana), non il valore convertito
    # in UTC appena salvato — evita un doppio giro di conversione
    # solo per la visualizzazione.
    return f"✅ Appuntamento '{doc['title']}' fissato per {raw_start[:10]} alle {raw_start[11:16]}."


async def _add_lead(lead_repo, tool_input: dict, user_id: str) -> str:
    doc = {
        "id": gen_id(),
        "user_id": user_id,
        "company_name": tool_input.get("company_name", ""),
        "contact_name": tool_input.get("contact_name", ""),
        "email": tool_input.get("email", ""),
        "phone": tool_input.get("phone", ""),
        "value": tool_input.get("value", 0),
        "notes": tool_input.get("notes", ""),
        "stage": "nuovo",
        "status": "aperto",
        "created_at": now_iso(),
    }
    await lead_repo.insert(doc)
    return f"✅ Lead '{doc['company_name']}' aggiunto alla pipeline."


async def _add_note_to_client(client_repo, tool_input: dict, user_id: str) -> str:
    client_name = tool_input.get("client_name", "")
    note = tool_input.get("note", "")
    cli = await client_repo.find_by_name_regex(user_id, client_name)
    if not cli:
        return f"❌ Cliente '{client_name}' non trovato nel CRM."
    existing_notes = cli.get("notes", "")
    new_notes = f"{existing_notes}\n[{now_iso()[:10]}] {note}".strip()
    await client_repo.update(cli["id"], user_id, {"notes": new_notes})
    return f"✅ Nota aggiunta al cliente '{cli['company_name']}'."


async def _add_employee(tool_input: dict, user_id: str) -> str:
    # Passa dal service (non un insert diretto come add_client)
    # per riusare davvero la generazione del token/link personale
    # (hash SHA-256, mai l'inserimento manuale della stessa
    # logica qui) — vedi employee_service.create_employee.
    payload = EmployeeIn(
        name=tool_input.get("name", ""),
        surname=tool_input.get("surname", ""),
        role=tool_input.get("role", ""),
        email=tool_input.get("email") or None,
        phone=tool_input.get("phone", ""),
    )
    doc = await employee_service.create_employee({"id": user_id}, payload)
    full_name = f"{doc['name']} {doc.get('surname', '')}".strip()
    return f"✅ Dipendente '{full_name}' aggiunto. Il link personale per le richieste di assenza è visibile nella sua scheda in Personale."


async def _add_vehicle(tool_input: dict, user_id: str) -> str:
    payload = VehicleIn(
        plate=tool_input.get("plate", ""),
        model=tool_input.get("model", ""),
        type=tool_input.get("type") or "furgone",
    )
    doc = await vehicle_service.create_vehicle({"id": user_id}, payload)
    return f"✅ Mezzo '{doc['plate']}' aggiunto alla Flotta."


async def execute_crm_tool(
    service, tool_name: str, tool_input: dict, user_id: str
) -> str:
    """Esegue un tool CRM e restituisce il risultato come stringa.

    `service` è l'istanza AiService chiamante: i tool add_offer/add_expense
    passano dal pattern prepara/conferma già esposto dai suoi metodi
    (prepare_add_offer/_finalize_offer, ecc.), mentre i repository per i
    tool più semplici (add_client, add_appointment, ...) sono letti dai
    suoi attributi — evita di dover passare qui dentro una dozzina di
    parametri separati per gli stessi repository già raggruppati lì."""
    try:
        if tool_name == "add_client":
            return await _add_client(service.client_repo, tool_input, user_id)

        elif tool_name == "add_appointment":
            return await _add_appointment(
                service.client_repo, service.appointment_repo, tool_input, user_id
            )

        elif tool_name == "add_lead":
            return await _add_lead(service.lead_repo, tool_input, user_id)

        elif tool_name == "add_note_to_client":
            return await _add_note_to_client(service.client_repo, tool_input, user_id)

        elif tool_name == "add_offer":
            prepared = await service.prepare_add_offer(tool_input, user_id)
            if "error" in prepared:
                return f"❌ {prepared['error']}"
            return await service._finalize_offer(user_id, prepared["resolved_input"])

        elif tool_name == "add_expense":
            prepared = await service.prepare_add_expense(tool_input, user_id)
            if "error" in prepared:
                return f"❌ {prepared['error']}"
            return await service._finalize_expense(user_id, prepared["resolved_input"])

        elif tool_name == "add_employee":
            return await _add_employee(tool_input, user_id)

        elif tool_name == "add_vehicle":
            return await _add_vehicle(tool_input, user_id)

        elif tool_name == "search_clients":
            return await search_clients(
                service.client_repo,
                service.order_repo,
                service.appointment_repo,
                tool_input,
                user_id,
            )

        elif tool_name == "search_offers":
            return await search_offers(service.offer_repo, tool_input, user_id)

        return f"❌ Tool '{tool_name}' non riconosciuto."
    except Exception as e:
        logger.error(f"CRM tool error: {e}")
        return f"❌ Errore durante l'operazione: {str(e)[:200]}"

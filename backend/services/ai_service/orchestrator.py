import os
import time
import logging

from fastapi import HTTPException

from core.utils import gen_id, now_iso
from core.observability import record_event
from core.rate_limit import check_and_record
from core.security import module_enabled
from services.ai_service.pricing import AI_MODEL, _estimate_cost_usd, _usage_tokens
from services.ai_service.catalog import CRM_TOOLS, TOOL_MODULE, CRM_WRITE_TOOLS, detect_intended_tool

logger = logging.getLogger(__name__)


async def chat(service, user: dict, payload) -> dict:
    import anthropic as anthropic_sdk
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(500, "ANTHROPIC_API_KEY mancante")

    # Limite di burst distinto dalla quota mensile per piano qui sotto:
    # anche un utente ben dentro la propria quota potrebbe scriptare
    # richieste ravvicinate, ognuna delle quali chiama davvero l'API
    # Anthropic a pagamento (incluso il tool di ricerca web, fatturato a
    # parte) — stessa protezione già applicata a geocoding/route
    # planning per le altre API esterne a consumo.
    ok = await check_and_record("ai_chat", user["id"], max_attempts=20, window_minutes=10)
    if not ok:
        raise HTTPException(429, "Troppe richieste all'assistente AI in poco tempo, riprova tra qualche minuto")

    await service._enforce_ai_message_quota(user)

    context = await service.gather_context(user["id"])
    system = (
        "Sei un assistente commerciale italiano per agenti di commercio. "
        "Aiuti l'agente a decidere quali clienti visitare, analizzare le vendite, "
        "suggerire azioni concrete. Puoi anche modificare il CRM: aggiungere clienti, "
        "appuntamenti, lead, note, vendite/offerte, ordini, provvigioni manuali e spese "
        "personali/aziendali (carburante, INPS, ENASARCO, assicurazione auto, commercialista, ecc.). "
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
        "REGOLA SU VENDITE/OFFERTE, ORDINI, PROVVIGIONI E SPESE ELEVATE: i tool add_offer, "
        "add_order, add_commission e (per importi elevati) add_expense NON vengono eseguiti "
        "subito quando li chiami: l'operazione viene solo preparata e mostrata all'utente in "
        "una scheda di conferma, per evitare che un importo frainteso (specialmente da un "
        "comando vocale) venga registrato senza controllo. Dopo aver chiamato uno di questi "
        "tool, NON dire che l'operazione è stata 'registrata' o 'creata': di' che è pronta ed "
        "è in attesa della conferma dell'utente nella scheda che vedrà a schermo.\n\n"
        "REGOLA SU RICERCHE E FILTRI: i DATI ATTUALI qui sotto sono un riassunto parziale "
        "(i primi 20 clienti, le ultime 10 offerte): non bastano per rispondere con precisione "
        "quando l'utente chiede di elencare, contare o filtrare clienti o offerte con un criterio "
        "specifico (es. 'clienti che non acquistano da tre mesi', 'offerte sopra 5000 euro', "
        "'clienti visitati a maggio'). In questi casi usa SEMPRE search_clients o search_offers "
        "invece di rispondere a memoria dal riassunto: altrimenti rischi di dare una risposta "
        "incompleta o sbagliata perché basata solo su una parte dei dati.\n\n"
        f"DATI ATTUALI:\n{context}"
    )

    history = await service.repo.find_recent_for_context(user["id"], limit=10)

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
        _ai_start = time.perf_counter()
        client_ai = anthropic_sdk.Anthropic(api_key=api_key)
        actions_performed = []
        tools_invoked = set()
        total_input_tokens = 0
        total_output_tokens = 0
        total_web_searches = 0

        # Primo turno — potrebbe usare tool
        message = client_ai.messages.create(
            model=AI_MODEL,
            max_tokens=1024,
            system=system,
            tools=all_tools,
            messages=messages,
        )
        _in, _out, _ws = _usage_tokens(message)
        total_input_tokens += _in
        total_output_tokens += _out
        total_web_searches += _ws

        # Gestisci tool use in loop
        forced_attempt_used = False
        pending_actions = []
        while True:
            if message.stop_reason == "tool_use":
                tool_results = []
                for block in message.content:
                    if block.type == "tool_use":
                        tools_invoked.add(block.name)
                        required_module = TOOL_MODULE.get(block.name)
                        # module_enabled copre sia i moduli core (opt-out
                        # via disabled_modules, es. "spese") sia i moduli
                        # extra (opt-in via enabled_extra_modules, es.
                        # "personale"/"flotta" — add_employee/add_vehicle):
                        # un controllo che guardasse solo disabled_modules
                        # lascerebbe passare questi ultimi anche per un
                        # account che non li ha mai attivati, dato che non
                        # compaiono affatto in disabled_modules in quel caso.
                        if required_module and not module_enabled(user, required_module):
                            result = f"🔒 Il modulo \"{required_module}\" non è disponibile per questo account."
                            await service._log_action(
                                user["id"], channel, payload.message, block.name, block.input,
                                status="fallita", result=result,
                            )
                        elif service.requires_confirmation(block.name, block.input, channel):
                            if block.name == "add_offer":
                                prepared = await service.prepare_add_offer(block.input, user["id"])
                            elif block.name == "add_order":
                                prepared = await service.prepare_add_order(block.input, user["id"])
                            elif block.name == "add_commission":
                                prepared = await service.prepare_add_commission(block.input, user["id"])
                            else:
                                prepared = await service.prepare_add_expense(block.input, user["id"])
                            if "error" in prepared:
                                result = f"❌ {prepared['error']}"
                                await service._log_action(
                                    user["id"], channel, payload.message, block.name,
                                    block.input, status="fallita", result=prepared["error"],
                                )
                            else:
                                log_entry = await service._log_action(
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
                            await service._log_action(
                                user["id"], channel, payload.message, block.name, block.input,
                                status="fallita", result=result,
                            )
                        else:
                            result = await service.execute_crm_tool(block.name, block.input, user["id"])
                            actions_performed.append(result)
                            await service._log_action(
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
                _in, _out, _ws = _usage_tokens(message)
                total_input_tokens += _in
                total_output_tokens += _out
                total_web_searches += _ws
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
                _in, _out, _ws = _usage_tokens(message)
                total_input_tokens += _in
                total_output_tokens += _out
                total_web_searches += _ws
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
        await record_event(
            "ai_call", "failure", user_id=user["id"], channel=channel,
            duration_ms=round((time.perf_counter() - _ai_start) * 1000, 1),
            error=str(e)[:300],
        )
        raise HTTPException(500, f"Errore AI: {str(e)[:200]}")

    await record_event(
        "ai_call", "success", user_id=user["id"], channel=channel,
        duration_ms=round((time.perf_counter() - _ai_start) * 1000, 1),
        tokens_in=total_input_tokens, tokens_out=total_output_tokens,
        web_searches=total_web_searches,
        cost_usd=_estimate_cost_usd(total_input_tokens, total_output_tokens, total_web_searches),
        tools_invoked=list(tools_invoked),
    )

    log = {"id": gen_id(), "user_id": user["id"], "message": payload.message,
           "response": response, "created_at": now_iso()}
    await service.repo.insert_log(log)
    return {"response": response, "actions": actions_performed, "pending_actions": pending_actions}

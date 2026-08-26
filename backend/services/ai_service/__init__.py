import os
import json
import re
import logging
from typing import Optional

from repositories.ai_repository import ai_repository
from repositories.client_repository import client_repository
from repositories.appointment_repository import appointment_repository
from repositories.lead_repository import lead_repository
from repositories.offer_repository import offer_repository
from repositories.commission_repository import commission_repository
from repositories.manual_commission_repository import manual_commission_repository
from repositories.mandante_repository import mandante_repository
from repositories.product_repository import product_repository
from repositories.expense_repository import expense_repository
from repositories.order_repository import order_repository
from repositories.ai_action_log_repository import ai_action_log_repository
from services.dashboard_service import dashboard_service

logger = logging.getLogger(__name__)

from services.ai_service.pricing import (
    AI_MODEL,
    AI_PRICE_PER_MTOK_INPUT_USD,
    AI_PRICE_PER_MTOK_OUTPUT_USD,
    AI_PRICE_PER_1K_WEB_SEARCHES_USD,
    _estimate_cost_usd,
    _usage_tokens,
)
from services.ai_service.catalog import (
    EXPENSE_CONFIRM_THRESHOLD,
    STUCK_EXECUTION_THRESHOLD_SECONDS,
    CRM_WRITE_TOOLS,
    TOOL_MODULE,
    CRM_TOOLS,
    ACTION_INTENT_KEYWORDS,
    _safe_float,
    _validate_expense_date,
    _validate_commission_period,
    detect_intended_tool,
)
from services.ai_service.context import gather_context as _gather_context
from services.ai_service.quota import enforce_ai_message_quota as _enforce_ai_message_quota
from services.ai_service.action_log import (
    log_action as _log_action,
    cancel_pending_action as _cancel_pending_action,
    list_actions as _list_actions,
    reclaim_stuck_executions as _reclaim_stuck_executions,
    list_pending_actions as _list_pending_actions,
)
from services.ai_service.actions._shared import resolve_line_items as _resolve_line_items
from services.ai_service.actions.offers import prepare_add_offer as _prepare_add_offer, finalize_offer as _finalize_offer
from services.ai_service.actions.orders import prepare_add_order as _prepare_add_order, finalize_add_order as _finalize_add_order
from services.ai_service.actions.expenses import prepare_add_expense as _prepare_add_expense, finalize_expense as _finalize_expense
from services.ai_service.actions.commissions import prepare_add_commission as _prepare_add_commission, finalize_add_commission as _finalize_add_commission
from services.ai_service.tools.crm_writer import execute_crm_tool as _execute_crm_tool
from services.ai_service.tools.search import search_clients as _search_clients, search_offers as _search_offers
from services.ai_service.confirmation import (
    ALLOWED_CONFIRM_EDITS as _ALLOWED_CONFIRM_EDITS,
    requires_confirmation as _requires_confirmation,
    execute_confirmed_action as _execute_confirmed_action,
)
from services.ai_service.orchestrator import chat as _chat


class AiService:
    def __init__(
        self,
        repo=ai_repository,
        client_repo=client_repository,
        appointment_repo=appointment_repository,
        lead_repo=lead_repository,
        offer_repo=offer_repository,
        commission_repo=commission_repository,
        manual_commission_repo=manual_commission_repository,
        mandante_repo=mandante_repository,
        product_repo=product_repository,
        expense_repo=expense_repository,
        action_log_repo=ai_action_log_repository,
        order_repo=order_repository,
    ):
        self.repo = repo
        self.client_repo = client_repo
        self.appointment_repo = appointment_repo
        self.lead_repo = lead_repo
        self.offer_repo = offer_repo
        self.commission_repo = commission_repo
        self.manual_commission_repo = manual_commission_repo
        self.mandante_repo = mandante_repo
        self.product_repo = product_repo
        self.expense_repo = expense_repo
        self.action_log_repo = action_log_repo
        self.order_repo = order_repo

    async def get_history(self, user_id: str) -> list:
        """Restituisce gli ultimi 30 messaggi della cronologia AI."""
        return await self.repo.find_history(user_id, limit=30)

    async def clear_history(self, user_id: str) -> None:
        """Cancella tutta la cronologia AI dell'utente."""
        await self.repo.delete_all(user_id)

    async def gather_context(self, user_id: str) -> str:
        return await _gather_context(
            self.client_repo, self.offer_repo, self.appointment_repo,
            self.commission_repo, self.manual_commission_repo, self.expense_repo, user_id,
        )

    async def _log_action(
        self, user_id: str, channel: str, raw_input: str, tool_name: str,
        proposed_params: dict, status: str, resolved_params: Optional[dict] = None,
        result: Optional[str] = None,
    ) -> dict:
        return await _log_action(
            self.action_log_repo, user_id, channel, raw_input, tool_name,
            proposed_params, status, resolved_params, result,
        )

    async def cancel_pending_action(self, user: dict, log_id: Optional[str]) -> dict:
        return await _cancel_pending_action(self.action_log_repo, user, log_id)

    async def list_actions(
        self, user_id: str, tool_name: Optional[str] = None, status: Optional[str] = None,
        date_from: Optional[str] = None, date_to: Optional[str] = None, limit: int = 200,
    ) -> list:
        return await _list_actions(self.action_log_repo, user_id, tool_name, status, date_from, date_to, limit)

    async def reclaim_stuck_executions(self) -> int:
        return await _reclaim_stuck_executions(self.action_log_repo)

    async def list_pending_actions(self, user_id: str, limit: int = 50) -> list:
        return await _list_pending_actions(self.action_log_repo, user_id, limit)

    async def execute_crm_tool(self, tool_name: str, tool_input: dict, user_id: str) -> str:
        """Esegue un tool CRM e restituisce il risultato come stringa."""
        return await _execute_crm_tool(self, tool_name, tool_input, user_id)

    async def _search_clients(self, tool_input: dict, user_id: str) -> str:
        return await _search_clients(self.client_repo, self.order_repo, self.appointment_repo, tool_input, user_id)

    async def _search_offers(self, tool_input: dict, user_id: str) -> str:
        return await _search_offers(self.offer_repo, tool_input, user_id)


    async def _resolve_line_items(self, tool_input: dict, user_id: str, mandante_id: str, fallback_description: str) -> list:
        return await _resolve_line_items(self.product_repo, tool_input, user_id, mandante_id, fallback_description)

    async def prepare_add_offer(self, tool_input: dict, user_id: str) -> dict:
        return await _prepare_add_offer(self.client_repo, self.mandante_repo, self.product_repo, tool_input, user_id)

    async def _finalize_offer(self, user_id: str, resolved: dict) -> str:
        return await _finalize_offer(self.offer_repo, self.mandante_repo, user_id, resolved)

    async def prepare_add_order(self, tool_input: dict, user_id: str) -> dict:
        return await _prepare_add_order(self.client_repo, self.mandante_repo, self.product_repo, tool_input, user_id)

    async def _finalize_add_order(self, user_id: str, resolved: dict) -> str:
        return await _finalize_add_order(self.mandante_repo, user_id, resolved)

    async def prepare_add_expense(self, tool_input: dict, user_id: str) -> dict:
        return await _prepare_add_expense(self.client_repo, tool_input, user_id)

    async def _finalize_expense(self, user_id: str, resolved: dict) -> str:
        return await _finalize_expense(self.expense_repo, user_id, resolved)

    async def prepare_add_commission(self, tool_input: dict, user_id: str) -> dict:
        return await _prepare_add_commission(self.mandante_repo, self.client_repo, tool_input, user_id)

    async def _finalize_add_commission(self, user_id: str, resolved: dict) -> str:
        return await _finalize_add_commission(user_id, resolved)


    ALLOWED_CONFIRM_EDITS = _ALLOWED_CONFIRM_EDITS

    def requires_confirmation(self, tool_name: str, tool_input: dict, channel: str = "chat") -> bool:
        return _requires_confirmation(tool_name, tool_input, channel)

    async def execute_confirmed_action(self, user: dict, payload: dict) -> dict:
        return await _execute_confirmed_action(self, user, payload)

    async def _enforce_ai_message_quota(self, user: dict) -> None:
        await _enforce_ai_message_quota(self.repo, user)

    async def chat(self, user: dict, payload) -> dict:
        return await _chat(self, user, payload)


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

    async def generate_employee_summary(self, employee: dict, summary: dict) -> dict:
        """Riepilogo in linguaggio naturale di un dipendente per la scheda
        Personale (es. 'Mario ha 3 giorni di malattia questo mese, ferie
        quasi esaurite'): stessa forma minimale di suggestions() (una
        singola chiamata al modello, nessuna cronologia, nessun tool),
        non la conversazione completa di chat(). Nessun dato sanitario nel
        contesto inviato al modello — solo i conteggi già usati altrove
        nella scheda dipendente, mai la diagnosi (che SalesFly non
        memorizza comunque, vedi models/employee.py)."""
        import anthropic as anthropic_sdk
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return {"summary": None}

        name = f"{employee.get('name', '')} {employee.get('surname', '')}".strip()
        ferie = summary["ferie"]
        permessi = summary["permessi"]
        malattie = summary["malattie"]
        kpi = summary["kpi"]
        context = (
            f"Dipendente: {name}\n"
            f"Ruolo: {employee.get('role') or '—'}\n"
            f"Stato contrattuale: {employee.get('employment_status', 'attivo')}\n"
            f"Ferie quest'anno: {ferie['godute']} giorni goduti su {ferie['spettanti']} spettanti "
            f"({ferie['residue']} residui)\n"
            f"Permessi quest'anno: {permessi['ore_approvate']} ore approvate\n"
            f"Malattie quest'anno: {malattie['giorni']} giorni\n"
            f"Presenze stimate quest'anno: {kpi['presenze_stimate']} giorni\n"
        )
        # Tono puramente descrittivo, non valutativo: un testo che sembrasse
        # una valutazione automatizzata del lavoratore (es. segnalare
        # "assenze frequenti" come un problema) è esattamente il tipo di
        # output che un riepilogo HR generato da un modello non dovrebbe
        # produrre, specie con dati vicini alla salute della persona
        # (giorni di malattia) — riassume i valori, non li giudica.
        system = (
            "Sei un assistente HR italiano. In 1-2 frasi brevi riassumi i valori (ferie, permessi, "
            "malattie, presenze) di questo dipendente per il suo responsabile, in modo puramente "
            "descrittivo: riporta i numeri così come sono, senza formulare giudizi sulla persona e "
            "senza suggerire decisioni lavorative. Non inventare dati non forniti, non menzionare "
            "diagnosi o dettagli sanitari. Rispondi in italiano, testo semplice senza markdown."
        )
        try:
            client_ai = anthropic_sdk.Anthropic(api_key=api_key)
            message = client_ai.messages.create(
                model=AI_MODEL,
                max_tokens=200,
                system=system,
                messages=[{"role": "user", "content": context}],
            )
            return {"summary": message.content[0].text.strip()}
        except Exception as e:
            logger.error(f"AI employee summary error: {e}")
        return {"summary": None}


ai_service = AiService()

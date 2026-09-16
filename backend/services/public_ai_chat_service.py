import logging
import os
import time
from typing import Optional, cast

from fastapi import HTTPException

from core.config import PLANS, TRIAL_DAYS
from core.observability import record_event
from core.rate_limit import check_and_record
from core.utils import gen_id, now_iso
from models.public_ai_chat import PublicChatHistoryItem
from repositories.public_ai_chat_log_repository import public_ai_chat_log_repository
from services.ai_service.pricing import AI_MODEL, _estimate_cost_usd, _usage_tokens

logger = logging.getLogger(__name__)

PUBLIC_CHAT_MAX_TOKENS = 400


def _build_system_prompt() -> str:
    # Prezzi e feature lette da PLANS (core/config.py), la stessa fonte che
    # alimenta GET /api/subscription/plans e quindi la pagina /prezzi reale —
    # mai testo scritto a mano qui, altrimenti questa chat rischia di
    # promettere prezzi o funzioni diverse da quelle vere (vedi la lezione
    # sull'errore ENASARCO trovato il 2026-09-16: mai inventare/lasciare
    # disallineare un fatto verificabile).
    base = PLANS["base"]
    pro = PLANS["pro"]
    base_features = "\n".join(f"- {f}" for f in cast(list, base["features"]))
    pro_features = "\n".join(f"- {f}" for f in cast(list, pro["features"]))

    return (
        "Sei l'assistente informativo sul sito pubblico di SALESFLY, un CRM per agenti di "
        "commercio plurimandatari (che lavorano con più mandanti contemporaneamente). "
        "Rispondi in italiano, in modo breve, concreto e onesto, a chi visita il sito e "
        "vuole sapere di più prima di provare il prodotto.\n\n"
        "REGOLA IMPORTANTE — NON INVENTARE NULLA: usa solo le informazioni su prezzi e "
        "funzionalità elencate qui sotto. Se ti chiedono qualcosa che non è in questo "
        "elenco (una funzione, un prezzo, un'integrazione), di' onestamente che non lo sai "
        "o che non è (ancora) disponibile — non inventare mai una risposta plausibile.\n\n"
        "REGOLA IMPORTANTE — NON SEI L'ASSISTENTE DEL CRM: questa chat è solo informativa, "
        "su questo sito pubblico. Non hai accesso a nessun dato reale di nessun cliente e "
        "non puoi eseguire azioni (aggiungere clienti, appuntamenti, ecc.) — quella è una "
        "funzione diversa, disponibile solo dentro l'app dopo essersi registrati. Se ti "
        "chiedono di fare un'azione, spiega questa distinzione invece di fingere di farla.\n\n"
        "Se la domanda non riguarda SALESFLY, riporta gentilmente il discorso in tema. "
        "Quando è naturale (non ad ogni risposta), invita a provare la prova gratuita.\n\n"
        f"PIANI E PREZZI (validi oggi, {TRIAL_DAYS} giorni di prova gratuita su entrambi, "
        "nessuna carta di credito richiesta):\n\n"
        f"Piano {base['name']} — €{base['price_eur']}/mese. {base['tagline']}\n{base_features}\n\n"
        f"Piano {pro['name']} — €{pro['price_eur']}/mese. {pro['tagline']}\n{pro_features}"
    )


async def chat(
    message: str,
    history: Optional[list[PublicChatHistoryItem]],
    ip_address: Optional[str],
) -> str:
    if ip_address:
        ok = await check_and_record(
            "public_ai_chat_ip", ip_address, max_attempts=10, window_minutes=15
        )
        if not ok:
            raise HTTPException(
                429, "Troppe richieste da questo indirizzo, riprova tra qualche minuto."
            )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(500, "Assistente non disponibile al momento.")

    import anthropic as anthropic_sdk

    messages = [{"role": h.role, "content": h.text} for h in (history or [])]
    messages.append({"role": "user", "content": message})

    _start = time.perf_counter()
    try:
        client_ai = anthropic_sdk.Anthropic(api_key=api_key)
        # Nessun tool: questa chat non scrive né legge nulla, solo risposte
        # testuali basate sul system prompt — vedi la nota di design nel
        # piano su perché resta volutamente separata dall'assistente reale
        # (services/ai_service/orchestrator.py).
        response = client_ai.messages.create(
            model=AI_MODEL,
            max_tokens=PUBLIC_CHAT_MAX_TOKENS,
            system=_build_system_prompt(),
            messages=messages,  # type: ignore[arg-type]
        )
        text = " ".join(
            block.text for block in response.content if hasattr(block, "text")
        )
        tokens_in, tokens_out, _ = _usage_tokens(response)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Public AI chat error: {e}")
        await record_event(
            "ai_call",
            "failure",
            channel="public_landing",
            duration_ms=round((time.perf_counter() - _start) * 1000, 1),
            error=str(e)[:300],
        )
        raise HTTPException(500, "Non sono riuscito a rispondere, riprova tra poco.")

    await record_event(
        "ai_call",
        "success",
        channel="public_landing",
        duration_ms=round((time.perf_counter() - _start) * 1000, 1),
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=_estimate_cost_usd(tokens_in, tokens_out),
    )
    await public_ai_chat_log_repository.insert(
        {"id": gen_id(), "domanda": message, "risposta": text, "created_at": now_iso()}
    )
    return text

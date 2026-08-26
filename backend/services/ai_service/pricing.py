AI_MODEL = "claude-haiku-4-5-20251001"

# Prezzi usati solo per stimare il costo nel cruscotto di salute applicativa
# (non per fatturazione reale). VERIFICARE PERIODICAMENTE contro
# https://platform.claude.com/docs/en/about-claude/pricing — questi valori
# non sono letti da nessuna fonte live, vanno aggiornati manualmente.
# Confermati corretti il 26/07/2026 contro la tabella prezzi ufficiale.
AI_PRICE_PER_MTOK_INPUT_USD = 1.00
AI_PRICE_PER_MTOK_OUTPUT_USD = 5.00
# Il tool web_search (usato da questo assistente, vedi all_tools più sotto) è
# fatturato a parte dai token: $10 ogni 1000 ricerche, indipendentemente dal
# numero di risultati restituiti. Andava conteggiato a parte perché non è
# incluso in usage.input_tokens/output_tokens.
AI_PRICE_PER_1K_WEB_SEARCHES_USD = 10.00


def _estimate_cost_usd(input_tokens: int, output_tokens: int, web_searches: int = 0) -> float:
    return round(
        (input_tokens / 1_000_000) * AI_PRICE_PER_MTOK_INPUT_USD
        + (output_tokens / 1_000_000) * AI_PRICE_PER_MTOK_OUTPUT_USD
        + (web_searches / 1_000) * AI_PRICE_PER_1K_WEB_SEARCHES_USD,
        6,
    )


def _usage_tokens(message) -> tuple:
    """Legge input/output token e numero di ricerche web dalla risposta del
    modello in modo difensivo: gli attributi potrebbero mancare (es. in
    ambienti di test con un doppio finto dell'SDK) e questo non deve mai far
    fallire la conversazione — al più sottostima il costo registrato in
    telemetria."""
    usage = getattr(message, "usage", None)
    server_tool_use = getattr(usage, "server_tool_use", None)
    return (
        getattr(usage, "input_tokens", 0) or 0,
        getattr(usage, "output_tokens", 0) or 0,
        getattr(server_tool_use, "web_search_requests", 0) or 0,
    )

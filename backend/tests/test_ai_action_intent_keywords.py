"""
Verifica services.ai_service.catalog.detect_intended_tool per il caso reale
che ha causato un bug il 2026-09-15: Franco ha scritto "...inserisci questi
dati come nuovi lead" (12 lead incollati in chat). Nessuna delle frasi
allora in ACTION_INTENT_KEYWORDS["add_lead"] faceva match ("nuovi lead"
plurale ≠ "nuovo lead", nessuna variante con "inserisci") — la rete di
sicurezza anti-hallucination di orchestrator.chat() non è mai scattata, e
l'AI ha dichiarato un successo mai avvenuto.

Esegui con:
    python -m pytest tests/test_ai_action_intent_keywords.py -v
"""

import sys

sys.path.insert(0, ".")

from services.ai_service.catalog import detect_intended_tool


def test_detect_intended_tool_riconosce_la_frase_reale_del_bug():
    msg = (
        "Rossetti San Salvo 0873 329186 rsa.villarossetti@gruppolavilla.com "
        "Casa Religiosa Antoniano Lanciano 0872 715389 — RSA Santa Maria "
        "Ausiliatrice Montesilvano 085 73446 aga.pe@pec.it. inserisci questi "
        "dati come nuovi lead"
    )
    assert detect_intended_tool(msg) == "add_lead"


def test_detect_intended_tool_varianti_vicine_con_verbo_esplicito():
    for msg in [
        "inserisci lead",
        "inserisci questi lead",
        "inserisci questi dati come lead",
        "carica questi lead",
        "importa questi lead",
        "aggiungi questi lead",
        "aggiungi i lead",
    ]:
        assert detect_intended_tool(msg) == "add_lead", msg


def test_detect_intended_tool_non_scatta_su_una_domanda_generica():
    # Nessun verbo di creazione esplicito: non deve forzare un tool_choice
    # su una domanda di sola lettura, altrimenti si rischia di creare un
    # lead inventato pur di soddisfare la tool_choice forzata.
    assert detect_intended_tool("quanti nuovi lead ho questo mese?") is None
    assert detect_intended_tool("cosa ne pensi di questi lead?") is None

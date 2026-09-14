import asyncio
import os

import requests
from fastapi import HTTPException, UploadFile

from core.rate_limit import check_and_record

WHISPER_URL = "https://api.openai.com/v1/audio/transcriptions"

# Un comando vocale breve (il caso d'uso reale: "aggiungi una nota a...")
# sta ampiamente sotto questa soglia anche senza compressione — un margine
# ampio ma non illimitato, per non tenere in RAM un file enorme prima di
# rifiutarlo. Il tetto vero sui costi/abuso è comunque la quota mensile
# messaggi AI già applicata a /chat (services/ai_service/quota.py), a cui
# ogni messaggio vocale trascritto arriva comunque una volta inviato.
MAX_AUDIO_BYTES = 8 * 1024 * 1024
_AUDIO_CHUNK_SIZE = 1024 * 1024


# async + asyncio.to_thread attorno a `requests` (sincrona): senza, questa
# chiamata bloccherebbe l'intero event loop del worker per la durata della
# richiesta HTTP a OpenAI — stesso principio già applicato a PayPal in
# services/subscription_service.py e a Google Calendar in
# services/google_calendar_service.py.
async def transcribe_audio(audio_bytes: bytes, filename: str) -> str:
    """Trascrive un breve audio vocale in italiano tramite Whisper (OpenAI) —
    usato al posto del riconoscimento vocale nativo del browser
    (window.SpeechRecognition), che Safari/WebKit non implementa affatto
    (nessun browser su iPhone può quindi usarlo). L'audio non viene salvato
    da nessuna parte: passa per questa funzione e viene scartato subito
    dopo, sia in caso di successo sia di errore."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(500, "Trascrizione vocale non disponibile al momento")

    def _fetch():
        return requests.post(
            WHISPER_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": (filename, audio_bytes)},
            data={"model": "whisper-1", "language": "it"},
            timeout=30,
        )

    try:
        resp = await asyncio.to_thread(_fetch)
    except requests.RequestException:
        raise HTTPException(
            502, "Servizio di trascrizione non raggiungibile. Riprova tra poco."
        )

    if resp.status_code != 200:
        raise HTTPException(502, "Non sono riuscito a trascrivere l'audio. Riprova.")

    text = resp.json().get("text", "").strip()
    if not text:
        raise HTTPException(400, "Non ho sentito nulla. Riprova.")
    return text


async def transcribe_upload(file: UploadFile, user_id: str) -> str:
    """Orchestrazione della rotta POST /api/ai/transcribe: rate limit, lettura
    a blocchi con controllo dimensione progressivo (stesso principio di
    services/document_service.py::upload_document — un audio enorme viene
    rifiutato appena supera il limite, non dopo essere stato caricato per
    intero in memoria), poi la trascrizione vera e propria. Router
    deliberatamente sottile: stessa convenzione del resto del progetto
    (i router chiamano un service, la logica vive nel service)."""
    if not await check_and_record(
        "ai_transcribe", user_id, max_attempts=30, window_minutes=10
    ):
        raise HTTPException(429, "Troppe richieste di trascrizione. Riprova tra poco.")

    total = 0
    chunks = []
    while True:
        chunk = await file.read(_AUDIO_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_AUDIO_BYTES:
            raise HTTPException(
                413, f"Audio troppo lungo (max {MAX_AUDIO_BYTES // (1024*1024)} MB)"
            )
        chunks.append(chunk)
    if total == 0:
        raise HTTPException(400, "Audio vuoto")

    return await transcribe_audio(b"".join(chunks), file.filename or "voice.webm")

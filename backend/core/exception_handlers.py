"""Registrazione centralizzata degli exception handler dell'app — estratto
da server.py (che stava diventando il posto dove finiva un po' di tutto)
per tenere in un solo file ogni logica di "come rispondiamo quando qualcosa
va storto", separata dal setup dell'app/middleware/router.

Gli errori di validazione Pydantic restano gestiti da FastAPI stesso
(risposta 422 automatica) — non serve un handler dedicato qui. Un'eccezione
non prevista (es. un errore MongoDB non incapsulato in un AppError) resta
un 500 generico gestito dal default di FastAPI/Starlette, catturato da
Sentry quando SENTRY_DSN è configurato (vedi server.py) — nessuna
duplicazione di quella logica qui."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from core.exceptions import AppError


def register_exception_handlers(app: FastAPI) -> None:
    """Chiamata una volta sola da server.py subito dopo aver creato l'app.

    Il decoratore (invece di app.add_exception_handler diretto) è lo stesso
    stile già usato prima di questo file: mypy tipizza la callback in modo
    più permissivo così, mentre add_exception_handler pretende una firma
    generica su Exception che un handler specifico per AppError non
    soddisfa staticamente (pur essendo corretto a runtime — Starlette
    invoca l'handler solo per le eccezioni del tipo registrato)."""

    @app.exception_handler(AppError)
    async def _handle_app_error(request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

from typing import Literal, Optional

import jwt
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import StreamingResponse

from core.config import JWT_ALG, JWT_SECRET
from core.security import (
    DOCUMENT_DOWNLOAD_TOKEN_TTL_MINUTES,
    create_document_download_token,
    decode_document_download_token,
    forbid_demo_write,
    get_current_user,
    require_module,
)
from models.document import DOCUMENT_CATEGORIES, DocumentIn, DocumentMetaUpdate
from services.document_service import document_service
from services.storage_service import sanitize_filename, storage_get_stream

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Il modulo "documenti" copre solo l'archivio documenti vero e proprio
# (elenco, caricamento, cancellazione). Le rotte di download/signed-url
# più sotto restano SEMPRE raggiungibili: sono quelle usate per aprire lo
# scontrino allegato a una spesa (Spese.jsx) o l'allegato di un'offerta,
# indipendentemente dal fatto che l'archivio documenti standalone sia
# attivo per l'utente — disattivarlo non deve rendere illeggibili
# allegati già collegati altrove.
MODULE_DEP = Depends(require_module("documenti"))


@router.get("", dependencies=[MODULE_DEP])
async def list_documents(user=Depends(get_current_user)):
    return await document_service.list_documents(user)


@router.post("", dependencies=[MODULE_DEP])
async def create_document(payload: DocumentIn, user=Depends(forbid_demo_write)):
    return await document_service.create_document(user, payload)


@router.post("/upload", dependencies=[MODULE_DEP])
async def upload_document(
    file: UploadFile = File(...),
    name: str = Form(...),
    category: Literal[*DOCUMENT_CATEGORIES] = Form("altro"),
    client_id: Optional[str] = Form(None),
    notes: str = Form(""),
    tags: str = Form(""),
    user=Depends(forbid_demo_write),
):
    return await document_service.upload_document(
        user, file, name, category, client_id, notes, tags
    )


@router.patch("/{did}", dependencies=[MODULE_DEP])
async def update_document_meta(
    did: str, payload: DocumentMetaUpdate, user=Depends(forbid_demo_write)
):
    """Update metadata (tags, name, category, notes, client_id) without re-uploading the file."""
    await document_service.update_document_meta(user, did, payload)
    return {"ok": True}


@router.get("/{did}/signed-url")
async def get_signed_download_url(did: str, user=Depends(get_current_user)):
    """Genera un link di download temporaneo e specifico per QUESTO
    documento, da usare per link diretti (es. aprire in una nuova scheda,
    incollare in un'email) al posto di mettere il token di sessione completo
    — valido 7 giorni per l'intero account — in una query string. Il token
    restituito qui scade dopo pochi minuti e non serve a nient'altro che a
    scaricare questo specifico documento."""
    await document_service.get_document_for_download(
        user["id"], did
    )  # verifica esistenza + proprietà
    token = create_document_download_token(user["id"], did)
    return {
        "url": f"/api/documents/{did}/download?token={token}",
        "expires_in_minutes": DOCUMENT_DOWNLOAD_TOKEN_TTL_MINUTES,
    }


@router.get("/{did}/download")
async def download_document(
    did: str,
    request: Request,
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None),
):
    # Due modalità di autenticazione, entrambe legittime per usi diversi:
    # 1) cookie httponly o header Authorization — la sessione normale usata
    #    da fetch(..., {credentials: "include"}), come fa già il frontend
    #    per il download e l'anteprima (nessun token in query string qui).
    # 2) query param 'token' — SOLO il token firmato specifico per questo
    #    documento emesso da /signed-url qui sopra, mai il JWT di sessione
    #    completo: quel token durava 7 giorni e valeva per l'intero account,
    #    esattamente il tipo di segreto che non deve mai finire in un URL
    #    (cronologia browser, log server/reverse proxy, analytics, ecc.).
    user_id = None
    session_token = request.cookies.get("access_token")
    if not session_token and authorization and authorization.startswith("Bearer "):
        session_token = authorization[7:]

    if session_token:
        try:
            payload = jwt.decode(session_token, JWT_SECRET, algorithms=[JWT_ALG])
            user_id = payload["sub"]
        except jwt.InvalidTokenError:
            raise HTTPException(401, "Invalid token")
    elif token:
        try:
            user_id = decode_document_download_token(token, did)
        except jwt.InvalidTokenError:
            raise HTTPException(401, "Link di download non valido o scaduto")
    else:
        raise HTTPException(401, "Not authenticated")

    doc = await document_service.get_document_for_download(user_id, did)
    # Streaming dal bucket S3 al browser: il contenuto non viene mai tenuto
    # per intero in memoria sul server, nemmeno per un video o un documento
    # pesante (vedi storage_get_stream in storage_service.py).
    chunk_iterator, ctype, content_length = storage_get_stream(doc["storage_path"])
    # sanitize_filename applicato anche qui (non solo all'upload): protegge
    # anche i documenti già caricati prima di questa modifica, il cui
    # original_filename in DB potrebbe non essere ancora stato ripulito.
    filename = sanitize_filename(
        doc.get("original_filename") or doc.get("name") or "file"
    )
    # inline solo per i tipi "sicuri" da mostrare direttamente nel browser
    # (PDF e immagini): tutti gli altri (Office, video, testo, ecc.) vengono
    # forzati come attachment, così il browser li scarica invece di provare
    # a renderizzarli — riduce la superficie d'attacco anche se Content-Type
    # è già vincolato alla whitelist e servito con nosniff.
    disposition = (
        "inline"
        if (ctype == "application/pdf" or ctype.startswith("image/"))
        else "attachment"
    )
    headers = {
        "Content-Disposition": f'{disposition}; filename="{filename}"',
        "Cache-Control": "private, max-age=300",
        # Impedisce al browser di "indovinare" un tipo diverso da quello
        # dichiarato in Content-Type ispezionando i byte del corpo —
        # difesa aggiuntiva anche ora che Content-Type è sempre quello
        # della nostra whitelist (mai preso dal browser in upload),
        # non più solo un dato fidato per assunzione.
        "X-Content-Type-Options": "nosniff",
    }
    if content_length is not None:
        headers["Content-Length"] = str(content_length)
    return StreamingResponse(
        chunk_iterator,
        media_type=doc.get("content_type") or ctype,
        headers=headers,
    )


@router.delete("/{did}", dependencies=[MODULE_DEP])
async def delete_document(did: str, user=Depends(forbid_demo_write)):
    await document_service.delete_document(user, did)
    return {"ok": True}

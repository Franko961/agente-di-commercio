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
from models.employee_document import (
    EMPLOYEE_DOCUMENT_CATEGORIES,
    EmployeeDocumentMetaUpdate,
)
from services.employee_document_service import employee_document_service
from services.storage_service import sanitize_filename, storage_get_stream

# Gated da "personale" (non da "documenti", a differenza del modulo
# Documenti aziendale): un account con Personale attivo ma Documenti
# disattivo deve poter comunque caricare i documenti di un dipendente, e
# viceversa — sono moduli extra indipendenti, vedi core/security.py.
router = APIRouter(prefix="/api/employees/{eid}/documents", tags=["employee-documents"])
MODULE_DEP = Depends(require_module("personale"))


@router.get("", dependencies=[MODULE_DEP])
async def list_employee_documents(eid: str, user=Depends(get_current_user)):
    return await employee_document_service.list_documents(user, eid)


@router.post("/upload", dependencies=[MODULE_DEP])
async def upload_employee_document(
    eid: str,
    file: UploadFile = File(...),
    name: str = Form(""),
    category: Literal[*EMPLOYEE_DOCUMENT_CATEGORIES] = Form("altro"),
    notes: str = Form(""),
    user=Depends(forbid_demo_write),
):
    return await employee_document_service.upload_document(
        user, eid, file, name, category, notes
    )


@router.patch("/{did}", dependencies=[MODULE_DEP])
async def update_employee_document_meta(
    eid: str,
    did: str,
    payload: EmployeeDocumentMetaUpdate,
    user=Depends(forbid_demo_write),
):
    await employee_document_service.update_meta(user, eid, did, payload)
    return {"ok": True}


@router.get("/{did}/signed-url", dependencies=[MODULE_DEP])
async def get_employee_document_signed_url(
    eid: str, did: str, user=Depends(get_current_user)
):
    await employee_document_service.get_document_for_download(user["id"], eid, did)
    token = create_document_download_token(user["id"], did)
    return {
        "url": f"/api/employees/{eid}/documents/{did}/download?token={token}",
        "expires_in_minutes": DOCUMENT_DOWNLOAD_TOKEN_TTL_MINUTES,
    }


@router.get("/{did}/download")
async def download_employee_document(
    eid: str,
    did: str,
    request: Request,
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None),
):
    # Stesse due modalità di autenticazione di routers/documents.py: sessione
    # normale (cookie/Bearer) oppure token firmato specifico per questo
    # documento — vedi lì il commento esteso sul perché.
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

    doc = await employee_document_service.get_document_for_download(user_id, eid, did)
    chunk_iterator, ctype, content_length = storage_get_stream(doc["storage_path"])
    filename = sanitize_filename(
        doc.get("original_filename") or doc.get("name") or "file"
    )
    disposition = (
        "inline"
        if (ctype == "application/pdf" or ctype.startswith("image/"))
        else "attachment"
    )
    headers = {
        "Content-Disposition": f'{disposition}; filename="{filename}"',
        "Cache-Control": "private, max-age=300",
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
async def delete_employee_document(eid: str, did: str, user=Depends(forbid_demo_write)):
    await employee_document_service.delete_document(user, eid, did)
    return {"ok": True}

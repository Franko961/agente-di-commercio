import jwt
from typing import Optional
from fastapi import APIRouter, Depends, Body, UploadFile, File, Form, Header, Query, HTTPException, Response
from core.security import get_current_user
from core.config import JWT_SECRET, JWT_ALG
from services.document_service import document_service
from services.storage_service import storage_get
from models.document import DocumentIn

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("")
async def list_documents(user=Depends(get_current_user)):
    return await document_service.list_documents(user)


@router.post("")
async def create_document(payload: DocumentIn, user=Depends(get_current_user)):
    return await document_service.create_document(user, payload)


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    name: str = Form(...),
    category: str = Form("altro"),
    client_id: Optional[str] = Form(None),
    notes: str = Form(""),
    tags: str = Form(""),
    user=Depends(get_current_user),
):
    return await document_service.upload_document(user, file, name, category, client_id, notes, tags)


@router.patch("/{did}")
async def update_document_meta(did: str, payload: dict = Body(...), user=Depends(get_current_user)):
    """Update metadata (tags, name, category, notes, client_id) without re-uploading the file."""
    await document_service.update_document_meta(user, did, payload)
    return {"ok": True}


@router.get("/{did}/download")
async def download_document(did: str, authorization: Optional[str] = Header(None), auth: Optional[str] = Query(None)):
    # Allow auth via Authorization header OR ?auth=token query param (for direct browser links)
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    elif auth:
        token = auth
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

    doc = await document_service.get_document_for_download(payload["sub"], did)
    content, ctype = storage_get(doc["storage_path"])
    filename = doc.get("original_filename") or doc.get("name") or "file"
    return Response(
        content=content,
        media_type=doc.get("content_type") or ctype,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "private, max-age=300",
        },
    )


@router.delete("/{did}")
async def delete_document(did: str, user=Depends(get_current_user)):
    await document_service.delete_document(user, did)
    return {"ok": True}

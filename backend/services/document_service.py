from fastapi import HTTPException
from typing import Optional
from core.utils import gen_id, now_iso
from repositories.document_repository import document_repository
from services.storage_service import storage_put, ALLOWED_EXT, APP_NAME
from core.config import MAX_FILE_BYTES


class DocumentService:
    def __init__(self, repo=document_repository):
        self.repo = repo

    async def list_documents(self, user: dict) -> list:
        return await self.repo.find_many(user["id"])

    async def create_document(self, user: dict, payload) -> dict:
        doc = {
            "id": gen_id(), "user_id": user["id"], **payload.model_dump(),
            "is_deleted": False, "created_at": now_iso(),
        }
        return await self.repo.insert(doc)

    async def upload_document(self, user: dict, file, name: str, category: str,
                               client_id: Optional[str], notes: str, tags: str) -> dict:
        if not file.filename:
            raise HTTPException(400, "File mancante")
        ext = (file.filename.rsplit(".", 1)[-1] if "." in file.filename else "bin").lower()
        if ext not in ALLOWED_EXT:
            raise HTTPException(400, f"Estensione .{ext} non supportata. Consentite: PDF, Excel, Word, video, immagini.")
        data = await file.read()
        if len(data) > MAX_FILE_BYTES:
            raise HTTPException(413, f"File troppo grande (max {MAX_FILE_BYTES // (1024*1024)} MB)")
        if not data:
            raise HTTPException(400, "File vuoto")

        content_type = file.content_type or ALLOWED_EXT.get(ext, "application/octet-stream")
        storage_path = f"{APP_NAME}/uploads/{user['id']}/{gen_id()}.{ext}"
        result = storage_put(storage_path, data, content_type)

        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        doc = {
            "id": gen_id(), "user_id": user["id"],
            "client_id": client_id or None,
            "name": name or file.filename,
            "category": category,
            "url": "",
            "notes": notes,
            "tags": tag_list,
            "storage_path": result.get("path", storage_path),
            "original_filename": file.filename,
            "content_type": content_type,
            "size": len(data),
            "is_deleted": False,
            "created_at": now_iso(),
        }
        return await self.repo.insert(doc)

    async def update_document_meta(self, user: dict, did: str, payload: dict) -> None:
        allowed = {k: v for k, v in payload.items() if k in {"name", "category", "notes", "client_id", "tags"}}
        if "tags" in allowed and isinstance(allowed["tags"], list):
            allowed["tags"] = [str(t).strip() for t in allowed["tags"] if str(t).strip()]
        ok = await self.repo.update_meta(did, user["id"], allowed)
        if not ok:
            raise HTTPException(404, "Documento non trovato")

    async def get_document_for_download(self, user_id: str, did: str) -> dict:
        doc = await self.repo.find_one(did, user_id)
        if not doc or not doc.get("storage_path"):
            raise HTTPException(404, "Documento non trovato")
        return doc

    async def delete_document(self, user: dict, did: str) -> None:
        await self.repo.soft_delete(did, user["id"])


document_service = DocumentService()

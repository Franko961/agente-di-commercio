import tempfile
from fastapi import HTTPException
from core.utils import gen_id, now_iso
from core.config import MAX_FILE_BYTES
from repositories.employee_document_repository import employee_document_repository
from repositories.employee_repository import employee_repository
from services.storage_service import (
    storage_put_stream, ALLOWED_EXT, APP_NAME, sanitize_filename, _sniff_matches_extension,
)
from models.employee_document import EmployeeDocumentMetaUpdate

# Stessa logica di sicurezza upload di document_service.py (sniffing dei
# magic bytes, spooling su disco oltre una certa soglia): duplicata qui
# invece di condivisa perché il modulo Documenti aziendale è gated dal
# modulo "documenti", mentre questo deve restare gated da "personale" —
# vedi routers/employee_documents.py.
HEAD_SNIFF_BYTES = 4096
SPOOL_MAX_MEMORY_BYTES = 8 * 1024 * 1024


class EmployeeDocumentService:
    def __init__(self, repo=employee_document_repository, employees=employee_repository):
        self.repo = repo
        self.employees = employees

    async def _validate_employee(self, user_id: str, employee_id: str) -> dict:
        employee = await self.employees.find_one(employee_id, user_id)
        if not employee:
            raise HTTPException(404, "Dipendente non trovato")
        return employee

    async def list_documents(self, user: dict, employee_id: str) -> list:
        await self._validate_employee(user["id"], employee_id)
        return await self.repo.find_many(employee_id, user["id"])

    async def upload_document(self, user: dict, employee_id: str, file, name: str, category: str, notes: str) -> dict:
        await self._validate_employee(user["id"], employee_id)
        if not file.filename:
            raise HTTPException(400, "File mancante")
        ext = (file.filename.rsplit(".", 1)[-1] if "." in file.filename else "bin").lower()
        if ext not in ALLOWED_EXT:
            raise HTTPException(400, f"Estensione .{ext} non supportata. Consentite: PDF, Excel, Word, immagini.")

        chunk_size = 1024 * 1024
        head = b""
        total = 0
        spooled = tempfile.SpooledTemporaryFile(max_size=SPOOL_MAX_MEMORY_BYTES)
        try:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_FILE_BYTES:
                    raise HTTPException(413, f"File troppo grande (max {MAX_FILE_BYTES // (1024*1024)} MB)")
                if len(head) < HEAD_SNIFF_BYTES:
                    head += chunk[: HEAD_SNIFF_BYTES - len(head)]
                spooled.write(chunk)

            if total == 0:
                raise HTTPException(400, "File vuoto")

            if not _sniff_matches_extension(head, ext):
                raise HTTPException(400, "Il contenuto del file non corrisponde al tipo dichiarato dall'estensione")

            content_type = ALLOWED_EXT[ext]
            storage_path = f"{APP_NAME}/uploads/{user['id']}/employees/{employee_id}/{gen_id()}.{ext}"
            spooled.seek(0)
            result = storage_put_stream(storage_path, spooled, content_type)
        finally:
            spooled.close()

        safe_original_filename = sanitize_filename(file.filename)
        doc = {
            "id": gen_id(), "user_id": user["id"], "employee_id": employee_id,
            "name": sanitize_filename(name) if name else safe_original_filename,
            "category": category,
            "notes": notes,
            "storage_path": result.get("path", storage_path),
            "original_filename": safe_original_filename,
            "content_type": content_type,
            "size": total,
            "is_deleted": False,
            "created_at": now_iso(),
        }
        return await self.repo.insert(doc)

    async def update_meta(self, user: dict, did: str, payload: EmployeeDocumentMetaUpdate) -> None:
        allowed = payload.model_dump(exclude_unset=True)
        if "name" in allowed:
            allowed["name"] = sanitize_filename(allowed["name"])
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


employee_document_service = EmployeeDocumentService()

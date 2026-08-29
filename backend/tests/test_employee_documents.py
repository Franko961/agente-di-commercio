"""
Verifica services/employee_document_service.py: upload, elenco, modifica
metadati ed eliminazione dei documenti caricati sulla scheda dipendente
(contratto, documento d'identità, patente, ecc. — vedi models/employee_document.py).

Ricalca la logica di sicurezza upload già validata per il modulo Documenti
aziendale (services/document_service.py): sniffing dei magic bytes,
limite di dimensione, whitelist estensioni — duplicata qui invece che
condivisa perché questo modulo resta gated da "personale", non da
"documenti" (vedi routers/employee_documents.py).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_employee_documents.py -v
"""

import asyncio
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, ".")

import services.employee_document_service as employee_document_service_mod
from models.employee_document import EmployeeDocumentMetaUpdate
from services.employee_document_service import EmployeeDocumentService


def run(coro):
    return asyncio.run(coro)


USER = {
    "id": "user-1",
    "email": "manager@example.com",
    "enabled_extra_modules": ["personale"],
}
OTHER_USER = {
    "id": "user-2",
    "email": "altro@example.com",
    "enabled_extra_modules": ["personale"],
}

# %PDF- come primi byte: unica firma richiesta da _sniff_matches_extension
# per l'estensione "pdf" (vedi services/storage_service.py).
PDF_BYTES = b"%PDF-1.4\n%fake pdf content for tests\n" + b"x" * 100


class FakeEmployeeRepo:
    def __init__(self):
        self.docs = {}

    async def find_one(self, eid, user_id):
        d = self.docs.get(eid)
        return d if d and d["user_id"] == user_id else None


class FakeEmployeeDocumentRepo:
    def __init__(self):
        self.docs = {}

    async def find_many(self, employee_id, user_id):
        return [
            d
            for d in self.docs.values()
            if d["employee_id"] == employee_id
            and d["user_id"] == user_id
            and not d.get("is_deleted")
        ]

    async def find_one(self, did, user_id, employee_id):
        d = self.docs.get(did)
        if (
            not d
            or d["user_id"] != user_id
            or d["employee_id"] != employee_id
            or d.get("is_deleted")
        ):
            return None
        return d

    async def insert(self, doc):
        self.docs[doc["id"]] = dict(doc)
        return doc

    async def update_meta(self, did, user_id, employee_id, data):
        d = self.docs.get(did)
        if (
            not d
            or d["user_id"] != user_id
            or d["employee_id"] != employee_id
            or d.get("is_deleted")
        ):
            return False
        d.update(data)
        return True

    async def soft_delete(self, did, user_id, employee_id):
        d = self.docs.get(did)
        if d and d["user_id"] == user_id and d["employee_id"] == employee_id:
            d["is_deleted"] = True


class FakeUserRepo:
    def __init__(self):
        self.docs = {}

    async def find_by_id(self, uid):
        return self.docs.get(uid)


class FakeUploadFile:
    def __init__(self, filename, content):
        self.filename = filename
        self._content = content
        self._offset = 0

    async def read(self, n):
        chunk = self._content[self._offset : self._offset + n]
        self._offset += len(chunk)
        return chunk


def build_service():
    doc_repo = FakeEmployeeDocumentRepo()
    emp_repo = FakeEmployeeRepo()
    emp_repo.docs["emp-1"] = {"id": "emp-1", "user_id": USER["id"], "name": "Mario"}
    user_repo = FakeUserRepo()
    user_repo.docs[USER["id"]] = USER
    user_repo.docs[OTHER_USER["id"]] = OTHER_USER
    service = EmployeeDocumentService(
        repo=doc_repo, employees=emp_repo, users=user_repo
    )
    return service, doc_repo, emp_repo, user_repo


def patch_storage(monkeypatch, put_result=None):
    calls = []

    def fake_put_stream(path, fileobj, content_type):
        calls.append({"path": path, "content_type": content_type})
        return put_result or {"path": path}

    monkeypatch.setattr(
        employee_document_service_mod, "storage_put_stream", fake_put_stream
    )
    return calls


# ---------- upload_document ----------


def test_upload_document_happy_path(monkeypatch):
    service, doc_repo, _, _ = build_service()
    calls = patch_storage(monkeypatch)
    file = FakeUploadFile("contratto.pdf", PDF_BYTES)

    doc = run(
        service.upload_document(
            USER, "emp-1", file, "Contratto 2026", "contratto", "firmato il 1/1"
        )
    )

    assert doc["employee_id"] == "emp-1"
    assert doc["user_id"] == USER["id"]
    assert doc["category"] == "contratto"
    assert doc["name"] == "Contratto 2026"
    assert doc["original_filename"] == "contratto.pdf"
    assert doc["content_type"] == "application/pdf"
    assert doc["size"] == len(PDF_BYTES)
    assert doc["is_deleted"] is False
    assert len(calls) == 1
    assert "employees/emp-1/" in calls[0]["path"]


def test_upload_document_defaults_name_to_filename(monkeypatch):
    service, doc_repo, _, _ = build_service()
    patch_storage(monkeypatch)
    file = FakeUploadFile("patente.pdf", PDF_BYTES)

    doc = run(service.upload_document(USER, "emp-1", file, "", "patente", ""))

    assert doc["name"] == "patente.pdf"


def test_upload_document_rejects_unknown_employee(monkeypatch):
    service, _, _, _ = build_service()
    patch_storage(monkeypatch)
    file = FakeUploadFile("x.pdf", PDF_BYTES)

    with pytest.raises(HTTPException) as exc:
        run(service.upload_document(USER, "emp-does-not-exist", file, "", "altro", ""))
    assert exc.value.status_code == 404


def test_upload_document_rejects_other_users_employee(monkeypatch):
    service, _, _, _ = build_service()
    patch_storage(monkeypatch)
    file = FakeUploadFile("x.pdf", PDF_BYTES)

    with pytest.raises(HTTPException) as exc:
        run(service.upload_document(OTHER_USER, "emp-1", file, "", "altro", ""))
    assert exc.value.status_code == 404


def test_upload_document_rejects_disallowed_extension(monkeypatch):
    service, _, _, _ = build_service()
    patch_storage(monkeypatch)
    file = FakeUploadFile("script.exe", b"MZ" + b"x" * 100)

    with pytest.raises(HTTPException) as exc:
        run(service.upload_document(USER, "emp-1", file, "", "altro", ""))
    assert exc.value.status_code == 400


def test_upload_document_rejects_content_not_matching_extension(monkeypatch):
    service, _, _, _ = build_service()
    patch_storage(monkeypatch)
    # Estensione .pdf dichiarata, ma senza la firma "%PDF-" reale.
    file = FakeUploadFile("finto.pdf", b"not really a pdf" + b"x" * 100)

    with pytest.raises(HTTPException) as exc:
        run(service.upload_document(USER, "emp-1", file, "", "altro", ""))
    assert exc.value.status_code == 400


def test_upload_document_rejects_empty_file(monkeypatch):
    service, _, _, _ = build_service()
    patch_storage(monkeypatch)
    file = FakeUploadFile("vuoto.pdf", b"")

    with pytest.raises(HTTPException) as exc:
        run(service.upload_document(USER, "emp-1", file, "", "altro", ""))
    assert exc.value.status_code == 400


def test_upload_document_rejects_oversized_file(monkeypatch):
    service, _, _, _ = build_service()
    patch_storage(monkeypatch)
    monkeypatch.setattr(employee_document_service_mod, "MAX_FILE_BYTES", 50)
    file = FakeUploadFile("grande.pdf", PDF_BYTES)  # più di 50 byte

    with pytest.raises(HTTPException) as exc:
        run(service.upload_document(USER, "emp-1", file, "", "altro", ""))
    assert exc.value.status_code == 413


# ---------- list_documents ----------


def test_list_documents_scoped_to_employee_and_user(monkeypatch):
    service, doc_repo, emp_repo, _ = build_service()
    emp_repo.docs["emp-2"] = {"id": "emp-2", "user_id": USER["id"], "name": "Luca"}
    patch_storage(monkeypatch)
    file = FakeUploadFile("a.pdf", PDF_BYTES)
    run(service.upload_document(USER, "emp-1", file, "", "altro", ""))
    file2 = FakeUploadFile("b.pdf", PDF_BYTES)
    run(service.upload_document(USER, "emp-2", file2, "", "altro", ""))

    docs = run(service.list_documents(USER, "emp-1"))
    assert len(docs) == 1
    assert docs[0]["employee_id"] == "emp-1"


def test_list_documents_rejects_unknown_employee():
    service, _, _, _ = build_service()
    with pytest.raises(HTTPException) as exc:
        run(service.list_documents(USER, "emp-does-not-exist"))
    assert exc.value.status_code == 404


# ---------- update_meta ----------


def test_update_meta_updates_and_sanitizes_name(monkeypatch):
    service, doc_repo, _, _ = build_service()
    patch_storage(monkeypatch)
    file = FakeUploadFile("a.pdf", PDF_BYTES)
    doc = run(service.upload_document(USER, "emp-1", file, "Vecchio nome", "altro", ""))

    run(
        service.update_meta(
            USER,
            "emp-1",
            doc["id"],
            EmployeeDocumentMetaUpdate(name="Nuovo/nome*", category="contratto"),
        )
    )

    updated = doc_repo.docs[doc["id"]]
    assert updated["category"] == "contratto"
    assert "/" not in updated["name"]


def test_update_meta_unknown_document_raises_404():
    service, _, _, _ = build_service()
    with pytest.raises(HTTPException) as exc:
        run(
            service.update_meta(
                USER, "emp-1", "does-not-exist", EmployeeDocumentMetaUpdate(notes="x")
            )
        )
    assert exc.value.status_code == 404


def test_update_meta_wrong_employee_id_raises_404(monkeypatch):
    # Documento reale, ma eid nell'URL non è quello a cui appartiene: la
    # richiesta non deve "trovarlo" comunque solo perché did+user_id
    # coincidono — vedi employee_document_repository.find_one/update_meta.
    service, doc_repo, emp_repo, _ = build_service()
    emp_repo.docs["emp-2"] = {"id": "emp-2", "user_id": USER["id"], "name": "Luca"}
    patch_storage(monkeypatch)
    file = FakeUploadFile("a.pdf", PDF_BYTES)
    doc = run(service.upload_document(USER, "emp-1", file, "", "altro", ""))

    with pytest.raises(HTTPException) as exc:
        run(
            service.update_meta(
                USER, "emp-2", doc["id"], EmployeeDocumentMetaUpdate(notes="x")
            )
        )
    assert exc.value.status_code == 404


# ---------- delete_document / get_document_for_download ----------


def test_delete_document_soft_deletes(monkeypatch):
    service, doc_repo, _, _ = build_service()
    patch_storage(monkeypatch)
    file = FakeUploadFile("a.pdf", PDF_BYTES)
    doc = run(service.upload_document(USER, "emp-1", file, "", "altro", ""))

    run(service.delete_document(USER, "emp-1", doc["id"]))

    assert doc_repo.docs[doc["id"]]["is_deleted"] is True
    assert run(service.list_documents(USER, "emp-1")) == []
    with pytest.raises(HTTPException) as exc:
        run(service.get_document_for_download(USER["id"], "emp-1", doc["id"]))
    assert exc.value.status_code == 404


def test_delete_document_wrong_employee_id_does_not_delete(monkeypatch):
    service, doc_repo, emp_repo, _ = build_service()
    emp_repo.docs["emp-2"] = {"id": "emp-2", "user_id": USER["id"], "name": "Luca"}
    patch_storage(monkeypatch)
    file = FakeUploadFile("a.pdf", PDF_BYTES)
    doc = run(service.upload_document(USER, "emp-1", file, "", "altro", ""))

    run(service.delete_document(USER, "emp-2", doc["id"]))

    assert doc_repo.docs[doc["id"]]["is_deleted"] is False


def test_get_document_for_download_rejects_other_user(monkeypatch):
    service, _, _, _ = build_service()
    patch_storage(monkeypatch)
    file = FakeUploadFile("a.pdf", PDF_BYTES)
    doc = run(service.upload_document(USER, "emp-1", file, "", "altro", ""))

    with pytest.raises(HTTPException) as exc:
        run(service.get_document_for_download(OTHER_USER["id"], "emp-1", doc["id"]))
    assert exc.value.status_code == 404


def test_get_document_for_download_rejects_wrong_employee_id(monkeypatch):
    service, doc_repo, emp_repo, _ = build_service()
    emp_repo.docs["emp-2"] = {"id": "emp-2", "user_id": USER["id"], "name": "Luca"}
    patch_storage(monkeypatch)
    file = FakeUploadFile("a.pdf", PDF_BYTES)
    doc = run(service.upload_document(USER, "emp-1", file, "", "altro", ""))

    with pytest.raises(HTTPException) as exc:
        run(service.get_document_for_download(USER["id"], "emp-2", doc["id"]))
    assert exc.value.status_code == 404


def test_get_document_for_download_rejects_when_module_disabled(monkeypatch):
    # Il link (diretto o firmato) può essere stato generato PRIMA che
    # l'account disattivasse il modulo Personale: la verifica va ripetuta
    # qui contro il proprietario del documento, non solo a monte sulla
    # rotta di elenco/upload/cancellazione (vedi commento nel service).
    service, doc_repo, _, user_repo = build_service()
    patch_storage(monkeypatch)
    file = FakeUploadFile("a.pdf", PDF_BYTES)
    doc = run(service.upload_document(USER, "emp-1", file, "", "altro", ""))

    user_repo.docs[USER["id"]] = {**USER, "enabled_extra_modules": []}

    with pytest.raises(HTTPException) as exc:
        run(service.get_document_for_download(USER["id"], "emp-1", doc["id"]))
    assert exc.value.status_code == 403

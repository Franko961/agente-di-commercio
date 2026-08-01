"""
Verifica che create_document, upload_document e update_document_meta
rifiutino un client_id che non appartiene all'utente. Prima di questa
modifica, client_id arrivava dal payload/form dell'utente e veniva
accettato così com'è senza alcuna verifica di ownership: un id di un altro
utente (indovinato o enumerato) veniva comunque salvato, collegando
silenziosamente il documento a un cliente che non è il suo.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_document_client_ownership.py -v
"""
import sys
import asyncio

import pytest
from fastapi import HTTPException

sys.path.insert(0, ".")

from models.document import DocumentIn, DocumentMetaUpdate
from services.document_service import DocumentService


def run(coro):
    return asyncio.run(coro)


class FakeDocRepo:
    def __init__(self):
        self.docs = []

    async def insert(self, doc):
        self.docs.append(doc)
        return doc

    async def update_meta(self, did, user_id, data):
        for d in self.docs:
            if d["id"] == did:
                d.update(data)
                return True
        return False


class FakeClientRepo:
    def __init__(self, clients_by_id):
        self.clients_by_id = clients_by_id

    async def find_one(self, cid, user_id):
        return self.clients_by_id.get(cid)


class FakeUploadFile:
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self._content = content
        self._pos = 0

    async def read(self, n: int) -> bytes:
        chunk = self._content[self._pos:self._pos + n]
        self._pos += len(chunk)
        return chunk


USER = {"id": "user-1"}
CLIENTI = {"c1": {"id": "c1", "user_id": "user-1", "company_name": "Cliente Uno"}}


def build_service():
    return DocumentService(repo=FakeDocRepo(), client_repo=FakeClientRepo(CLIENTI))


def test_create_document_con_client_id_valido_funziona():
    service = build_service()
    doc = run(service.create_document(USER, DocumentIn(name="Contratto", client_id="c1")))
    assert doc["client_id"] == "c1"


def test_create_document_rifiuta_client_id_di_un_altro_utente():
    service = build_service()
    with pytest.raises(HTTPException) as exc_info:
        run(service.create_document(USER, DocumentIn(name="Contratto", client_id="c-di-un-altro-utente")))
    assert exc_info.value.status_code == 404


def test_create_document_senza_client_id_funziona_comunque():
    service = build_service()
    doc = run(service.create_document(USER, DocumentIn(name="Nota generica")))
    assert doc["client_id"] is None


def test_upload_document_rifiuta_client_id_di_un_altro_utente(monkeypatch):
    import services.document_service as doc_service_mod
    monkeypatch.setattr(doc_service_mod, "storage_put_stream", lambda *a, **k: {"path": "x"})
    service = build_service()
    file = FakeUploadFile("doc.pdf", b"%PDF-1.7\n" + b"\x00" * 100)

    with pytest.raises(HTTPException) as exc_info:
        run(service.upload_document(USER, file, "Doc", "altro", "c-di-un-altro-utente", "", ""))
    assert exc_info.value.status_code == 404


def test_update_document_meta_rifiuta_client_id_di_un_altro_utente():
    service = build_service()
    run(service.repo.insert({"id": "doc-1", "user_id": "user-1", "name": "originale.pdf", "client_id": None}))

    with pytest.raises(HTTPException) as exc_info:
        run(service.update_document_meta(USER, "doc-1", DocumentMetaUpdate(client_id="c-di-un-altro-utente")))
    assert exc_info.value.status_code == 404


def test_update_document_meta_con_client_id_valido_funziona():
    service = build_service()
    run(service.repo.insert({"id": "doc-1", "user_id": "user-1", "name": "originale.pdf", "client_id": None}))

    run(service.update_document_meta(USER, "doc-1", DocumentMetaUpdate(client_id="c1")))

    assert service.repo.docs[0]["client_id"] == "c1"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

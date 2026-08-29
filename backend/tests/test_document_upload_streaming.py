"""
Verifica che l'upload documenti (services.document_service.upload_document)
non tenga più l'intero file in memoria come oggetto bytes: il contenuto va
in uno SpooledTemporaryFile (RAM solo fino a una soglia, poi disco), e solo i
primi HEAD_SNIFF_BYTES byte vengono conservati a parte per la verifica della
firma — indipendentemente da quanto è grande il file.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_document_upload_streaming.py -v
"""

import asyncio
import sys

import pytest

sys.path.insert(0, ".")

import services.document_service as doc_service_mod
from models.document import DocumentMetaUpdate
from services.document_service import HEAD_SNIFF_BYTES, DocumentService


def run(coro):
    return asyncio.run(coro)


class FakeUploadFile:
    """Imita fastapi.UploadFile: espone .filename e un .read(n) asincrono
    che consuma un buffer bytes a blocchi, come farebbe un vero upload."""

    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self._content = content
        self._pos = 0
        self.read_calls = 0

    async def read(self, n: int) -> bytes:
        self.read_calls += 1
        chunk = self._content[self._pos : self._pos + n]
        self._pos += len(chunk)
        return chunk


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


def build_service():
    return DocumentService(repo=FakeDocRepo())


def _pdf_bytes(total_size: int) -> bytes:
    """Un PDF 'valido' quanto basta per superare _sniff_matches_extension
    (firma %PDF- a inizio file), riempito fino a total_size byte."""
    head = b"%PDF-1.7\n"
    return head + b"\x00" * (total_size - len(head))


def test_upload_normale_passa_e_registra_dimensione_corretta(monkeypatch):
    captured = {}

    def fake_storage_put_stream(path, fileobj, content_type):
        captured["fileobj_content"] = fileobj.read()
        captured["path"] = path
        captured["content_type"] = content_type
        return {"path": path}

    monkeypatch.setattr(doc_service_mod, "storage_put_stream", fake_storage_put_stream)
    service = build_service()
    content = _pdf_bytes(5000)
    file = FakeUploadFile("contratto.pdf", content)

    doc = run(
        service.upload_document(
            {"id": "user-1"},
            file,
            "Contratto",
            "contratto",
            None,
            "",
            "",
        )
    )

    assert doc["size"] == len(content)
    assert doc["content_type"] == "application/pdf"
    assert (
        captured["fileobj_content"] == content
    )  # nulla perso/alterato nello streaming


def test_solo_i_primi_byte_vengono_usati_per_lo_sniffing(monkeypatch):
    """Un file grande quanto si vuole, ma con la firma valida solo nei primi
    byte: non deve servire leggere/tenere in memoria il resto per superare
    la verifica. Il "resto" qui è deliberatamente enorme rispetto a
    HEAD_SNIFF_BYTES per dimostrare che la dimensione totale non conta ai
    fini dello sniffing."""

    def fake_storage_put_stream(path, fileobj, content_type):
        return {"path": path}

    monkeypatch.setattr(doc_service_mod, "storage_put_stream", fake_storage_put_stream)
    service = build_service()
    content = _pdf_bytes(HEAD_SNIFF_BYTES * 50)  # ben oltre la finestra di sniffing
    file = FakeUploadFile("video_contratto.pdf", content)

    doc = run(
        service.upload_document(
            {"id": "user-1"},
            file,
            "Doc",
            "altro",
            None,
            "",
            "",
        )
    )

    assert doc["size"] == len(content)


def test_contenuto_camuffato_rifiutato_anche_se_il_file_e_grande(monkeypatch):
    """La firma sbagliata è comunque dentro la finestra HEAD_SNIFF_BYTES,
    quindi deve essere rifiutato a prescindere da quanto è grande il resto
    del file — la sicurezza dello sniff non deve dipendere dalla
    dimensione totale."""

    def fake_storage_put_stream(path, fileobj, content_type):
        raise AssertionError("non dovrebbe mai arrivare all'upload S3")

    monkeypatch.setattr(doc_service_mod, "storage_put_stream", fake_storage_put_stream)
    service = build_service()
    fake_content = b"non e' un pdf" + b"\x00" * (HEAD_SNIFF_BYTES * 10)
    file = FakeUploadFile("finto.pdf", fake_content)

    with pytest.raises(Exception) as exc_info:
        run(
            service.upload_document(
                {"id": "user-1"}, file, "Doc", "altro", None, "", ""
            )
        )
    assert "non corrisponde" in str(exc_info.value.detail).lower()


def test_file_oltre_il_limite_viene_interrotto_subito(monkeypatch):
    """Supera MAX_FILE_BYTES: deve fallire con 413 SENZA mai chiamare
    storage_put_stream (il file non viene mai completato/caricato)."""

    def fake_storage_put_stream(path, fileobj, content_type):
        raise AssertionError("non dovrebbe mai arrivare all'upload: file troppo grande")

    monkeypatch.setattr(doc_service_mod, "storage_put_stream", fake_storage_put_stream)
    monkeypatch.setattr(
        doc_service_mod, "MAX_FILE_BYTES", 10 * 1024
    )  # soglia bassa per il test
    service = build_service()
    content = _pdf_bytes(50 * 1024)  # sopra la soglia appena impostata
    file = FakeUploadFile("grande.pdf", content)

    with pytest.raises(Exception) as exc_info:
        run(
            service.upload_document(
                {"id": "user-1"}, file, "Doc", "altro", None, "", ""
            )
        )
    assert exc_info.value.status_code == 413


def test_file_vuoto_rifiutato(monkeypatch):
    def fake_storage_put_stream(path, fileobj, content_type):
        raise AssertionError("non dovrebbe mai arrivare all'upload: file vuoto")

    monkeypatch.setattr(doc_service_mod, "storage_put_stream", fake_storage_put_stream)
    service = build_service()
    file = FakeUploadFile("vuoto.pdf", b"")

    with pytest.raises(Exception) as exc_info:
        run(
            service.upload_document(
                {"id": "user-1"}, file, "Doc", "altro", None, "", ""
            )
        )
    assert exc_info.value.status_code == 400


def test_estensione_non_supportata_rifiutata_prima_di_leggere_il_file():
    service = build_service()
    file = FakeUploadFile("script.exe", b"MZ\x90\x00")

    with pytest.raises(Exception) as exc_info:
        run(
            service.upload_document(
                {"id": "user-1"}, file, "Doc", "altro", None, "", ""
            )
        )
    assert exc_info.value.status_code == 400
    assert (
        file.read_calls == 0
    )  # rifiutato dall'estensione, il file non va nemmeno letto


def test_update_document_meta_sanifica_il_nome():
    """A differenza del nome impostato al primo upload (già ripulito da
    sanitize_filename), il nome modificato in un secondo momento via
    update_document_meta non veniva più sanificato: un valore con
    separatori di percorso poteva restare salvato così com'è, per poi
    essere riusato come nome voce nello zip dell'export GDPR."""
    service = build_service()
    run(
        service.repo.insert(
            {"id": "doc-1", "user_id": "user-1", "name": "originale.pdf"}
        )
    )

    run(
        service.update_document_meta(
            {"id": "user-1"}, "doc-1", DocumentMetaUpdate(name="../../evil.sh")
        )
    )

    saved = service.repo.docs[0]
    assert "/" not in saved["name"]
    assert "\\" not in saved["name"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

"""
Verifica storage_get_stream(): deve restituire un iteratore di blocchi (per
alimentare una StreamingResponse) invece di leggere l'intero oggetto S3 in
memoria come fa storage_get().

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_storage_service_streaming.py -v
"""
import sys

import pytest

sys.path.insert(0, ".")

import services.storage_service as storage_mod
from services.storage_service import storage_get_stream, storage_put_stream


class FakeStreamingBody:
    def __init__(self, chunks):
        self._chunks = list(chunks)
        self.closed = False

    def iter_chunks(self, chunk_size=1024):
        for c in self._chunks:
            yield c

    def close(self):
        self.closed = True


class FakeS3Client:
    def __init__(self, chunks, content_type="application/pdf", content_length=None):
        self._chunks = chunks
        self._content_type = content_type
        self._content_length = content_length
        self.uploaded = None

    def get_object(self, Bucket, Key):
        return {
            "Body": FakeStreamingBody(self._chunks),
            "ContentType": self._content_type,
            "ContentLength": self._content_length,
        }

    def upload_fileobj(self, fileobj, bucket, key, ExtraArgs=None):
        self.uploaded = {"content": fileobj.read(), "bucket": bucket, "key": key, "extra": ExtraArgs}


def test_storage_get_stream_restituisce_i_blocchi_in_ordine(monkeypatch):
    fake_s3 = FakeS3Client([b"parte1", b"parte2", b"parte3"], content_length=18)
    monkeypatch.setattr(storage_mod, "get_s3", lambda: fake_s3)

    iterator, content_type, content_length = storage_get_stream("path/al/file.pdf")

    assert list(iterator) == [b"parte1", b"parte2", b"parte3"]
    assert content_type == "application/pdf"
    assert content_length == 18


def test_storage_get_stream_chiude_il_body_dopo_la_lettura(monkeypatch):
    body = FakeStreamingBody([b"x"])
    fake_s3 = FakeS3Client([])
    fake_s3.get_object = lambda Bucket, Key: {"Body": body, "ContentType": "application/pdf", "ContentLength": 1}
    monkeypatch.setattr(storage_mod, "get_s3", lambda: fake_s3)

    iterator, _, _ = storage_get_stream("path/al/file.pdf")
    list(iterator)  # consuma tutto il generatore

    assert body.closed is True


def test_storage_get_stream_senza_s3_configurato_solleva_errore(monkeypatch):
    monkeypatch.setattr(storage_mod, "get_s3", lambda: None)

    with pytest.raises(Exception) as exc_info:
        storage_get_stream("qualsiasi/path.pdf")
    assert exc_info.value.status_code == 500


def test_storage_put_stream_passa_il_fileobj_a_upload_fileobj(monkeypatch):
    import io
    fake_s3 = FakeS3Client([])
    monkeypatch.setattr(storage_mod, "get_s3", lambda: fake_s3)

    result = storage_put_stream("path/nuovo.pdf", io.BytesIO(b"contenuto pdf"), "application/pdf")

    assert result == {"path": "path/nuovo.pdf"}
    assert fake_s3.uploaded["content"] == b"contenuto pdf"
    assert fake_s3.uploaded["extra"] == {"ContentType": "application/pdf"}


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

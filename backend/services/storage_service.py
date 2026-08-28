import logging
import re

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException

from core.config import (
    AWS_ACCESS_KEY_ID,
    AWS_REGION,
    AWS_SECRET_ACCESS_KEY,
    S3_BUCKET,
    S3_ENDPOINT,
)

logger = logging.getLogger(__name__)

APP_NAME = "agente-crm"

ALLOWED_EXT = {
    "pdf": "application/pdf",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "csv": "text/csv",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "heic": "image/heic",
    "heif": "image/heif",
    "mp4": "video/mp4",
    "mov": "video/quicktime",
    "webm": "video/webm",
    "avi": "video/x-msvideo",
    "mkv": "video/x-matroska",
}


def _looks_like_html_or_script(data: bytes) -> bool:
    """Controllo di sicurezza per i formati 'testo libero' (txt, csv), che non
    hanno una firma binaria affidabile: rifiuta il contenuto se sembra HTML o
    script eseguibile camuffato da file di testo — il modo più comune per
    aggirare un controllo basato solo sull'estensione (es. un file .txt il
    cui contenuto è in realtà <script>...</script>)."""
    head = data[:2048].lstrip().lower()
    danger_markers = (
        b"<script",
        b"<html",
        b"<!doctype html",
        b"<iframe",
        b"<svg",
        b"<?php",
    )
    return any(m in head for m in danger_markers)


def _sniff_matches_extension(data: bytes, ext: str) -> bool:
    """Verifica che i byte reali del file corrispondano davvero al tipo
    dichiarato dall'estensione (magic bytes), invece di fidarsi ciecamente
    del nome file o del Content-Type dichiarato dal browser — entrambi
    liberamente falsificabili da chi carica il file. Copre solo il set fisso
    di estensioni in ALLOWED_EXT, quindi non serve una libreria esterna
    (python-magic/libmagic) con le complicazioni di deploy che comporta."""
    if not data:
        return False
    head = data[:16]

    if ext == "pdf":
        return head.startswith(b"%PDF-")
    if ext == "png":
        return head.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in ("jpg", "jpeg"):
        return head.startswith(b"\xff\xd8\xff")
    if ext in ("doc", "xls"):
        # Formato OLE2 legacy di Office, comune a doc/xls/ppt: qui basta
        # sapere che è un contenitore OLE2 valido, non serve distinguerli.
        return head.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
    if ext in ("docx", "xlsx"):
        # Contenitore ZIP (Office Open XML). PK\x05\x06 / PK\x07\x08 coprono
        # rispettivamente uno zip vuoto e uno con spanning, casi limite ma
        # innocui da accettare qui.
        return head[:2] == b"PK" and head[2:4] in (
            b"\x03\x04",
            b"\x05\x06",
            b"\x07\x08",
        )
    if ext in ("mp4", "mov"):
        # Contenitori ISO-BMFF (MPEG-4/QuickTime): il box 'ftyp' è sempre ai
        # byte 4-8 nei file validi, non c'è un magic number a inizio file.
        return data[4:8] == b"ftyp"
    if ext in ("heic", "heif"):
        # Anche HEIC/HEIF sono contenitori ISO-BMFF (come mp4/mov): stesso box
        # 'ftyp', ma con 'brand' specifico ai byte 8-12 (i valori tipici
        # prodotti da iPhone/fotocamere).
        return data[4:8] == b"ftyp" and data[8:12] in (
            b"heic",
            b"heix",
            b"hevc",
            b"hevx",
            b"mif1",
            b"msf1",
        )
    if ext == "webp":
        return head.startswith(b"RIFF") and data[8:12] == b"WEBP"
    if ext == "webm" or ext == "mkv":
        return head.startswith(b"\x1a\x45\xdf\xa3")  # header EBML (Matroska/WebM)
    if ext == "avi":
        return head.startswith(b"RIFF") and data[8:12] == b"AVI "
    if ext in ("csv", "txt"):
        # Nessuna firma binaria affidabile per il testo libero: il controllo
        # utile qui è escludere contenuti HTML/script camuffati, non
        # verificare una struttura specifica.
        return not _looks_like_html_or_script(data)
    return False


_FILENAME_SAFE_RE = re.compile(r"[^A-Za-z0-9À-ÿ ._\-()]+")


def sanitize_filename(filename: str, fallback: str = "file") -> str:
    """Ripulisce un nome file prima di salvarlo/riusarlo: rimuove byte nulli e
    caratteri di controllo, tronca la lunghezza, e sostituisce i caratteri non
    innocui (separatori di percorso, virgolette, ecc.) con '_'. Da applicare
    a original_filename PRIMA di salvarlo — anche se il path di storage reale
    usa già un id generato e non è quindi vulnerabile a path traversal, questo
    nome viene riproposto nell'header Content-Disposition al download, dove
    virgolette/newline non filtrati possono rompere o iniettare nell'header."""
    if not filename:
        return fallback
    cleaned = "".join(ch for ch in filename if ch.isprintable())
    cleaned = _FILENAME_SAFE_RE.sub("_", cleaned).strip()
    cleaned = cleaned[:200]
    return cleaned or fallback


_s3_client = None


def get_s3():
    global _s3_client
    if _s3_client:
        return _s3_client
    if not AWS_ACCESS_KEY_ID or not S3_BUCKET:
        return None
    kwargs = dict(
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )
    if S3_ENDPOINT:
        kwargs["endpoint_url"] = S3_ENDPOINT
    _s3_client = boto3.client("s3", **kwargs)
    return _s3_client


def init_storage() -> bool:
    """Check S3 is configured."""
    return get_s3() is not None


def storage_put(path: str, data: bytes, content_type: str) -> dict:
    s3 = get_s3()
    if not s3:
        raise HTTPException(
            500,
            "Storage S3 non disponibile — controlla AWS_ACCESS_KEY_ID e AWS_S3_BUCKET",
        )
    try:
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=path,
            Body=data,
            ContentType=content_type,
        )
        return {"path": path}
    except (BotoCoreError, ClientError) as e:
        logger.error(f"S3 put error: {e}")
        raise HTTPException(500, f"Errore upload S3: {str(e)[:200]}")


def storage_put_stream(path: str, fileobj, content_type: str) -> dict:
    """Come storage_put, ma accetta un file-like già posizionato all'inizio
    (es. un tempfile.SpooledTemporaryFile) invece di un blob bytes già
    interamente in memoria. boto3 gestisce da solo l'upload multipart in
    streaming, leggendo il file a blocchi — così un video o un documento
    pesante non devono mai esistere per intero come oggetto Python in RAM,
    a differenza di storage_put(path, data, ...)."""
    s3 = get_s3()
    if not s3:
        raise HTTPException(
            500,
            "Storage S3 non disponibile — controlla AWS_ACCESS_KEY_ID e AWS_S3_BUCKET",
        )
    try:
        s3.upload_fileobj(
            fileobj, S3_BUCKET, path, ExtraArgs={"ContentType": content_type}
        )
        return {"path": path}
    except (BotoCoreError, ClientError) as e:
        logger.error(f"S3 upload_fileobj error: {e}")
        raise HTTPException(500, f"Errore upload S3: {str(e)[:200]}")


def storage_get(path: str) -> tuple:
    s3 = get_s3()
    if not s3:
        raise HTTPException(500, "Storage S3 non disponibile")
    try:
        obj = s3.get_object(Bucket=S3_BUCKET, Key=path)
        data = obj["Body"].read()
        content_type = obj.get("ContentType", "application/octet-stream")
        return data, content_type
    except (BotoCoreError, ClientError) as e:
        logger.error(f"S3 get error: {e}")
        raise HTTPException(500, f"Errore download S3: {str(e)[:200]}")


def storage_get_stream(path: str, chunk_size: int = 1024 * 1024) -> tuple:
    """Come storage_get, ma restituisce un iteratore di blocchi invece del
    contenuto già interamente letto in memoria — pensato per essere passato
    a una StreamingResponse, così scaricare un video o un documento pesante
    non richiede di tenerlo per intero in RAM sul server durante l'invio."""
    s3 = get_s3()
    if not s3:
        raise HTTPException(500, "Storage S3 non disponibile")
    try:
        obj = s3.get_object(Bucket=S3_BUCKET, Key=path)
    except (BotoCoreError, ClientError) as e:
        logger.error(f"S3 get error: {e}")
        raise HTTPException(500, f"Errore download S3: {str(e)[:200]}")

    content_type = obj.get("ContentType", "application/octet-stream")
    content_length = obj.get("ContentLength")
    body = obj["Body"]

    def _iterator():
        try:
            for chunk in body.iter_chunks(chunk_size):
                yield chunk
        finally:
            body.close()

    return _iterator(), content_type, content_length


def storage_delete(path: str) -> None:
    """Cancellazione definitiva del file da S3 — non un semplice soft-delete
    del record nel database. Usata dalla cancellazione account (diritto
    all'oblio, art. 17 GDPR): un documento rimosso "per finta" (solo
    is_deleted=True) resterebbe comunque leggibile a chi conoscesse il
    percorso di storage. Non solleva se il file non esiste già (idempotente),
    solo per errori reali di comunicazione con S3."""
    s3 = get_s3()
    if not s3:
        raise HTTPException(500, "Storage S3 non disponibile")
    try:
        s3.delete_object(Bucket=S3_BUCKET, Key=path)
    except (BotoCoreError, ClientError) as e:
        logger.error(f"S3 delete error: {e}")
        raise HTTPException(500, f"Errore cancellazione S3: {str(e)[:200]}")

import logging
from fastapi import HTTPException
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from core.config import (
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION,
    S3_BUCKET, S3_ENDPOINT, MAX_FILE_BYTES,
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
    "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "mp4": "video/mp4", "mov": "video/quicktime", "webm": "video/webm",
    "avi": "video/x-msvideo", "mkv": "video/x-matroska",
}

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
        raise HTTPException(500, "Storage S3 non disponibile — controlla AWS_ACCESS_KEY_ID e AWS_S3_BUCKET")
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

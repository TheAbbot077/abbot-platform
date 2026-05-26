from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import uuid4

from django.conf import settings


class R2ConfigurationError(RuntimeError):
    pass


def r2_is_configured() -> bool:
    return all(
        [
            settings.CLOUDFLARE_R2_ACCOUNT_ID,
            settings.CLOUDFLARE_R2_ACCESS_KEY_ID,
            settings.CLOUDFLARE_R2_SECRET_ACCESS_KEY,
            settings.CLOUDFLARE_R2_BUCKET_NAME,
        ]
    )


def build_document_object_key(user_id: int, filename: str) -> str:
    safe_name = Path(filename).name.replace("\\", "_").replace("/", "_")
    return f"documents/user-{user_id}/{uuid4()}-{safe_name}"


def create_presigned_upload_url(object_key: str, content_type: str) -> str:
    client = _client()
    return client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.CLOUDFLARE_R2_BUCKET_NAME,
            "Key": object_key,
            "ContentType": content_type or "application/pdf",
        },
        ExpiresIn=15 * 60,
    )


def download_object_to_tempfile(object_key: str) -> str:
    temp_file = tempfile.NamedTemporaryFile(prefix="abbot-study-", suffix=".pdf", delete=False)
    temp_path = temp_file.name
    temp_file.close()

    _client().download_file(settings.CLOUDFLARE_R2_BUCKET_NAME, object_key, temp_path)
    return temp_path


def delete_object(object_key: str) -> None:
    if not object_key or not r2_is_configured():
        return

    _client().delete_object(Bucket=settings.CLOUDFLARE_R2_BUCKET_NAME, Key=object_key)


def _client():
    if not r2_is_configured():
        raise R2ConfigurationError("Cloudflare R2 is not configured.")

    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.CLOUDFLARE_R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.CLOUDFLARE_R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.CLOUDFLARE_R2_SECRET_ACCESS_KEY,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )

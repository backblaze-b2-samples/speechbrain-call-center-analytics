"""Generic object I/O for the call-analytics domain.

Kept separate from `b2_client.py` (which sits at the 300-line structural
ceiling) but in the SAME repo/ layer, so boto3/botocore stays confined here.
The cached S3 client is reused from `b2_client` for connection pooling, and
mutations invalidate the shared full-bucket listing cache so the Files browser
and stats stay consistent after a call is written or deleted.

Every helper is prefix-addressed. `delete_prefix` is deliberately scoped: it
refuses an empty prefix so a call delete can never fan out into a bucket-wide
wipe.
"""

import io

from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings
from app.repo.b2_client import _invalidate_list_cache, get_s3_client


def put_bytes(key: str, data: bytes, content_type: str) -> None:
    """Write raw bytes to B2 at `key`. Raises RuntimeError on failure."""
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=key,
            Body=io.BytesIO(data),
            ContentType=content_type,
        )
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 put_object failed for '{key}': {e}") from e
    _invalidate_list_cache()


def list_prefix(prefix: str) -> list[dict]:
    """Return [{key, size, last_modified}] for every object under `prefix`.

    Follows the S3 continuation token so callers see all keys, not just the
    first 1000. Raises RuntimeError on failure.
    """
    client = get_s3_client()
    out: list[dict] = []
    kwargs: dict = {
        "Bucket": settings.b2_bucket_name,
        "Prefix": prefix,
        "MaxKeys": 1000,
    }
    try:
        while True:
            resp = client.list_objects_v2(**kwargs)
            for obj in resp.get("Contents", []):
                out.append(
                    {
                        "key": obj["Key"],
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"],
                    }
                )
            if not resp.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = resp["NextContinuationToken"]
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 list failed for '{prefix}': {e}") from e
    return out


def delete_prefix(prefix: str) -> int:
    """Delete every object under `prefix`. Returns the count deleted.

    SAFETY: refuses an empty/whitespace prefix so this can never delete the
    whole bucket. Callers pass a per-call prefix like
    ``calls/2026-07-23/support/<callId>/``. Raises RuntimeError on failure.
    """
    if not prefix or not prefix.strip():
        raise ValueError("delete_prefix requires a non-empty prefix")
    client = get_s3_client()
    objects = [{"Key": o["key"]} for o in list_prefix(prefix)]
    if not objects:
        return 0
    deleted = 0
    try:
        # delete_objects caps at 1000 keys per call — batch to stay under it.
        for i in range(0, len(objects), 1000):
            batch = objects[i : i + 1000]
            client.delete_objects(
                Bucket=settings.b2_bucket_name,
                Delete={"Objects": batch, "Quiet": True},
            )
            deleted += len(batch)
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 delete failed for '{prefix}': {e}") from e
    _invalidate_list_cache()
    return deleted


def get_play_url(key: str, expires_in: int = 3600) -> str:
    """Presigned GET URL for inline playback/streaming (no forced download).

    Distinct from `b2_client.get_presigned_url`, which forces
    ``Content-Disposition: attachment``; an <audio> element needs the object
    served inline. Raises RuntimeError on failure.
    """
    client = get_s3_client()
    try:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.b2_bucket_name, "Key": key},
            ExpiresIn=expires_in,
        )
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 presign failed for '{key}': {e}") from e

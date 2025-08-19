# gcs.py
from datetime import timedelta
from typing import Optional
import base64, json, os, mimetypes

from google.cloud import storage
from google.oauth2 import service_account
from config import settings

def _build_client() -> storage.Client:
    b64 = os.getenv("GCS_SA_JSON_B64")
    if b64:
        info = json.loads(base64.b64decode(b64))
        creds = service_account.Credentials.from_service_account_info(info)
        return storage.Client(credentials=creds, project=info.get("project_id"))

    raw = os.getenv("GCS_SA_JSON")
    if raw:
        info = json.loads(raw)
        creds = service_account.Credentials.from_service_account_info(info)
        return storage.Client(credentials=creds, project=info.get("project_id"))

    project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
    return storage.Client(project=project)


def make_object_name(session_id: int) -> str:
    return f"{settings.GCS_PREFIX.strip('/')}/{session_id}/cv.pdf"

def upload_fileobj(fileobj, bucket_name: str, object_name: str, content_type: Optional[str] = None):
    client = _build_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)

    try:
        fileobj.seek(0)
    except Exception:
        pass

    ct = content_type or mimetypes.guess_type(object_name)[0] or "application/pdf"
    blob.cache_control = "public, max-age=0, no-cache"
    blob.upload_from_file(fileobj, content_type=ct)

def generate_signed_url(bucket_name: str, object_name: str, expires_minutes: int = 15) -> str:
    client = _build_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    return blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=expires_minutes),
        method="GET",
        response_disposition="inline",
        response_type="application/pdf",
    )

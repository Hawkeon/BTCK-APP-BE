import os
import uuid
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings


class StorageService:
    """S3-compatible object storage service with local fallback."""

    def __init__(self):
        self.use_s3 = bool(
            settings.effective_s3_key_id
            and settings.effective_s3_secret
            and (settings.S3_BUCKET or settings.MINIO_BUCKET)
        )
        if self.use_s3:
            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.effective_s3_key_id,
                aws_secret_access_key=settings.effective_s3_secret,
                endpoint_url=settings.effective_s3_endpoint,
                region_name=settings.S3_REGION,
            )
            self.bucket = settings.S3_BUCKET or settings.MINIO_BUCKET
        else:
            self.local_path = "/app/uploads"

    def _generate_filename(self, original_filename: str, folder: str) -> str:
        ext = original_filename.split(".")[-1] if "." in original_filename else "png"
        unique_name = f"{uuid.uuid4().hex[:8]}.{ext}"
        return f"{folder}/{unique_name}"

    async def upload_image(
        self, file_content: bytes, filename: str, folder: str = "avatars"
    ) -> str:
        """Upload image and return URL."""
        key = self._generate_filename(filename, folder)

        if self.use_s3:
            try:
                self.s3_client.put_object(
                    Bucket=self.bucket,
                    Key=key,
                    Body=file_content,
                    ContentType=self._detect_content_type(filename),
                )
                if settings.effective_s3_endpoint:
                    return f"{settings.effective_s3_endpoint}/{self.bucket}/{key}"
                return f"https://{self.bucket}.s3.{settings.S3_REGION}.amazonaws.com/{key}"
            except ClientError as e:
                raise ValueError(f"Failed to upload to S3: {e}")
        else:
            local_dir = os.path.join(self.local_path, folder)
            os.makedirs(local_dir, exist_ok=True)
            local_path = os.path.join(local_dir, os.path.basename(key))
            with open(local_path, "wb") as f:
                f.write(file_content)
            return f"/uploads/{folder}/{os.path.basename(key)}"

    def delete_image(self, image_url: str) -> bool:
        """Delete image by URL. Returns True if successful."""
        if not image_url:
            return True

        if self.use_s3:
            try:
                key = self._extract_s3_key(image_url)
                if key:
                    self.s3_client.delete_object(Bucket=self.bucket, Key=key)
                    return True
            except ClientError:
                return False
        else:
            if image_url.startswith("/uploads"):
                local_path = os.path.join(self.local_path, image_url.lstrip("/uploads/"))
                if os.path.exists(local_path):
                    os.remove(local_path)
                    return True
        return False

    def _extract_s3_key(self, url: str) -> Optional[str]:
        """Extract S3 key from URL."""
        endpoint = settings.effective_s3_endpoint
        if endpoint and endpoint in url:
            return url.split(endpoint)[1].lstrip("/")
        if f"{self.bucket}.s3" in url:
            parts = url.split(".s3.")
            if len(parts) > 1:
                return parts[1].split("/", 1)[1] if "/" in parts[1] else None
        return None

    def _detect_content_type(self, filename: str) -> str:
        ext = filename.lower().split(".")[-1] if "." in filename else ""
        content_types = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp",
        }
        return content_types.get(ext, "application/octet-stream")


storage_service = StorageService()
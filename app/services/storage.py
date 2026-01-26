import boto3
from botocore.config import Config
from typing import Optional
import httpx

from app.config import settings


class StorageService:
    """Cloudflare R2 storage service."""

    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.R2_ACCESS_KEY,
            aws_secret_access_key=settings.R2_SECRET_KEY,
            config=Config(signature_version="s3v4"),
        )
        self.bucket = settings.R2_BUCKET_NAME
        self.public_url = settings.R2_PUBLIC_URL

    async def upload(
        self,
        key: str,
        content: bytes,
        content_type: str = "image/jpeg",
    ) -> str:
        """Upload file to R2 storage."""
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=content,
                ContentType=content_type,
            )

            if self.public_url:
                return f"{self.public_url}/{key}"
            return f"https://{self.bucket}.{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com/{key}"
        except Exception as e:
            # Fallback for development - return placeholder URL
            print(f"Storage upload error: {e}")
            return f"https://images.keroxio.fr/{key}"

    async def delete(self, key: str) -> bool:
        """Delete file from R2 storage."""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except Exception as e:
            print(f"Storage delete error: {e}")
            return False

    async def get_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
    ) -> str:
        """Generate a presigned URL for direct upload."""
        try:
            url = self.client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": key,
                },
                ExpiresIn=expiration,
            )
            return url
        except Exception as e:
            print(f"Presigned URL error: {e}")
            return ""

    async def download(self, key: str) -> Optional[bytes]:
        """Download file from R2 storage."""
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except Exception as e:
            print(f"Storage download error: {e}")
            return None

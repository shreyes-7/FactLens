"""
Supabase Storage client for FactLens.
Handles private document uploads, downloads, and canonical path structuring.
"""

import logging
from typing import Any
import httpx

from backend.app.config import Settings, get_settings

logger = logging.getLogger("factlens.storage")


class SupabaseStorageClient:
    """HTTP client for Supabase Storage REST API."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if not self.settings.supabase_url:
            raise ValueError("SUPABASE_URL is required for Supabase Storage.")
        if not self.settings.supabase_service_role_key:
            raise ValueError("SUPABASE_SERVICE_ROLE_KEY is required for Supabase Storage.")

        self.base_url = self.settings.supabase_url.rstrip("/")
        self.bucket = self.settings.supabase_storage_bucket or "documents"
        self._headers = {
            "Authorization": f"Bearer {self.settings.supabase_service_role_key}",
            "apikey": self.settings.supabase_service_role_key,
        }

    @staticmethod
    def get_canonical_path(dataset_id: str, document_id: str, filename: str) -> str:
        """
        Build canonical storage path according to FactLens architecture:
        documents/{dataset_id}/{document_id}/{filename}
        """
        clean_filename = filename.replace("\\", "/").split("/")[-1]
        return f"{dataset_id}/{document_id}/{clean_filename}"

    async def ensure_bucket_exists(self, bucket_name: str | None = None) -> None:
        """Verify the storage bucket exists, or create it as a private bucket."""
        target_bucket = bucket_name or self.bucket
        list_url = f"{self.base_url}/storage/v1/bucket"

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(list_url, headers=self._headers)
            if resp.status_code == 200:
                buckets = [b["id"] for b in resp.json()]
                if target_bucket in buckets:
                    return

            # Bucket does not exist, create it
            create_url = f"{self.base_url}/storage/v1/bucket"
            payload = {
                "id": target_bucket,
                "name": target_bucket,
                "public": False,
            }
            create_resp = await client.post(create_url, headers=self._headers, json=payload)
            if create_resp.status_code not in (200, 201):
                logger.warning(
                    "Could not create storage bucket '%s': %s",
                    target_bucket,
                    create_resp.text[:200],
                )

    async def upload_file(
        self,
        file_bytes: bytes,
        storage_path: str,
        content_type: str = "application/pdf",
    ) -> str:
        """
        Upload binary file to Supabase Storage with upsert enabled.
        Returns the relative storage key.
        """
        # Ensure clean path without leading slashes
        clean_path = storage_path.lstrip("/")
        url = f"{self.base_url}/storage/v1/object/{self.bucket}/{clean_path}"

        headers = {
            **self._headers,
            "Content-Type": content_type,
            "x-upsert": "true",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, content=file_bytes)
            if resp.status_code not in (200, 201):
                raise RuntimeError(
                    f"Supabase Storage upload failed ({resp.status_code}): {resp.text[:200]}"
                )

        logger.info("Successfully uploaded file to '%s/%s'", self.bucket, clean_path)
        return f"{self.bucket}/{clean_path}"

    async def download_file(self, storage_path: str) -> bytes:
        """Download binary file from Supabase Storage."""
        clean_path = storage_path.lstrip("/")
        if clean_path.startswith(f"{self.bucket}/"):
            clean_path = clean_path[len(self.bucket) + 1 :]

        url = f"{self.base_url}/storage/v1/object/{self.bucket}/{clean_path}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(url, headers=self._headers)
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Supabase Storage download failed ({resp.status_code}): {resp.text[:200]}"
                )
            return resp.content

    async def delete_file(self, storage_path: str) -> bool:
        """Delete file from Supabase Storage."""
        clean_path = storage_path.lstrip("/")
        if clean_path.startswith(f"{self.bucket}/"):
            clean_path = clean_path[len(self.bucket) + 1 :]

        url = f"{self.base_url}/storage/v1/object/{self.bucket}/{clean_path}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.delete(url, headers=self._headers)
            return resp.status_code == 200

"""Azure Blob Storage adapter — upload and download resume files.

Design spec Section 7.2:
  - resumes-raw container: resumes-raw/{job_id}/{safe_filename}
  - reports container: reports/{job_id}/report.json
"""

from __future__ import annotations

import logging
from typing import Any

from backend.app.config import Settings

logger = logging.getLogger(__name__)


class BlobStorageAdapter:
    """Wraps Azure Blob Storage for resume and report file operations."""

    def __init__(self, settings: Settings) -> None:
        self._connection_string = settings.storage_connection_string
        self._account_name = settings.storage_account_name
        self._client: Any | None = None

    async def upload_resume(
        self,
        job_id: str,
        safe_filename: str,
        data: bytes,
        *,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
        client: Any | None = None,
    ) -> str:
        """Upload a resume blob and return the blob path."""
        blob_path = f"resumes-raw/{job_id}/{safe_filename}"
        container = await self._get_container("resumes-raw", client)

        from azure.storage.blob import ContentSettings
        await container.upload_blob(
            name=f"{job_id}/{safe_filename}",
            data=data,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
            metadata=metadata,
        )
        logger.info("Uploaded resume to %s", blob_path)
        return blob_path

    async def download_resume(
        self,
        blob_path: str,
        *,
        client: Any | None = None,
    ) -> bytes:
        """Download a resume blob by path."""
        # Parse container and blob name from path like "resumes-raw/{job_id}/{file}"
        parts = blob_path.split("/", 1)
        container_name = parts[0]
        blob_name = parts[1] if len(parts) > 1 else ""

        container = await self._get_container(container_name, client)
        blob_client = container.get_blob_client(blob_name)

        stream = await blob_client.download_blob()
        data = await stream.readall()
        logger.info("Downloaded blob %s (%d bytes)", blob_path, len(data))
        return data

    async def upload_report(
        self,
        job_id: str,
        report_json: str,
        *,
        client: Any | None = None,
    ) -> str:
        """Upload a report JSON blob."""
        blob_path = f"reports/{job_id}/report.json"
        container = await self._get_container("reports", client)

        from azure.storage.blob import ContentSettings
        await container.upload_blob(
            name=f"{job_id}/report.json",
            data=report_json.encode("utf-8"),
            overwrite=True,
            content_settings=ContentSettings(content_type="application/json"),
        )
        logger.info("Uploaded report to %s", blob_path)
        return blob_path

    async def _get_container(self, container_name: str, client: Any | None = None) -> Any:
        if client is not None:
            # Test context: client is already a container mock.
            return client
        blob_client = await self._get_client()
        return blob_client.get_container_client(container_name)

    async def _get_client(self) -> Any:
        if self._client is None:
            from azure.storage.blob.aio import BlobServiceClient

            if self._connection_string:
                self._client = BlobServiceClient.from_connection_string(self._connection_string)
            else:
                raise ValueError("Storage connection string or account name required")
        return self._client

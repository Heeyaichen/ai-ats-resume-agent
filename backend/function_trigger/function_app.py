"""Azure Function blob trigger — enqueues Service Bus jobs.

Design spec Section 5.4:
- Parse job_id from blob path resumes-raw/{job_id}/{safe_filename}.
- Validate blob metadata job_id matches the path.
- Read the jobs document by job_id.
- Send {job_id, blob_path, jd_text} to the Service Bus queue.
- Use managed identity where supported.
- Never query jobs by filename.

Uses the Azure Functions Python v2 decorator-based model.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Callable, Awaitable

import azure.functions as func

logger = logging.getLogger(__name__)

app = func.FunctionApp()

_QUEUE_NAME = os.environ.get("SERVICEBUS_QUEUE_NAME", "ats-agent-jobs")


def parse_job_id_from_path(blob_path: str) -> str | None:
    """Extract job_id from a blob path like resumes-raw/{job_id}/{filename}.

    Returns None if the path doesn't match the expected pattern.
    """
    parts = blob_path.replace("\\", "/").split("/")
    # Expected: ["resumes-raw", "{job_id}", "{filename}"]
    if len(parts) >= 3 and parts[0] == "resumes-raw" and parts[1]:
        return parts[1]
    return None


async def handle_blob_trigger(
    blob_path: str,
    blob_metadata: dict[str, str],
    blob_uri: str,
    *,
    get_job: Callable[[str], Awaitable[Any | None]] | None = None,
) -> dict[str, Any]:
    """Core logic for the blob trigger, extracted for testability.

    Args:
        blob_path: The blob path, e.g. "{job_id}/{filename}" or
            "resumes-raw/{job_id}/{filename}".
        blob_metadata: Blob metadata dict (should include job_id).
        blob_uri: Full blob URI for logging.
        get_job: Optional async callable(job_id) -> JobRecord | None.
            If not provided, reads from Cosmos using Settings.

    Returns:
        The Service Bus message body dict.

    Raises:
        ValueError: If path parsing fails or metadata mismatch.
        LookupError: If the job is not found in Cosmos.
    """
    # Normalize to full path.
    full_path = f"resumes-raw/{blob_path}" if not blob_path.startswith("resumes-raw/") else blob_path

    job_id = parse_job_id_from_path(full_path)
    if job_id is None:
        raise ValueError(f"Cannot parse job_id from blob path: {full_path}")

    # Validate metadata matches path.
    metadata_job_id = blob_metadata.get("job_id")
    if metadata_job_id and metadata_job_id != job_id:
        raise ValueError(
            f"Metadata job_id mismatch: metadata={metadata_job_id}, path={job_id}"
        )

    # Read job document.
    if get_job is not None:
        job = await get_job(job_id)
    else:
        raise RuntimeError(
            "handle_blob_trigger requires a get_job callable. "
            "Callers in the Function must pass one explicitly."
        )

    if job is None:
        raise LookupError(f"Job {job_id} not found in Cosmos DB.")

    message_body = {
        "job_id": job_id,
        "blob_path": full_path,
        "jd_text": job.job_description,
    }

    logger.info(
        "Blob trigger: parsed job_id=%s from path=%s, sending to queue",
        job_id, full_path,
    )

    return message_body


async def send_to_service_bus(message_body: dict[str, Any]) -> None:
    """Send a message to the Service Bus queue.

    Uses managed identity when SERVICEBUS_CONNECTION_STRING is not set
    and SERVICEBUS_FULLY_QUALIFIED_NAMESPACE is set instead.
    """
    from azure.servicebus.aio import ServiceBusClient
    from azure.servicebus import ServiceBusMessage

    conn_str = os.environ.get("SERVICEBUS_CONNECTION_STRING")
    namespace = os.environ.get("SERVICEBUS_FULLY_QUALIFIED_NAMESPACE")

    message = ServiceBusMessage(
        body=json.dumps(message_body),
        message_id=message_body["job_id"],
    )

    if conn_str:
        async with ServiceBusClient.from_connection_string(conn_str) as client:
            sender = client.get_queue_sender(queue_name=_QUEUE_NAME)
            async with sender:
                await sender.send_messages(message)
    elif namespace:
        from azure.identity.aio import DefaultAzureCredential
        credential = DefaultAzureCredential()
        try:
            async with ServiceBusClient(
                fully_qualified_namespace=namespace,
                credential=credential,
            ) as client:
                sender = client.get_queue_sender(queue_name=_QUEUE_NAME)
                async with sender:
                    await sender.send_messages(message)
        finally:
            await credential.close()
    else:
        raise RuntimeError(
            "Neither SERVICEBUS_CONNECTION_STRING nor "
            "SERVICEBUS_FULLY_QUALIFIED_NAMESPACE is configured."
        )

    logger.info("Sent job %s to Service Bus queue %s", message_body["job_id"], _QUEUE_NAME)


@app.blob_trigger(
    arg_name="blob",
    path="resumes-raw/{job_id}/{name}",
    connection="AzureWebJobsStorage",
)
@app.service_bus_queue_output(
    arg_name="msg",
    queue_name="ats-agent-jobs",
    connection="ServiceBusConnection",
)
def on_resume_upload(blob: func.InputStream, msg: func.Out[str]) -> None:
    """Blob trigger: fires when a new resume is uploaded.

    Binding pattern: resumes-raw/{job_id}/{name}
    The runtime injects the {job_id} and {name} from the path.

    Validates metadata, reads the job from Cosmos, and writes
    the Service Bus message via the output binding.
    """
    blob_path = blob.name  # e.g. "resumes-raw/{job_id}/{filename}"
    blob_metadata = blob.metadata or {}

    logger.info("Blob trigger fired for path: %s", blob_path)

    # Determine job_id from path parsing (the Python v2 model does not expose
    # trigger_metadata on InputStream, so we parse from the blob path).
    job_id = parse_job_id_from_path(blob_path)
    if job_id is None:
        logger.error("Cannot determine job_id from blob: %s", blob_path)
        return

    # Validate metadata job_id matches path-derived job_id.
    metadata_job_id = blob_metadata.get("job_id", "")
    if metadata_job_id and metadata_job_id != job_id:
        logger.error(
            "Metadata job_id mismatch: metadata=%s, path=%s. Skipping.",
            metadata_job_id, job_id,
        )
        return

    # Run async logic synchronously within the Function.
    loop = asyncio.new_event_loop()
    try:
        message_body = loop.run_until_complete(_get_job_and_build_message(job_id, blob_path))
    finally:
        loop.close()

    if message_body is not None:
        msg.set(json.dumps(message_body))
        logger.info("Enqueued job %s to Service Bus", job_id)


async def _get_job_and_build_message(job_id: str, blob_path: str) -> dict[str, Any] | None:
    """Read the job from Cosmos using the azure-cosmos SDK directly.

    Avoids importing backend.app.* (which depends on pydantic) so the
    Function can run with its minimal requirements.txt.
    """
    cosmos_endpoint = os.environ.get("COSMOS_ENDPOINT")
    cosmos_key = os.environ.get("COSMOS_KEY")
    cosmos_db = os.environ.get("COSMOS_DATABASE_NAME", "ats-db")

    if not cosmos_endpoint or not cosmos_key:
        logger.error("COSMOS_ENDPOINT / COSMOS_KEY not configured. Skipping.")
        return None

    from azure.cosmos.aio import CosmosClient

    async with CosmosClient(cosmos_endpoint, credential=cosmos_key) as client:
        database = client.get_database_client(cosmos_db)
        container = database.get_container_client("jobs")
        try:
            job_doc = await container.read_item(item=job_id, partition_key=job_id)
        except Exception as exc:
            logger.error("Job %s not found in Cosmos DB: %s", job_id, exc)
            return None

    jd_text = job_doc.get("job_description", "")
    if not jd_text:
        logger.error("Job %s has no job_description. Skipping.", job_id)
        return None

    return {
        "job_id": job_id,
        "blob_path": blob_path,
        "jd_text": jd_text,
    }

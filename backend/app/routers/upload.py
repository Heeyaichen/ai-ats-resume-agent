"""Upload router — POST /api/upload.

Design spec Section 5.1:
- Auth: Entra ID bearer token required (placeholder for now).
- Request: multipart form data with file and job_description.
- Validation: .pdf/.docx only, max 10 MB, JD non-empty and < 50 000 chars.
- Creates job record, uploads blob, returns {job_id, status: queued}.
"""

from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from backend.app.models.jobs import JobRecord, JobStatus, UploadResponse

router = APIRouter()

# Only allow filenames with safe characters.
_UNSAFE_CHARS = re.compile(r"[^\w.\-]")


def _sanitize_filename(filename: str) -> str:
    """Strip path components and replace unsafe characters."""
    name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    name = _UNSAFE_CHARS.sub("_", name)
    return name or "upload"


@router.post("/api/upload", response_model=UploadResponse)
async def upload(
    request: Request,
    file: UploadFile = File(...),
    job_description: str = Form(...),
) -> UploadResponse:
    settings = request.app.state.settings

    # ── Validate job description ────────────────────────────────
    if not job_description.strip():
        raise HTTPException(status_code=400, detail="Job description must not be empty.")
    if len(job_description) > settings.max_jd_length:
        raise HTTPException(
            status_code=400,
            detail=f"Job description exceeds {settings.max_jd_length} characters.",
        )

    # ── Validate file extension ─────────────────────────────────
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if f".{ext}" not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '.{ext}'. Allowed: {', '.join(settings.allowed_extensions)}.",
        )

    # ── Validate file size ──────────────────────────────────────
    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds {settings.max_upload_size_bytes // (1024 * 1024)} MB limit.",
        )

    # ── Create job record ───────────────────────────────────────
    job_id = uuid.uuid4().hex
    safe_filename = _sanitize_filename(filename)
    blob_path = f"resumes-raw/{job_id}/{safe_filename}"

    job = JobRecord(
        id=job_id,
        status=JobStatus.QUEUED,
        filename=safe_filename,
        blob_path=blob_path,
        job_description=job_description,
        uploaded_by="anonymous",  # Will be replaced with Entra ID claims in Phase 8.
    )

    # ── Persist via adapters ───────────────────────────────────
    # Always store in memory as fallback for score lookup.
    job_store: dict = request.app.state.job_store
    job_store[job_id] = job

    # Upload blob if blob adapter is available.
    blob_adapter = getattr(request.app.state, "blob_adapter", None)
    if blob_adapter is not None:
        await blob_adapter.upload_resume(
            job_id=job_id,
            safe_filename=safe_filename,
            data=content,
            content_type=file.content_type or "application/octet-stream",
            metadata={
                "job_id": job_id,
                "original_filename": filename,
                "uploaded_by": "anonymous",
            },
        )

    # Persist job to Cosmos DB if adapter is available.
    cosmos_adapter = getattr(request.app.state, "cosmos_adapter", None)
    if cosmos_adapter is not None:
        await cosmos_adapter.upsert_job(job)

    return UploadResponse(job_id=job_id, status=JobStatus.QUEUED)

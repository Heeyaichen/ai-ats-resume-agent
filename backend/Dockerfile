# Multi-target Dockerfile for ATS Agent backend.
# Targets:
#   api     — FastAPI uvicorn server (default)
#   worker  — Service Bus worker loop

FROM python:3.11-slim AS base

WORKDIR /app

# Install Python dependencies.
COPY requirements.in .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.in

# Copy application code as the 'backend' package.
# All backend imports use 'from backend.app.xxx import ...'.
# WORKDIR is /app, so /app/backend/app/ resolves correctly.
COPY __init__.py backend/__init__.py
COPY app/ backend/app/
COPY run_worker.py backend/run_worker.py
COPY function_trigger/ backend/function_trigger/

# ── API target (default) ────────────────────────────────────────
FROM base AS api
EXPOSE 8000
CMD ["uvicorn", "backend.app.main:create_app", \
     "--host", "0.0.0.0", "--port", "8000", "--factory"]

# ── Worker target ───────────────────────────────────────────────
FROM base AS worker
CMD ["python", "-m", "backend.run_worker"]

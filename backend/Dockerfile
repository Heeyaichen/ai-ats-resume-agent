FROM python:3.11-slim AS base

WORKDIR /app

# Install build dependencies.
COPY requirements.in .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.in

# Copy application code.
COPY app/ app/
COPY function_trigger/ function_trigger/

# Expose uvicorn on port 8000.
EXPOSE 8000

CMD ["uvicorn", "app.main:create_app", "--host", "0.0.0.0", "--port", "8000", "--factory"]

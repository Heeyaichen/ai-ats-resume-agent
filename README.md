# AI-ATS-RESUME-AGENT

AI-powered Applicant Tracking System (ATS) Resume Screening Agent. Accepts PDF/DOCX resume uploads and job descriptions, runs a guarded agentic reasoning loop using Azure OpenAI function calling, streams agent progress via Server-Sent Events (SSE), and produces recruiter-readable ATS reports.

## Architecture Overview

```
SPA (React) → CDN → Static Web Apps
                    ↓
              API Management (JWT, rate limit) [dev only]
                    ↓
              FastAPI (Container Apps) → Service Bus (direct enqueue)
                    ↑         ↓
              SSE stream  Blob Storage → Function (backup trigger)
                    ↑                       ↓
              Worker (guarded agent loop) ←─┘
                              ↓
                    Azure OpenAI + 9 tool functions
                    (Document Intelligence, Translator, AI Language,
                     Content Safety, Embeddings, AI Search, Cosmos DB)
```

**Data flow:**

1. Recruiter signs in via Microsoft Entra ID.
2. SPA sends `POST /api/upload` (through APIM in dev; directly in cost-optimized production) with file + job description.
3. FastAPI validates, creates a job record, uploads the resume blob, **enqueues a Service Bus message directly**.
4. The blob trigger Function serves as a backup path (Consumption plan blob polling can take minutes).
5. The worker receives the message, runs the guarded agent, streams SSE events, persists results.
6. The frontend uses SSE for real-time progress and polls `GET /api/score/{job_id}` as a completion fallback.

## What Makes This a Guarded Agent

This is **not a hardcoded pipeline** and **not an unrestricted AI agent**. The system uses a **guarded agent** architecture:

- **The model chooses tools and arguments** through Azure OpenAI function calling each turn.
- **The runtime enforces safety and completeness invariants** the model cannot override:

  - `extract_resume_text` must complete before any tool needing resume text.
  - `check_pii_and_safety` must complete before scoring, embedding, or summary.
  - Non-English resumes require translation or human review flag.
  - `score_resume`, `compute_semantic_similarity`, `generate_fit_summary` must all complete.
  - Auto-flag for human review when: score < 30, confidence < 0.6, safety flagged, extraction confidence low, max iterations hit (12), or missing required fields.
  - Max 2 retries per tool call. Max 12 iterations per job.
  - All tool I/O validated against Pydantic models.
  - Raw resume text never persisted in logs or traces.

## The 9 Canonical Agent Tools

| # | Tool | Azure Service | Purpose |
|---|------|---------------|---------|
| 1 | `extract_resume_text` | Document Intelligence | Extract text from PDF/DOCX |
| 2 | `detect_language` | Translator | Detect resume language |
| 3 | `translate_text` | Translator | Translate non-English text to English |
| 4 | `check_pii_and_safety` | AI Language + Content Safety | PII redaction + harmful content check |
| 5 | `score_resume` | Azure OpenAI | Score 0–100 (40 keyword + 30 experience + 30 skills) |
| 6 | `compute_semantic_similarity` | OpenAI Embeddings + Redis | JD/resume semantic similarity with cache |
| 7 | `search_similar_candidates` | AI Search | Vector search across historical embeddings |
| 8 | `flag_for_human_review` | Cosmos DB | Write review flag for low scores or issues |
| 9 | `generate_fit_summary` | Azure OpenAI | 2–3 sentence plain-English recruiter summary |

> `get_embedding` and `search_similar_jds` are obsolete aliases. The canonical names above are the only valid tool identifiers.

## Setup Prerequisites

- **Azure CLI** — `az` command-line tool, logged in
- **Terraform** >= 1.6
- **Docker** — for building backend images
- **Node.js** 20+
- **Python** 3.11+
- **GitHub OIDC** — Federated identity configured for GitHub Actions (see [Terraform deployment steps](#terraform-deployment))

## Local Development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.in

# Required environment variable (placeholder for local testing):
export AZURE_OPENAI_ENDPOINT="https://placeholder.openai.azure.com/"

# Run the API (from repo root):
uvicorn backend.app.main:create_app --factory --reload --port 8000

# Run tests (all Azure/OpenAI clients are mocked):
pytest tests/ -v
```

### Frontend

```bash
cd frontend
npm install
npm run dev          # Vite dev server with API proxy to localhost:8000
npm run typecheck    # TypeScript check
npm test             # Vitest (22 tests)
npm run build        # Production build
```

### Worker (local)

```bash
cd backend
# The worker requires a Service Bus connection for production mode.
# For local testing, use the async iterator interface in tests.
pytest tests/test_worker.py -v
```

## Terraform Deployment

### Deployment Order

1. **Configure Azure OIDC** — Create an Entra ID application registration and federated credential for your GitHub repo.
2. **Bootstrap Terraform state storage** — Create a storage account and container for remote state before the first CI `terraform init`.
3. **Configure GitHub secrets/variables** — See the required secrets table below.
4. **Run Terraform plan/apply** — CI runs this automatically on push to `main`. For first-time setup, run manually.
5. **Build/deploy API, worker, Function, frontend** — CI deploys these automatically after Terraform.

### Bootstrap Terraform Remote State

Before the first CI `terraform init`, create the state storage:

```bash
RESOURCE_GROUP="tfstate-rg"
STORAGE_ACCOUNT="tfstate$RANDOM"
az group create --name $RESOURCE_GROUP --location swedencentral
az storage account create --name $STORAGE_ACCOUNT --resource-group $RESOURCE_GROUP --sku Standard_LRS
az storage container create --name tfstate --account-name $STORAGE_ACCOUNT
```

Then set `TF_STATE_RESOURCE_GROUP`, `TF_STATE_STORAGE_ACCOUNT`, `TF_STATE_CONTAINER` as GitHub secrets.

### Configure GitHub OIDC

1. Create an Entra ID application registration and federated credential for your GitHub repo.
2. Note the `client_id`, `tenant_id`, and `subscription_id`.
3. Add them as GitHub repository secrets: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`.

### Deploy Infrastructure

```bash
cd infra

# Dev environment
terraform init \
  -backend-config="resource_group_name=<rg>" \
  -backend-config="storage_account_name=<sa>" \
  -backend-config="container_name=tfstate" \
  -backend-config="key=dev.tfstate"
terraform apply -var-file=env/dev.tfvars

# Prod environment
terraform init \
  -backend-config="resource_group_name=<rg>" \
  -backend-config="storage_account_name=<sa>" \
  -backend-config="container_name=tfstate" \
  -backend-config="key=prod.tfstate"
terraform apply -var-file=env/prod.tfvars
```

### Required GitHub Environments

| Environment | Purpose |
|-------------|---------|
| `dev` | PR validation (terraform plan) |
| `production` | Main-branch deploys (terraform apply, backend/frontend deploy) |

### Required GitHub Secrets

| Secret | Description |
|--------|-------------|
| `AZURE_CLIENT_ID` | Entra ID app registration client ID (OIDC) |
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID |
| `ACR_NAME` | Azure Container Registry name (no `.azurecr.io`) |
| `API_CONTAINER_APP_NAME` | FastAPI Container App name |
| `WORKER_CONTAINER_APP_NAME` | Worker Container App name |
| `FUNCTION_APP_NAME` | Function App name |
| `RESOURCE_GROUP_NAME` | Resource group containing compute resources |
| `AZURE_STATIC_WEB_APPS_API_TOKEN` | Static Web Apps deployment token |
| `TF_STATE_RESOURCE_GROUP` | Resource group for Terraform state storage account |
| `TF_STATE_STORAGE_ACCOUNT` | Storage account name for Terraform remote state |
| `TF_STATE_CONTAINER` | Blob container name for Terraform state files |

### API Management Note

APIM is provisioned by Terraform (Developer SKU in dev) but does not yet enforce API policy (JWT validation, rate limiting, request forwarding to the FastAPI backend). The FastAPI Container App is publicly accessible via its external ingress. APIM policy configuration is a follow-up task after initial deployment.

### Cost-Optimized Production Constraints

The production environment is configured for cost control on a subscription with limited quotas. The following constraints apply:

| Constraint | Dev | Cost-Optimized Production | Reason |
|------------|-----|---------------------------|--------|
| Azure OpenAI | Dedicated (`ats-agent-dev-openai`) | Shares dev OpenAI account | 1 OpenAI account per subscription |
| Container Apps Environment | Dedicated (`ats-agent-dev-cae`) | Shares dev CAE | 1 CAE per region per subscription |
| API Management | Enabled (Developer SKU) | Disabled (`enable_apim=false`) | APIM creation blocked on free trial |
| AI Search | Basic SKU | Free SKU | Basic unavailable in swedencentral |
| Function trigger latency | Consumption (2–10 min scan) | Direct SB enqueue bypasses delay | Blob trigger is backup path only |

These are controlled via `infra/env/prod.tfvars` toggles: `use_existing_openai`, `existing_cae_id`, `enable_apim`, and `search_sku`. This configuration prioritizes deployability and cost control over full environment isolation. For a production deployment with full isolation, request subscription quota increases or use a pay-as-you-go subscription.

## Environment Variable Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AZURE_OPENAI_ENDPOINT` | Yes | — | Azure OpenAI resource endpoint URL |
| `AZURE_OPENAI_KEY` | No* | — | API key (omit when using managed identity) |
| `CHAT_MODEL_DEPLOYMENT_NAME` | No | `gpt-4o` | Chat model deployment name |
| `EMBEDDING_MODEL_DEPLOYMENT_NAME` | No | `text-embedding-ada-002` | Embedding model deployment name |
| `OPENAI_API_VERSION` | No | `2024-06-01` | Azure OpenAI API version |
| `DOCUMENT_INTELLIGENCE_ENDPOINT` | No | — | Document Intelligence endpoint |
| `TRANSLATOR_ENDPOINT` | No | — | Translator endpoint |
| `TRANSLATOR_REGION` | No | — | Translator region (e.g. `swedencentral`) |
| `LANGUAGE_ENDPOINT` | No | — | AI Language endpoint |
| `CONTENT_SAFETY_ENDPOINT` | No | — | Content Safety endpoint |
| `COSMOS_ENDPOINT` | No | — | Cosmos DB account endpoint |
| `COSMOS_KEY` | No | — | Cosmos DB primary key |
| `COSMOS_DATABASE_NAME` | No | `ats-db` | Cosmos database name |
| `STORAGE_CONNECTION_STRING` | No | — | Blob Storage connection string |
| `REDIS_URL` | No | — | Redis connection URL |
| `SEARCH_ENDPOINT` | No | — | AI Search endpoint |
| `SEARCH_INDEX_NAME` | No | `candidate-embeddings` | AI Search index name |
| `SERVICEBUS_CONNECTION_STRING` | No | — | Service Bus connection string |
| `SERVICEBUS_QUEUE_NAME` | No | `ats-agent-jobs` | Service Bus queue name |
| `AGENT_MAX_ITERATIONS` | No | `12` | Maximum agent loop iterations |
| `AGENT_MAX_RETRIES_PER_TOOL` | No | `2` | Max retries per tool call |

*\* Required unless using managed identity.*

## API Reference

### Health Check

```bash
curl http://localhost:8000/api/health
```

```json
{ "status": "ok", "version": "0.1.0", "environment": "dev" }
```

### Upload Resume

```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@resume.pdf" \
  -F "job_description=Senior Python developer with 5 years experience"
```

```json
{ "job_id": "abc123...", "status": "queued" }
```

### Get Score

```bash
curl http://localhost:8000/api/score/{job_id}
```

### SSE Stream

```bash
curl -N http://localhost:8000/api/score/{job_id}/stream
```

Events are framed as `data: {json}\n\n` with types: `tool_call`, `tool_result`, `complete`, `error`.

## Security and PII Handling

- **Authentication**: Microsoft Entra ID for SPA sign-in; APIM validates JWT on API requests.
- **PII redaction**: Azure AI Language (not Content Safety) detects and redacts PII before scoring, embeddings, summaries, and traces. Raw text exists only in process memory for the active job.
- **Trace sanitization**: Agent traces store summarized, sanitized outputs only — never raw resume text.
- **File safety**: PDF and DOCX only, 10 MB max, sanitized filenames, stored under `job_id` folders.
- **Retention**: 90-day default for raw resumes, reports, and detailed traces. Blob lifecycle management deletes blobs after 90 days.
- **Secret management**: Managed identity preferred; unavoidable API keys stored in Key Vault with RBAC access.

## Cost Estimate

Approximate monthly cost for low-usage **dev** environment (swedencentral):

| Resource | SKU | Estimated Monthly Cost |
|----------|-----|----------------------|
| Container Apps | 0.5 vCPU, 1 GB × 2 | ~$30 |
| Container Registry | Basic | ~$5 |
| Azure OpenAI | S0, usage-based | ~$20–$100 (varies by usage) |
| Cosmos DB | 400 RU/s autoscale | ~$25 |
| Service Bus | Standard | ~$10 |
| Redis | Basic C0 | ~$20 |
| AI Search | Basic | ~$250 |
| Storage | Standard LRS | ~$2 |
| Key Vault | Standard | ~$1 |
| App Insights | Pay-as-you-go | ~$5 |
| API Management | Developer | Free |
| Static Web Apps | Free | Free |
| Function App | Consumption (Y1) | ~$1 |
| **Total (estimated)** | | **~$370–$470/month** |

> Prod costs are lower than dev due to the cost-optimized production configuration (shared OpenAI, shared CAE, free Search, no APIM). Add Azure budget alerts per environment.

## Troubleshooting

### DeploymentNotFound (Azure OpenAI)

**Symptom**: Backend fails at startup with `DeploymentNotFound` or HTTP 404 when calling Azure OpenAI.

**Cause**: The `AZURE_OPENAI_ENDPOINT` points to a different Azure OpenAI resource than where the model deployments exist. This commonly happens when using an Azure AI Foundry proxy endpoint instead of the direct Azure OpenAI resource endpoint.

**Fix**:
1. Open the Azure OpenAI resource (not Foundry project) in the Azure Portal.
2. Copy the endpoint from the resource's "Keys and Endpoint" page.
3. Ensure `CHAT_MODEL_DEPLOYMENT_NAME` and `EMBEDDING_MODEL_DEPLOYMENT_NAME` match the deployment names shown under "Model deployments".
4. If using Foundry, the endpoint and key may belong to the Foundry-managed OpenAI resource — verify by checking the resource name.

### Service Bus Scaling

**Symptom**: Queue depth grows, messages not consumed.

**Cause**: Worker Container App may have insufficient replicas or the KEDA scale rule is not configured.

**Fix**:
1. Check Container App replica count: `az containerapp show --name <name> --resource-group <rg> --query properties.template.scale`.
2. Add a KEDA scale rule on Service Bus queue depth (max replicas = 10, target queue depth = 5).
3. Check Service Bus queue dead-letter count for messages that exceeded max delivery count (3).
4. Verify the worker process is running and not crash-looping (check Container App logs).

### Content Safety / Language Authentication

**Symptom**: Tool calls to Content Safety or AI Language fail with 401 Unauthorized.

**Cause**: The managed identity or API key does not have the correct RBAC role on the cognitive account.

**Fix**:
1. For managed identity: ensure `Cognitive Services User` role is assigned on the specific cognitive account resource.
2. For API key: verify the key matches the endpoint's resource (check in Azure Portal under "Keys and Endpoint").
3. AI Language is used for PII redaction; Content Safety is used only for harmful-content moderation. These are separate services with separate endpoints.

### SSE Disconnects

**Symptom**: Frontend EventSource closes unexpectedly during agent processing.

**Cause**: 5-minute inactivity timeout, client network change, or load balancer idle timeout.

**Fix**:
1. The backend SSE endpoint has a 5-minute inactivity timeout — if the agent stalls, the connection drops.
2. Ensure APIM or any reverse proxy does not buffer SSE responses (set `Connection: keep-alive` and disable response buffering).
3. The frontend hook (`useSSEStream`) automatically closes the EventSource on terminal events (`complete`, `error`) and on page unload.
4. Check Container App logs for SSE registry errors.

### AI Search Index Issues

**Symptom**: `search_similar_candidates` returns empty results or errors.

**Cause**: The `candidate-embeddings` index does not exist, has wrong vector dimensions, or no documents are indexed.

**Fix**:
1. Verify the index exists: check the AI Search resource in the Azure Portal.
2. Vector dimension must be **1536** for `text-embedding-ada-002`. If the embedding model changes, update both the index schema and Terraform in the same commit.
3. The index requires fields: `id`, `job_id`, `candidate_id`, `document_type`, `score`, `created_at`, `embedding` (vector-search enabled).
4. This tool is **optional** for completion — if skipped, the report shows `similar_candidates: []`.

### Max-Iteration Fallback

**Symptom**: Job completes with `failed_review_required` status and a "max iterations" flag.

**Cause**: The agent loop reached 12 iterations without completing all required milestones (extraction, PII check, scoring, similarity, summary).

**Fix**:
1. Check the agent trace in Cosmos DB `agent_traces` container to see which tools were called and where it got stuck.
2. Common causes: tool retries exhausting the iteration budget, or the model not calling a required tool.
3. The runtime automatically writes a `review_flags` record so a human can review the partial result.
4. If this happens frequently, consider increasing `AGENT_MAX_ITERATIONS` or investigating why specific tools are failing.

## Repository Structure

```
├── .github/workflows/     # CI/CD (terraform.yml, backend.yml, frontend.yml)
├── backend/
│   ├── app/
│   │   ├── agent/         # Agent runtime (runner, policy, memory, executor, registry)
│   │   ├── models/        # Pydantic domain models (9 files)
│   │   ├── routers/       # FastAPI routes (health, upload, score + SSE)
│   │   ├── services/      # Azure service adapters (10 adapters)
│   │   ├── config.py      # pydantic-settings configuration
│   │   ├── logging_config.py
│   │   ├── main.py        # FastAPI app factory
│   │   └── worker.py      # Service Bus worker with retry/dead-letter
│   ├── function_trigger/  # Azure Function blob trigger (requirements.txt)
│   ├── tests/             # pytest suite (150 tests)
│   ├── Dockerfile         # Multi-target: api (uvicorn) and worker
│   ├── run_worker.py      # Worker container entrypoint
│   ├── requirements.in    # FastAPI + worker deps (no azure-functions)
├── frontend/
│   ├── src/
│   │   ├── components/    # React UI components (7 components)
│   │   ├── test/          # Vitest suite (22 tests)
│   │   ├── App.tsx        # MSAL provider wrapper
│   │   ├── Home.tsx       # Main page with state machine
│   │   ├── api.ts         # Axios API client
│   │   ├── authConfig.ts  # MSAL configuration
│   │   ├── types.ts       # TypeScript type definitions
│   │   └── useSSEStream.ts
│   └── package.json
├── infra/
│   ├── modules/           # Terraform modules (storage, ai_services, compute, data, networking, observability, security)
│   ├── env/               # Environment tfvars (dev, prod)
│   └── main.tf            # Root module wiring
├── docs/superpowers/specs/2026-04-08-ats-agent-design.md  # Authoritative design spec
├── implementation_prompt.md  # Original implementation instructions (historical)
└── CLAUDE.md              # Project guidance for AI coding agents
```

## Implementation Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Workspace structure | Done |
| 2 | Backend models, config, logging | Done |
| 3 | Azure service adapters | Done |
| 4 | Agent runtime (registry, memory, policy, executor, runner) | Done |
| 5 | FastAPI upload, score, health, SSE endpoints | Done |
| 6 | Service Bus worker | Done |
| 7 | Azure Function blob trigger | Done |
| 8 | React frontend | Done |
| 9 | Terraform modules | Done |
| 10 | GitHub Actions CI/CD | Done |
| 11 | README | Done |
| 12 | Full local test + Terraform validation | Done |

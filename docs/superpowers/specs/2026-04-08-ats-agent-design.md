# ATS Resume Screening Agent - Production System Design

Date: 2026-04-08
Status: approved design spec for implementation
Source prompt: `implementation_prompt.md`
Target approach: preserve the original Azure-heavy architecture, correct production risks, and remove ambiguity for an AI coding agent.

## 1. Executive Summary

Build a greenfield, production-grade ATS resume screening agent that accepts PDF/DOCX resumes and job descriptions, streams an agent reasoning trace to a React UI, and produces a recruiter-readable ATS report.

The original Claude Sonnet 4.6 prompt is directionally useful but not implementation-safe as written. It asks for a genuinely agentic Azure system, yet also mandates a fixed sequence of actions. It maps PII detection to Azure AI Content Safety even though Microsoft documents PII detection/redaction under Azure AI Language. It also relies on a blob-triggered Function querying Cosmos by filename, which is collision-prone. This spec preserves the original service inventory while correcting those issues.

The target architecture is:

- React 18 + TypeScript + Vite frontend hosted on Azure Static Web Apps, fronted by Azure CDN.
- Azure API Management as the public API ingress, enforcing Microsoft Entra ID JWT validation and rate limiting.
- FastAPI Python 3.11 backend on Azure Container Apps.
- Azure Function blob trigger that enqueues Service Bus jobs.
- Service Bus queue consumed by a Container Apps worker.
- Guarded agent runtime using Azure OpenAI function calling with an explicit tool registry.
- Azure AI Document Intelligence, Translator, Language, Content Safety, OpenAI, AI Search, Redis, Cosmos DB, Blob Storage, Key Vault, Azure Monitor, Application Insights, and Log Analytics.
- Terraform for all infrastructure and GitHub Actions for CI/CD.

## 2. Source Prompt Audit

### 2.1 Extracted Requirements

The source prompt requires the system to:

- Accept resume uploads in PDF or DOCX format and job descriptions from a React UI.
- Use an Azure OpenAI model to decide which tools to call based on observed tool results.
- Expose 9 agent tools for resume text extraction, language detection, translation, PII/safety checks, scoring, semantic similarity, vector search, human review flagging, and fit summary generation.
- Persist structured data in Cosmos DB.
- Store raw resumes and reports in Blob Storage.
- Stream tool calls and tool results to the client via Server-Sent Events.
- Return an ATS report with score, score breakdown, keyword matches, semantic similarity, missing skills, fit explanation, and agent trace.
- Automatically flag low scores, non-English resumes, PII/safety issues, ambiguous job descriptions, tool failures, and low-confidence outputs for human review.
- Provision Azure resources using Terraform.
- Use managed identity, Key Vault, RBAC, and structured observability.

### 2.2 Intended Outcomes

The implemented system must be usable by recruiters and auditable by engineering teams. A successful run starts with a resume/JD upload, streams meaningful agent progress, produces a complete report, persists the report and trace, and fails safely by requiring human review when confidence or safety constraints are not met.

### 2.3 Original Technology Stack

The original prompt requires:

- Frontend: React 18, TypeScript, Vite, Tailwind CSS, Lucide React, Azure Static Web Apps, Azure CDN.
- API and worker: FastAPI, Python 3.11, Azure Container Apps, Azure Container Registry.
- Eventing: Azure Function blob trigger, Azure Service Bus Standard queue.
- AI: Azure OpenAI `gpt-4o`, Azure OpenAI `text-embedding-ada-002`, Azure AI Document Intelligence, Azure AI Translator, Azure AI Content Safety, Azure AI Search.
- Data: Azure Blob Storage, Azure Cosmos DB NoSQL, Azure Cache for Redis.
- Security: Azure Key Vault, system-assigned managed identities, RBAC.
- Observability: Azure Monitor, Application Insights, Log Analytics.
- IaC and CI/CD: Terraform and GitHub Actions.

This spec preserves that inventory and adds Azure AI Language because the PII requirement is otherwise not production-correct.

### 2.4 Architecture Assumptions

The prompt assumes:

- The project is a greenfield implementation.
- Azure is the required cloud provider.
- The app is for internal recruiter users, not anonymous public users.
- Service Bus is the durable work queue.
- The worker can run in the same Container App image as the API or as a separate Container App revision/process.
- Azure OpenAI function calling is the primary agent mechanism.
- The agent trace is a product feature and an audit artifact.
- Job scoring is asynchronous even though the upload endpoint returns synchronously.

### 2.5 Key Gaps and Corrections

| Area | Prompt Issue | Required Correction |
| --- | --- | --- |
| Agent control | Says "not a hardcoded pipeline" but also says "always start" and "always check" several steps. | Use a guarded agent: model chooses tool calls, runtime enforces required milestones and completion policy. |
| PII detection | Maps PII detection to Content Safety. | Use Azure AI Language for PII redaction and Content Safety for harmful-content moderation. |
| Queue handoff | Function queries Cosmos by filename after blob creation. | Store blobs under `resumes-raw/{job_id}/{safe_filename}` and derive `job_id` from the blob path. |
| Tool naming | Mentions `get_embedding` and `search_similar_jds` in one section, then uses `compute_semantic_similarity` and `search_similar_candidates` later. | Canonicalize on the 9-tool schema defined in Section 4. |
| Search object | Prompt alternates between job description embeddings and similar candidates. | Use AI Search for candidate/report benchmarking in v1; store JD/resume embeddings with clear document type metadata. |
| Auth | Mentions JWT policy but does not define identity provider. | Use Microsoft Entra ID for SPA/API auth. |
| Data privacy | No retention policy. | Use 90-day default retention for raw resumes, reports, and detailed traces. |
| Dependency pins | Old exact SDK versions may be stale by implementation time. | Require lockfiles and tested exact pins during implementation. Do not blindly copy stale pins. |
| Streaming | Agent call uses non-streaming OpenAI calls while SSE streams tool events. | Keep non-streaming tool-call turns for implementation simplicity; stream internal events to the client. |
| Compliance | Agent trace may contain PII if raw tool results are logged. | Persist sanitized summaries by default; never persist raw resume text in logs or traces. |

### 2.6 Feasibility Assessment

The design is feasible on Azure, but it is operationally broad for v1. The largest implementation risks are Azure service configuration, managed identity/RBAC correctness, API Management plus Static Web Apps auth integration, agent loop determinism, SSE state management across replicas, PII-safe trace persistence, and AI Search vector schema compatibility with the chosen embedding deployment.

Because the user selected "preserve original", APIM, CDN, Redis, Functions, Service Bus, AI Search, and the full AI service inventory remain required. The spec mitigates complexity by assigning each service one clear responsibility and making optional behavior explicit.

## 3. Production Blueprint

### 3.1 Environments

Implement two environments:

- `dev`: lower-cost environment for integration testing and manual validation.
- `prod`: production environment with separate Terraform state, Key Vault secrets, app registrations, resource names, and deployment approvals.

Default Azure region:

- `swedencentral`

Prerequisites before implementation:

- Confirm Azure OpenAI model availability and quota in `swedencentral`.
- Confirm Azure AI Document Intelligence, Translator, Language, Content Safety, AI Search, Container Apps, Static Web Apps, APIM, Redis, Cosmos DB, and Service Bus availability for the subscription and region.
- Confirm Entra ID app registration permissions for SPA sign-in and APIM JWT validation.

### 3.2 Azure OpenAI Foundry Endpoint Rule

The implementation must validate the Azure OpenAI endpoint and deployment source before any agent work begins.

When models are deployed through Azure AI Foundry, the endpoint and key may belong to the Foundry-managed Azure OpenAI resource rather than an originally created OpenAI resource. The implementation must document where the endpoint and key came from and must fail startup with a clear configuration error when the configured endpoint cannot resolve the `gpt-4o` or embedding deployments.

Required configuration values:

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_KEY` or managed identity configuration where supported
- `CHAT_MODEL_DEPLOYMENT_NAME`
- `EMBEDDING_MODEL_DEPLOYMENT_NAME`

The README and backend OpenAI service module must include a short note explaining how to avoid `DeploymentNotFound` caused by using the wrong Azure OpenAI resource endpoint.

### 3.3 High-Level Components

| Component | Responsibility |
| --- | --- |
| React SPA | Upload resume/JD, open SSE stream, display trace and report. |
| Azure CDN | Front Static Web Apps for edge caching of static assets. |
| Static Web Apps | Host the compiled SPA. |
| API Management | Public API gateway, Entra JWT validation, rate limiting, request forwarding. |
| FastAPI API | Validate uploads, write job records, upload blobs, expose score and SSE endpoints. |
| Blob Storage | Store raw resumes and generated report artifacts. |
| Azure Function | Trigger on resume blob creation and enqueue Service Bus work. |
| Service Bus | Durable queue for agent jobs. |
| Container Apps Worker | Consume queue messages and run the guarded agent. |
| Azure OpenAI | Function-calling agent, scoring, fit summary, embeddings. |
| Document Intelligence | Extract text from PDFs/DOCX files. |
| Translator | Detect and translate non-English resume text. |
| Azure AI Language | Detect and redact PII. |
| Content Safety | Analyze harmful content risk. |
| AI Search | Vector benchmark search across historical candidate/report embeddings. |
| Redis | Cache embeddings and similarity computations with TTL. |
| Cosmos DB | Persist jobs, candidates, scores, traces, and review flags. |
| Key Vault | Store secrets and service keys that cannot be replaced with managed identity. |
| Monitor/App Insights/Log Analytics | Logs, traces, metrics, alerts, dashboards. |
| GitHub Actions | Terraform, backend, and frontend CI/CD. |

### 3.4 End-to-End Data Flow

1. Recruiter signs into the SPA using Microsoft Entra ID.
2. SPA sends `POST /api/upload` through APIM with a bearer token, PDF/DOCX file, and job description.
3. APIM validates the JWT, applies rate limiting, and forwards the request to FastAPI.
4. FastAPI validates file type and size, creates `job_id`, writes a `jobs` document, and uploads the resume to `resumes-raw/{job_id}/{safe_filename}` with metadata.
5. Blob creation triggers the Azure Function.
6. The Function parses `job_id` from the blob path, reads the matching job document, and sends `{job_id, blob_path, jd_text}` to the Service Bus queue.
7. SPA opens `GET /api/score/{job_id}/stream` through APIM.
8. The worker receives the Service Bus message, marks the job as `agent_running`, and creates an SSE stream entry for the job.
9. The guarded agent calls Azure OpenAI with the tool registry and prior memory.
10. Each tool call and summarized tool result is pushed to the SSE registry and persisted to `agent_traces` after sanitization.
11. The worker compiles the `AgentResult`, writes `scores`, updates `jobs`, writes `review_flags` if needed, uploads report JSON to `reports/{job_id}/report.json`, and sends a final SSE event.
12. SPA renders the score dashboard, keyword badges, trace, fit summary, language/PII badges, and human-review banner when applicable.

## 4. Agent Design

### 4.1 Agent Control Model

Use a guarded agent architecture.

The Azure OpenAI model chooses tools and arguments through function calling. The runtime does not implement a fixed business pipeline, but it does enforce safety and completeness invariants. This is required because a production ATS system cannot trust a model alone to remember mandatory privacy, safety, and reporting steps.

The runtime must enforce:

- `extract_resume_text` must occur before any tool that needs resume text.
- `check_pii_and_safety` must complete before `score_resume`, `compute_semantic_similarity`, or `generate_fit_summary` can use resume text.
- If `detect_language` returns a non-English language, either `translate_text` must be completed or the job must be flagged for human review before final completion.
- `score_resume`, `compute_semantic_similarity`, and `generate_fit_summary` must complete before a report is marked complete.
- `flag_for_human_review` must be called, or a `review_flags` record must be written by the guardrail fallback, when score is below 30, tool confidence is below 0.6, safety is flagged, extraction confidence is low, max iterations are reached, required fields are missing, or the model attempts to finish early.
- Maximum agent iterations is 12.
- Maximum retries per tool call is 2 retries after the initial attempt.
- All tool inputs and outputs must be validated against Pydantic models before being accepted into memory.

### 4.2 Canonical Tool Registry

The canonical tools are:

1. `extract_resume_text`
2. `detect_language`
3. `translate_text`
4. `check_pii_and_safety`
5. `score_resume`
6. `compute_semantic_similarity`
7. `search_similar_candidates`
8. `flag_for_human_review`
9. `generate_fit_summary`

Treat `get_embedding` and `search_similar_jds` from the original prompt as obsolete aliases. Do not expose them in the OpenAI tool registry.

### 4.3 Tool Contracts

`extract_resume_text`

- Input: `{ "blob_path": "resumes-raw/{job_id}/{safe_filename}" }`
- Uses: Azure AI Document Intelligence prebuilt read model.
- Output: `{ "text": string, "page_count": int, "confidence": float }`
- Rules: do not persist raw extracted text in logs or traces.

`detect_language`

- Input: `{ "text": string }`
- Uses: Azure AI Translator detect endpoint.
- Output: `{ "language_code": string, "language_name": string, "confidence": float }`
- Rules: pass at most the first 500 safe characters.

`translate_text`

- Input: `{ "text": string, "source_language": string }`
- Uses: Azure AI Translator translate endpoint with target language `en`.
- Output: `{ "translated_text": string, "source_language": string }`
- Rules: use only when language is not English or when guardrails require translation after a non-English detection.

`check_pii_and_safety`

- Input: `{ "text": string }`
- Uses: Azure AI Language PII recognition/redaction and Azure AI Content Safety text moderation.
- Output: `{ "sanitized_text": string, "pii_detected": bool, "pii_categories": string[], "safety_flagged": bool, "safety_categories": string[] }`
- Rules: use sanitized text for all scoring, summary, embeddings, traces, and logs. Raw text can exist only in process memory for the duration of a job.

`score_resume`

- Input: `{ "job_description": string, "resume_text": string }`
- Uses: Azure OpenAI chat completion with deterministic JSON output.
- Output:

```json
{
  "score": 0,
  "breakdown": {
    "keyword_match": 0,
    "experience_alignment": 0,
    "skills_coverage": 0
  },
  "matched_keywords": [],
  "missing_keywords": [],
  "confidence": 0.0
}
```

- Rules: `score` must be 0-100. Breakdown must sum to the same 0-100 scale: 40 points keyword match, 30 points experience alignment, 30 points skills coverage.

`compute_semantic_similarity`

- Input: `{ "job_description": string, "resume_text": string }`
- Uses: Redis cache and Azure OpenAI embeddings.
- Output: `{ "similarity_score": float, "cache_hit": bool, "resume_embedding_ref": string, "jd_embedding_ref": string }`
- Rules: default deployment is `text-embedding-ada-002` with 1536 dimensions. If implementation validates a newer embedding model, AI Search vector dimensions and all schemas must be updated consistently in the same change.

`search_similar_candidates`

- Input: `{ "resume_embedding_ref": string, "top_k": 3 }`
- Uses: Azure AI Search vector query over historical candidate/report embeddings.
- Output:

```json
{
  "similar_candidates": [
    { "candidate_id": "string", "job_id": "string", "score": 0, "similarity": 0.0 }
  ]
}
```

- Rules: optional for final completion. If skipped, report `similar_candidates: []`.

`flag_for_human_review`

- Input: `{ "job_id": string, "reason": string, "severity": "low|medium|high" }`
- Uses: Cosmos DB `review_flags` container.
- Output: `{ "review_id": string, "flagged": bool }`
- Rules: idempotent by `{job_id, reason_code}`.

`generate_fit_summary`

- Input: `{ "score": int, "matched_keywords": string[], "missing_keywords": string[], "job_description": string, "resume_text": string }`
- Uses: Azure OpenAI chat completion.
- Output: `{ "summary": string }`
- Rules: generate 2-3 plain-English sentences for recruiters. Do not expose protected attributes, raw PII, or unsupported claims.

### 4.4 Agent Runtime Modules

Implement these backend modules:

- `agent_runner`: owns the iteration loop, model calls, guardrails, retries, max iterations, event emission, and final result compilation.
- `tool_registry`: defines OpenAI tool schemas and maps obsolete aliases to explicit validation errors.
- `tool_executor`: dispatches validated tool calls to service adapters and normalizes failures.
- `agent_memory`: stores model messages, accepted tool calls, accepted tool results, milestones, and sanitized trace summaries.
- `agent_policy`: enforces required milestones, blocked transitions, human-review fallback, and completion criteria.
- `agent_models`: Pydantic request/response/event/result models.

The agent runner must use non-streaming OpenAI calls for each tool-call turn and emit SSE events from the application runtime. This keeps the implementation simpler while still giving the user real-time tool call visibility.

## 5. Backend API Design

### 5.1 API Endpoints

`POST /api/upload`

- Auth: Entra ID bearer token required.
- Request: multipart form data with `file` and `job_description`.
- Validation:
  - File extension must be `.pdf` or `.docx`.
  - MIME type must match the allowed extension.
  - Maximum file size: 10 MB.
  - Job description must be non-empty and below 50,000 characters.
- Behavior:
  - Generate UUID `job_id`.
  - Sanitize the filename.
  - Write `jobs` record with status `queued`.
  - Upload the blob to `resumes-raw/{job_id}/{safe_filename}` with metadata: `job_id`, `original_filename`, `uploaded_by`, `uploaded_at`.
  - Return immediately.
- Response:

```json
{ "job_id": "uuid", "status": "queued" }
```

`GET /api/score/{job_id}`

- Auth: Entra ID bearer token required.
- Behavior: return job status and score if available.
- Response status:
  - `200` when the job exists.
  - `404` when the job does not exist or the user is not allowed to view it.

`GET /api/score/{job_id}/stream`

- Auth: Entra ID bearer token required.
- Behavior:
  - Register an SSE queue by `job_id` and user context.
  - Stream events until `complete`, `error`, client disconnect, or 5-minute inactivity timeout.
  - Use valid SSE framing: `data: {json}\n\n`.
- Response content type: `text/event-stream`.

`GET /api/health`

- Auth: not required for internal container health probe.
- Response:

```json
{ "status": "ok", "version": "string", "environment": "dev|prod" }
```

### 5.2 SSE Events

Every SSE payload must include `event_type`, `job_id`, and `timestamp`.

`tool_call`

```json
{
  "event_type": "tool_call",
  "job_id": "uuid",
  "iteration": 1,
  "tool_name": "extract_resume_text",
  "arguments_summary": "resume blob path",
  "timestamp": "2026-04-08T00:00:00Z"
}
```

`tool_result`

```json
{
  "event_type": "tool_result",
  "job_id": "uuid",
  "iteration": 1,
  "tool_name": "extract_resume_text",
  "result_summary": "Extracted 2 pages with 0.94 confidence.",
  "duration_ms": 1234,
  "timestamp": "2026-04-08T00:00:00Z"
}
```

`complete`

```json
{
  "event_type": "complete",
  "job_id": "uuid",
  "result": {},
  "timestamp": "2026-04-08T00:00:00Z"
}
```

`error`

```json
{
  "event_type": "error",
  "job_id": "uuid",
  "message": "Job failed and was flagged for human review.",
  "retryable": false,
  "timestamp": "2026-04-08T00:00:00Z"
}
```

### 5.3 Worker Behavior

The worker must:

- Receive one Service Bus message at a time per task execution.
- Validate message shape: `{job_id, blob_path, jd_text}`.
- Update the job status to `agent_running`.
- Create or find the SSE queue for the job.
- Run the guarded agent.
- Persist score, trace, review flag, and report JSON.
- Update the job status to `completed`, `completed_with_review`, or `failed_review_required`.
- Complete the Service Bus message only after durable writes succeed.
- Abandon on retryable failures with exponential backoff.
- Dead-letter after max delivery count, write a `review_flags` record, and log full exception context without raw resume text.

### 5.4 Azure Function Behavior

The blob trigger path is:

```text
resumes-raw/{job_id}/{safe_filename}
```

The Function must:

- Parse `job_id` from the path.
- Validate that the blob metadata `job_id` matches the path.
- Read the `jobs` document by `job_id`.
- Send `{job_id, blob_path, jd_text}` to the Service Bus queue.
- Use managed identity where supported.
- Never query jobs by filename.

## 6. Frontend Design

### 6.1 State Machine

The Home page state machine is:

```text
idle -> uploading -> queued -> agent_running -> complete
idle -> uploading -> error
agent_running -> completed_with_review
agent_running -> error
```

### 6.2 Required UI Components

- `UploadPanel`: PDF/DOCX file selector and validation errors.
- `JobDescriptionPanel`: JD textarea with character count.
- `AgentTracePanel`: live tool call/result cards from SSE.
- `ProgressStream`: EventSource state and reconnection handling.
- `ScoreGauge`: score 0-100 with red/amber/green thresholds.
- `ScoreBreakdown`: keyword, experience, skills, and semantic similarity bars.
- `KeywordBadges`: matched and missing keyword chips.
- `HumanReviewBanner`: visible when `human_review_required` is true.
- `PrivacyBadges`: language detected/translated and PII redacted indicators.

### 6.3 Frontend Security Requirements

- Store access tokens only according to the Microsoft identity library's recommended browser pattern.
- Never render raw resume text.
- Never include raw PII in trace cards.
- Show only summarized tool arguments and summarized tool results.
- Close the EventSource on page unload, terminal events, and auth expiry.

## 7. Data Architecture

### 7.1 Cosmos DB

Database: `ats-db`

Containers:

`jobs`

- Partition key: `/id`
- TTL: 90 days unless `retention_hold=true`
- Fields:
  - `id`
  - `status`
  - `filename`
  - `blob_path`
  - `job_description`
  - `uploaded_by`
  - `created_at`
  - `updated_at`
  - `retention_hold`

`candidates`

- Partition key: `/id`
- TTL: 90 days unless `retention_hold=true`
- Fields:
  - `id`
  - `job_id`
  - `resume_blob_path`
  - `language_detected`
  - `translated`
  - `pii_detected`
  - `created_at`

`scores`

- Partition key: `/job_id`
- TTL: 90 days unless `retention_hold=true`
- Fields:
  - `id`
  - `job_id`
  - `score`
  - `breakdown`
  - `matched_keywords`
  - `missing_keywords`
  - `semantic_similarity`
  - `fit_summary`
  - `human_review_required`
  - `human_review_reason`
  - `similar_candidates`
  - `created_at`

`agent_traces`

- Partition key: `/job_id`
- TTL: 90 days unless `retention_hold=true`
- Fields:
  - `id`
  - `job_id`
  - `steps`
  - `total_iterations`
  - `total_duration_ms`
  - `contains_raw_text`: always false
  - `created_at`

`review_flags`

- Partition key: `/job_id`
- TTL: 90 days unless `retention_hold=true`
- Fields:
  - `id`
  - `job_id`
  - `reason_code`
  - `reason`
  - `severity`
  - `created_at`
  - `created_by`: `agent|policy_guardrail|worker`

### 7.2 Blob Storage

Containers:

- `resumes-raw`: raw uploaded resumes at `resumes-raw/{job_id}/{safe_filename}`.
- `reports`: generated report JSON at `reports/{job_id}/report.json`.

Retention:

- Apply lifecycle management to delete blobs after 90 days unless legal/admin retention requires separate storage policy.

### 7.3 Service Bus

Queue:

- `ats-agent-jobs`

Configuration:

- Standard tier.
- Max delivery count: 3.
- Dead-letter on message expiration.
- Message body: `{ "job_id": string, "blob_path": string, "jd_text": string }`.
- Message id: `job_id` for duplicate detection where supported.

### 7.4 Redis

Use Redis for short-lived embedding and similarity cache entries:

- TTL: 1 hour.
- Cache key format:
  - `embedding:{model}:{sha256(text)}`
  - `similarity:{model}:{sha256(jd_text)}:{sha256(resume_text)}`
- Cache values must not include raw text.

### 7.5 Azure AI Search

Index name:

- `candidate-embeddings`

Vector dimension:

- 1536 for `text-embedding-ada-002`.

Required fields:

- `id`: key
- `job_id`
- `candidate_id`
- `document_type`: `resume|job_description|report`
- `score`
- `created_at`
- `embedding`: `Collection(Edm.Single)`, vector-search enabled

If implementation changes the embedding deployment, update vector dimensions and Terraform schema in the same commit.

## 8. Infrastructure Design

### 8.1 Terraform Layout

Create a greenfield project under `ats-agent/` when implementation begins. Use modules for:

- `storage`
- `ai_services`
- `compute`
- `networking`
- `observability`
- `security`
- `data`

Root Terraform must create:

- Resource group.
- Storage account and containers.
- Key Vault.
- Cognitive accounts or equivalent resources for Document Intelligence, Translator, Language, Content Safety, and OpenAI/Foundry integration.
- AI Search service.
- Cosmos DB account, database, and containers.
- Service Bus namespace and queue.
- Redis cache.
- Container Registry.
- Log Analytics Workspace.
- Application Insights.
- Container Apps Environment.
- FastAPI Container App and worker process.
- Linux Function App for blob trigger.
- API Management Developer SKU for dev and an explicitly chosen SKU for prod.
- Static Web App.
- CDN profile and endpoint.
- RBAC assignments.
- Alerts.

### 8.2 Naming

Use:

```text
${project_name}-${environment}-<resource-type>
```

Default variables:

- `project_name = "ats-agent"`
- `environment = "dev"`
- `location = "swedencentral"`

### 8.3 Target Repository Structure

Implementation must create this structure unless a generated framework requires additional standard files:

```text
ats-agent/
├── infra/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── providers.tf
│   ├── terraform.tfvars.example
│   ├── env/
│   │   ├── dev.tfvars.example
│   │   └── prod.tfvars.example
│   └── modules/
│       ├── ai_services/
│       ├── compute/
│       ├── data/
│       ├── networking/
│       ├── observability/
│       ├── security/
│       └── storage/
├── backend/
│   ├── Dockerfile
│   ├── requirements.in
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── logging_config.py
│   │   ├── routers/
│   │   ├── agent/
│   │   ├── services/
│   │   ├── models/
│   │   └── worker.py
│   ├── function_trigger/
│   └── tests/
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── staticwebapp.config.json
│   ├── index.html
│   └── src/
├── .github/
│   └── workflows/
│       ├── terraform.yml
│       ├── backend.yml
│       └── frontend.yml
└── README.md
```

### 8.4 Identity and RBAC

Container App managed identity:

- Storage Blob Data Contributor on storage account.
- Cognitive Services User on Document Intelligence, Translator, Language, and Content Safety where supported.
- Cognitive Services OpenAI User or equivalent Azure OpenAI role on OpenAI resource where supported.
- Search Index Data Contributor on AI Search.
- Cosmos DB Built-in Data Contributor on Cosmos account.
- Azure Service Bus Data Receiver on Service Bus namespace.
- Key Vault Secrets User on Key Vault.

Function App managed identity:

- Storage Blob Data Reader on storage account.
- Azure Service Bus Data Sender on Service Bus namespace.
- Cosmos DB Built-in Data Reader on Cosmos account.
- Key Vault Secrets User if it must read configuration secrets.

GitHub Actions OIDC identity:

- Contributor scoped to the environment resource group for Terraform apply.
- Least-privilege refinements should be applied after initial bootstrap.

## 9. Security, Privacy, and Compliance

### 9.1 User Authentication

Use Microsoft Entra ID:

- SPA signs in recruiter/admin users.
- APIM validates issuer, audience, signature, and token expiry.
- Backend receives forwarded user claims and enforces ownership/role checks.

### 9.2 Secret Management

- No hardcoded credentials.
- Prefer managed identity for Azure SDK clients.
- Store unavoidable API keys in Key Vault.
- Use Key Vault references for Container App and Function App environment variables.
- Do not expose Key Vault values through Terraform outputs.

### 9.3 PII Handling

- Raw resume blobs are stored only in Blob Storage.
- Raw extracted text exists only in process memory for the active job.
- Azure AI Language redacts PII before scoring, embeddings, summaries, traces, and logs.
- Agent traces store summarized, sanitized outputs only.
- App logs must not include raw resume text, raw job descriptions, or unredacted tool outputs.

### 9.4 File Safety

- Allow PDF and DOCX only.
- Enforce 10 MB max upload size.
- Sanitize filenames.
- Store uploads under `job_id` folders, not user-provided paths.
- Reject encrypted or unreadable files with human-review fallback where possible.

### 9.5 Retention

Default retention is 90 days:

- Blob lifecycle deletes raw resumes and reports.
- Cosmos DB TTL deletes jobs, candidates, scores, traces, and review flags.
- Retention can be extended only by setting `retention_hold=true` through an authenticated administrative path.

## 10. Observability

### 10.1 Logging

Use structured JSON logs with:

- `timestamp`
- `level`
- `service`
- `environment`
- `request_id`
- `job_id`
- `iteration`
- `tool_name`
- `duration_ms`
- `status`
- `error_type`

Never use `print()` in backend or worker code.

### 10.2 Metrics and Alerts

Required metrics:

- Upload request count and latency.
- SSE connection count, duration, disconnect count, and timeout count.
- Service Bus queue depth.
- Service Bus dead-letter count.
- Agent iteration count per job.
- Tool duration and failure count by tool.
- Human-review flag count by reason.
- Container App CPU/memory/restart count.

Required alerts:

- Service Bus queue depth above 50 for 5 minutes.
- Dead-letter count greater than 0.
- Agent max-iteration fallback above baseline.
- Tool failure rate above 5% over 15 minutes.
- Container App restart loop.
- APIM 5xx rate above 2% over 10 minutes.

## 11. CI/CD Design

### 11.1 Terraform Workflow

Trigger:

- PR and push to `main` for `infra/**`.

PR:

- `terraform fmt -check`
- `terraform init`
- `terraform validate`
- `terraform plan`

Main:

- Environment-gated `terraform apply -auto-approve`.

Auth:

- GitHub OIDC to Azure.
- No stored Azure client secret.

### 11.2 Backend Workflow

Trigger:

- PR and push to `main` for `backend/**`.

Steps:

- Install locked Python dependencies.
- Run formatting/lint/type checks.
- Run pytest with Azure/OpenAI clients mocked.
- Build Docker image.
- Push to ACR on main.
- Deploy Container App on main.

### 11.3 Frontend Workflow

Trigger:

- PR and push to `main` for `frontend/**`.

Steps:

- `npm ci`
- Typecheck.
- Lint.
- Test.
- Build.
- Deploy to Static Web Apps on main.

## 12. Cost and Scale Posture

Because the selected approach preserves the original Azure-heavy inventory, the implementation must make cost controls explicit rather than silently removing services.

Default v1 sizing:

- Static Web Apps: Free tier where compatible.
- API Management: Developer SKU for dev; choose a production SKU explicitly during prod rollout.
- Container Apps: min replicas 1, max replicas 10, KEDA scale rule on Service Bus queue depth.
- Service Bus: Standard.
- Redis: smallest non-production tier in dev; production tier chosen by reliability requirement.
- AI Search: Standard tier with one replica unless load testing requires more.
- Cosmos DB: start with autoscale or provisioned throughput chosen by expected recruiter volume; document the choice in Terraform variables.
- Blob Storage lifecycle: 90-day deletion to reduce storage and privacy exposure.
- Azure OpenAI, Document Intelligence, Translator, Language, and Content Safety: usage-based; add budget alerts.

Required cost controls:

- Azure budget alert per environment.
- Tags: `project`, `environment`, `owner`, `cost_center`.
- Terraform variables for SKU choices rather than hardcoded production-scale SKUs.
- README cost estimate table for low-usage dev and expected production baseline.

## 13. Testing and Acceptance Criteria

### 13.1 Unit Tests

Required backend unit tests:

- Agent starts with resume extraction or policy correction.
- Agent blocks scoring before PII/safety completion.
- Agent translates non-English text or requires review if translation fails.
- Agent flags score below 30.
- Agent flags safety issue.
- Agent flags low extraction or language confidence.
- Agent max iterations triggers human review.
- Tool executor retries retryable failures.
- Tool executor returns typed non-retryable errors.
- Agent result compilation rejects incomplete report fields.

### 13.2 Service Adapter Tests

Mock all external services:

- Document Intelligence extraction.
- Translator detect/translate.
- Azure AI Language PII redaction.
- Content Safety moderation.
- Azure OpenAI scoring, summary, tool-call, and embedding calls.
- Redis cache hit/miss.
- AI Search vector query.
- Cosmos create/update/query.
- Blob upload/read metadata.
- Service Bus send/receive/complete/dead-letter.

### 13.3 API Tests

Required API tests:

- Reject unsupported file type.
- Reject oversized file.
- Create deterministic blob path with `job_id`.
- Create `jobs` document on upload.
- Return score when available.
- Return queued/running state before score is available.
- Format SSE events as valid `data: {json}\n\n`.
- Emit terminal `error` event when worker fails.
- Enforce auth on upload, score, and stream endpoints.

### 13.4 Frontend Tests

Required frontend tests:

- Upload flow transitions from idle to queued.
- EventSource events update the trace panel.
- Complete event renders score report.
- Human-review banner appears when required.
- Language badge appears for translated resumes.
- PII badge appears when redaction occurred.
- SSE disconnect produces a recoverable user-facing error.

### 13.5 Terraform Tests

Required validation:

- `terraform fmt -check`.
- `terraform validate`.
- Plan creates all required resources.
- RBAC assignments reference correct managed identities.
- Key Vault references are used for secrets.
- Resource names follow naming convention.
- Outputs include API URL, Static Web App URL, APIM gateway URL, Key Vault URI, Cosmos endpoint, Search endpoint, and App Insights connection string.

### 13.6 Acceptance Scenario

The implementation is acceptable when a tester can:

1. Sign in through Entra ID.
2. Upload a valid PDF or DOCX resume with a job description.
3. See live agent tool calls and summarized tool results.
4. Receive a complete ATS report with score, breakdown, semantic similarity, matched keywords, missing keywords, and fit summary.
5. Confirm raw PII is not visible in UI traces or logs.
6. Confirm non-English input is translated or flagged for review.
7. Confirm low-score or unsafe content is flagged for human review.
8. Confirm result, trace, review flag, and report artifact are persisted.
9. Confirm queue/dead-letter/agent metrics are visible in Azure Monitor.

## 14. README Requirements

The generated `README.md` must include:

- What makes the system a guarded AI agent rather than a deterministic pipeline.
- Architecture overview across frontend, API, worker, agent, data, and Azure infrastructure.
- Agent tool reference with all 9 canonical tools.
- Azure OpenAI Foundry endpoint troubleshooting note.
- Setup prerequisites: Azure CLI, Terraform, Docker, Node 20+, Python 3.11, and GitHub OIDC configuration.
- Local development steps.
- Terraform deployment steps for dev and prod.
- Environment variable reference table.
- API reference with curl examples.
- Security and PII handling explanation.
- Cost estimate table.
- Troubleshooting for `DeploymentNotFound`, Service Bus scaling, Content Safety/Language authentication, SSE disconnects, AI Search index issues, and max-iteration fallback.

## 15. Dependency Policy

Do not blindly copy the exact package pins from `implementation_prompt.md`.

Implementation must:

- Start from the original dependency intent.
- Resolve current compatible package versions.
- Commit exact lockfiles or pinned dependency files after tests pass.
- Keep Python, TypeScript, Terraform provider, and GitHub Action versions reproducible.
- Document any SDK version changes that affect API calls or authentication behavior.

## 16. Implementation Order

An AI coding agent should implement in this order:

1. Create the greenfield `ats-agent/` workspace structure.
2. Add backend models, config, logging, and test scaffolding.
3. Implement Azure service adapters with mocked tests first.
4. Implement agent registry, memory, policy, executor, and runner.
5. Implement FastAPI upload, score, health, and SSE endpoints.
6. Implement Service Bus worker.
7. Implement Azure Function blob trigger.
8. Implement frontend auth, upload flow, SSE hook, trace panel, and report dashboard.
9. Implement Terraform modules and environment variables.
10. Implement GitHub Actions workflows.
11. Add README with setup, architecture, agent behavior, cost estimate, and troubleshooting.
12. Run full local tests and Terraform validation before deploying to Azure.

## 17. Source References

Official Microsoft documentation used to correct and validate this design:

- Azure AI Language PII redaction: <https://learn.microsoft.com/en-us/azure/ai-services/language-service/personally-identifiable-information/how-to/redact-text-pii>
- Azure AI Content Safety overview: <https://learn.microsoft.com/en-us/azure/ai-services/content-safety/overview>
- Azure OpenAI function calling: <https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/function-calling>
- Azure AI Search vector index creation: <https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-create-index>

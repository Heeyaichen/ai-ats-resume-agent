You are a senior Azure AI engineer and full-stack developer. Build a production-grade,
genuinely agentic ATS Resume Screening Agent from scratch — a complete greenfield
implementation. Do not reference any prior code. Follow every instruction precisely.

═══════════════════════════════════════════════════════════════════════
PROBLEM STATEMENT & OBJECTIVE
═══════════════════════════════════════════════════════════════════════

Recruitment teams receive hundreds of resumes per job opening. Manual screening is
slow, inconsistent, and blind to nuance (multilingual resumes, ambiguous JDs, edge
cases requiring human judgment). Build an AI-powered ATS Resume Screening Agent that:

1. Accepts resume uploads (PDF/DOCX) and job descriptions via a React web UI
2. Runs a TRUE AGENTIC REASONING LOOP — an Azure OpenAI gpt-4o model that
   autonomously decides which tools to call, in what order, based on what it
   observes at each step — not a hardcoded sequential pipeline
3. The agent's tool arsenal maps directly to Azure AI services:
   - extract_resume_text      → Azure AI Document Intelligence
   - detect_language          → Azure AI Translator
   - translate_text           → Azure AI Translator
   - check_pii_and_safety     → Azure AI Content Safety
   - score_resume             → Azure OpenAI gpt-4o chat completions
   - get_embedding            → Azure OpenAI text-embedding-ada-002
   - search_similar_jds       → Azure AI Search (vector similarity)
   - flag_for_human_review    → Cosmos DB write (sets review flag)
   - generate_fit_summary     → Azure OpenAI gpt-4o (plain English paragraph)
4. Persists all structured data in Azure Cosmos DB
5. Streams real-time agent reasoning steps and tool calls to the client via SSE
6. Returns a full ATS report: score (0-100), keyword breakdown, semantic similarity,
   matched/missing skills, fit explanation, and agent reasoning trace
7. Flags edge cases automatically: low scores, non-English resumes, PII detected,
   ambiguous JDs — without any hardcoded if/else logic

The agent must exhibit genuine agentic properties:
- AUTONOMY: decides next action based on tool outputs, not a fixed sequence
- TOOL USE: dynamically selects from 9 tools via Azure OpenAI function calling
- MULTI-STEP REASONING: planning loop with memory of prior tool call results
- GOAL-DIRECTED: works toward "produce a complete, trustworthy ATS report"
- SELF-CORRECTION: if a tool returns an error or low-confidence result,
  the agent retries with adjusted parameters or escalates to human review

═══════════════════════════════════════════════════════════════════════
ARCHITECTURE — IMPLEMENT EXACTLY THIS
═══════════════════════════════════════════════════════════════════════

LAYER 1 — IaC:
  - Terraform (>= 1.6) provisions ALL Azure resources — zero click-ops
  - Azure Key Vault stores ALL sensitive values
  - System-Assigned Managed Identity on all compute resources
  - All RBAC role assignments declared in Terraform

LAYER 2 — Frontend:
  - React 18 + TypeScript + Vite SPA
  - Azure Static Web Apps (Free tier)
  - Azure CDN in front for edge caching
  - Azure API Management as single API ingress (rate limiting, JWT policy)
  - Features: resume upload, JD input, live agent reasoning trace panel (SSE),
    score dashboard, keyword badges, agent decision log

LAYER 3 — API / Compute:
  - Azure Container Apps — FastAPI (Python 3.11) — primary compute host
  - Azure Functions — blob-created trigger only — enqueues to Service Bus
  - Azure Service Bus Standard — queue: "ats-agent-jobs"
  - Azure Cache for Redis — embedding vector cache (TTL 1hr)
  - Azure Container Registry — stores Docker image

LAYER 4 — AGENT LAYER (new — the intelligence core):
  - Azure OpenAI Assistants API OR gpt-4o with streaming tool_choice
    (use the streaming function calling approach via openai SDK — more
    control, better for SSE streaming of agent steps to client)
  - Agent has a defined tool schema (9 tools — see AGENT SPECIFICATION below)
  - Agent runs inside the Container App worker, consuming from Service Bus
  - Each tool call is an async function that wraps an Azure AI service
  - Agent reasoning trace (each tool call + result) is streamed to client via SSE
  - Max iterations: 12 (prevents infinite loops — after 12, force-complete with
    whatever data is available and flag for human review)

LAYER 5 — AI Services:
  - Azure AI Document Intelligence — prebuilt-read (OCR, PDF + DOCX)
  - Azure OpenAI (Foundry resource) — gpt-4o + text-embedding-ada-002
  - Azure AI Search — Standard tier — vector index "jd-embeddings" (1536 dims)
  - Azure AI Content Safety — text analysis for PII and harmful content
  - Azure AI Translator — detect + translate non-English resume text

LAYER 6 — Storage & Observability:
  - Azure Blob Storage — containers: resumes-raw, reports
  - Azure Cosmos DB NoSQL — database: ats-db
    containers: jobs, candidates, scores, agent_traces
  - Azure Monitor + Application Insights + Log Analytics Workspace
  - Azure Monitor alert: queue depth > 50 for 5 min
  - Structured JSON logging with job_id and agent_iteration in every log line

═══════════════════════════════════════════════════════════════════════
DIRECTORY STRUCTURE — CREATE EXACTLY THIS
═══════════════════════════════════════════════════════════════════════

ats-agent/
├── infra/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── providers.tf
│   ├── terraform.tfvars.example
│   └── modules/
│       ├── storage/        (main.tf, variables.tf, outputs.tf)
│       ├── ai_services/    (main.tf, variables.tf, outputs.tf)
│       ├── compute/        (main.tf, variables.tf, outputs.tf)
│       ├── networking/     (main.tf, variables.tf, outputs.tf)
│       └── observability/  (main.tf, variables.tf, outputs.tf)
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── routers/
│   │   │   ├── upload.py
│   │   │   ├── score.py
│   │   │   └── health.py
│   │   ├── agent/
│   │   │   ├── agent_runner.py     ← THE CORE AGENTIC LOOP
│   │   │   ├── tool_registry.py    ← tool schema + dispatch table
│   │   │   ├── tool_executor.py    ← async execution of each tool
│   │   │   └── agent_memory.py     ← in-context state across iterations
│   │   ├── services/
│   │   │   ├── document_intel.py
│   │   │   ├── openai_service.py
│   │   │   ├── search_service.py
│   │   │   ├── blob_service.py
│   │   │   ├── cosmos_service.py
│   │   │   ├── queue_service.py
│   │   │   ├── cache_service.py
│   │   │   ├── translator_service.py
│   │   │   └── content_safety_service.py
│   │   ├── models/
│   │   │   ├── requests.py
│   │   │   ├── responses.py
│   │   │   └── agent_models.py     ← AgentState, ToolCall, AgentTrace
│   │   └── worker.py
│   └── function_trigger/
│       ├── function_app.py
│       └── requirements.txt
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── staticwebapp.config.json
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/
│       │   └── client.ts
│       ├── components/
│       │   ├── UploadPanel.tsx
│       │   ├── JobDescriptionPanel.tsx
│       │   ├── ScoreGauge.tsx
│       │   ├── KeywordBadges.tsx
│       │   ├── ScoreBreakdown.tsx
│       │   ├── AgentTracePanel.tsx   ← live agent reasoning log
│       │   └── ProgressStream.tsx
│       └── pages/
│           └── Home.tsx
├── .github/
│   └── workflows/
│       ├── terraform.yml
│       ├── backend.yml
│       └── frontend.yml
└── README.md

═══════════════════════════════════════════════════════════════════════
AGENT SPECIFICATION — IMPLEMENT THIS EXACTLY
═══════════════════════════════════════════════════════════════════════

FILE: backend/app/agent/tool_registry.py

Define TOOLS as a list of dicts following the OpenAI function calling schema.
Implement ALL 9 tools with complete JSON schema definitions:

TOOL 1: extract_resume_text
  description: "Extract raw text from a resume PDF or DOCX stored in Azure Blob Storage
                using Azure AI Document Intelligence OCR."
  parameters:
    blob_path: string (required) — e.g. "resumes-raw/john_doe.pdf"
  returns: { "text": string, "page_count": int, "confidence": float }

TOOL 2: detect_language
  description: "Detect the language of the extracted resume text using Azure AI Translator."
  parameters:
    text: string (required) — first 500 chars of resume text
  returns: { "language_code": string, "language_name": string, "confidence": float }

TOOL 3: translate_text
  description: "Translate non-English resume text to English using Azure AI Translator.
                Only call this if detect_language returned a non-English language."
  parameters:
    text: string (required)
    source_language: string (required) — ISO 639-1 code
  returns: { "translated_text": string, "source_language": string }

TOOL 4: check_pii_and_safety
  description: "Analyze resume text for PII (names, emails, phone numbers, addresses)
                and harmful content using Azure AI Content Safety. Returns sanitized
                text with PII replaced by placeholders."
  parameters:
    text: string (required)
  returns: { "sanitized_text": string, "pii_detected": bool,
             "pii_categories": list[string], "safety_flagged": bool }

TOOL 5: score_resume
  description: "Score the resume against the job description using Azure OpenAI gpt-4o.
                Returns keyword match score, experience alignment, skills coverage,
                matched keywords, and missing keywords."
  parameters:
    job_description: string (required)
    resume_text: string (required) — use sanitized text if PII was detected
  returns: {
    "score": int (0-100),
    "breakdown": {
      "keyword_match": int (0-40),
      "experience_alignment": int (0-30),
      "skills_coverage": int (0-30)
    },
    "matched_keywords": list[string],
    "missing_keywords": list[string]
  }

TOOL 6: compute_semantic_similarity
  description: "Compute embedding-based cosine similarity between the job description
                and resume using text-embedding-ada-002. Returns a similarity score
                0.0-1.0. Check Redis cache before calling the embeddings API."
  parameters:
    job_description: string (required)
    resume_text: string (required)
  returns: { "similarity_score": float, "cache_hit": bool }

TOOL 7: search_similar_candidates
  description: "Search Azure AI Search vector index for historically scored resumes
                similar to this one. Use to benchmark the candidate against the pool."
  parameters:
    resume_embedding: list[float] (required) — from a prior compute_semantic_similarity call
    top_k: int (optional, default 3)
  returns: { "similar_candidates": list[{ "candidate_id": string, "score": int,
             "similarity": float }] }

TOOL 8: flag_for_human_review
  description: "Flag this job for mandatory human recruiter review. Call this when:
                score < 30, safety_flagged=true, confidence < 0.6, or JD is too
                vague to score reliably. Writes a review record to Cosmos DB."
  parameters:
    job_id: string (required)
    reason: string (required) — plain English explanation of why review is needed
    severity: string (required) — one of: "low", "medium", "high"
  returns: { "review_id": string, "flagged": bool }

TOOL 9: generate_fit_summary
  description: "Generate a 2-3 sentence plain English summary of the candidate fit
                using Azure OpenAI gpt-4o. Call this as the final step after scoring
                is complete."
  parameters:
    score: int (required)
    matched_keywords: list[string] (required)
    missing_keywords: list[string] (required)
    job_description: string (required)
    resume_text: string (required)
  returns: { "summary": string }

═══════════════════════════════════════════════════════════════════════
FILE: backend/app/agent/agent_runner.py — IMPLEMENT IN FULL
═══════════════════════════════════════════════════════════════════════

This is the most important file. Implement a complete agentic loop.

SYSTEM PROMPT for the agent (pass as system message on every iteration):
"""
You are an expert ATS (Applicant Tracking System) screening agent. Your goal is to
produce a complete, accurate, and trustworthy resume screening report.

You have access to 9 tools. Use them autonomously based on what you observe.

Your reasoning process:
1. Always start by extracting the resume text
2. Always check the language — translate if not English
3. Always check for PII and safety issues before scoring
4. Score the resume against the JD
5. Compute semantic similarity
6. Optionally search for similar candidates for benchmarking
7. If score < 30, confidence is low, or content was flagged: call flag_for_human_review
8. Always end by calling generate_fit_summary

You decide the order and whether to call optional tools based on intermediate results.
Never assume a fixed pipeline — reason through each step.
Return tool_choice="auto" responses only — never respond with plain text until the
final generate_fit_summary result is in hand.
"""

class AgentRunner:
  def __init__(self, job_id: str, blob_path: str, jd_text: str,
               sse_queue: asyncio.Queue):
    - store all parameters
    - initialize AgentMemory(job_id)
    - initialize iteration counter = 0
    - MAX_ITERATIONS = 12

  async def run(self) -> AgentResult:
    """
    The main agentic loop. Runs until:
    - generate_fit_summary has been called and returned (goal achieved)
    - MAX_ITERATIONS reached (force-complete, flag for review)
    - An unrecoverable error occurs

    Loop structure:
    1. Build messages list from agent memory (system prompt + all prior
       tool calls and results as assistant + tool messages)
    2. Call openai_client.chat.completions.create() with:
       - model = CHAT_MODEL_DEPLOYMENT_NAME
       - messages = memory.to_messages()
       - tools = TOOLS (full schema list from tool_registry.py)
       - tool_choice = "auto"
       - temperature = 0.0
       - stream = False (use non-streaming for tool calls; SSE to client
         is handled separately by pushing to sse_queue)
    3. Parse response:
       a. If finish_reason == "tool_calls":
          - Extract all tool calls from response.choices[0].message.tool_calls
          - For each tool call:
            i.  Push ToolCallEvent to sse_queue (client sees agent thinking)
            ii. Execute tool via tool_executor.execute(tool_name, args)
            iii.Push ToolResultEvent to sse_queue (client sees result)
            iv. Append tool call + result to agent memory
          - Increment iteration counter
          - Continue loop
       b. If finish_reason == "stop":
          - This should only happen after generate_fit_summary is complete
          - Compile final AgentResult from memory
          - Return result
    4. If iteration >= MAX_ITERATIONS:
       - Call flag_for_human_review with reason="max iterations reached"
       - Compile partial AgentResult
       - Return with is_complete=False
    """

  async def _execute_tool_call(self, tool_name: str,
                                arguments: dict) -> dict:
    """Dispatch to tool_executor and handle errors with retry."""
    MAX_TOOL_RETRIES = 2
    for attempt in range(MAX_TOOL_RETRIES + 1):
      try:
        result = await tool_executor.execute(tool_name, arguments)
        return result
      except Exception as e:
        if attempt == MAX_TOOL_RETRIES:
          return {"error": str(e), "tool": tool_name}
        await asyncio.sleep(2 ** attempt)

═══════════════════════════════════════════════════════════════════════
FILE: backend/app/agent/agent_memory.py
═══════════════════════════════════════════════════════════════════════

class AgentMemory:
  Maintains the full conversation history for the agent loop.

  Fields:
    - job_id: str
    - messages: list[dict]  — OpenAI message format
    - tool_calls_made: list[str]  — names of tools called so far
    - tool_results: dict[str, Any]  — keyed by tool name, last result
    - iteration: int

  Methods:
    - add_assistant_message(message) — appends assistant message with tool_calls
    - add_tool_result(tool_call_id, tool_name, result) — appends tool message
    - to_messages() -> list[dict] — returns full message list for API call
    - get_result(tool_name) -> Any — retrieves prior tool result by name
    - has_called(tool_name) -> bool — checks if tool was already called
    - to_trace() -> list[AgentTraceStep] — serializable trace for Cosmos DB

═══════════════════════════════════════════════════════════════════════
FILE: backend/app/agent/tool_executor.py
═══════════════════════════════════════════════════════════════════════

class ToolExecutor:
  Async dispatch table mapping tool names to service function calls.

  async def execute(self, tool_name: str, arguments: dict) -> dict:
    Dispatch map (implement all 9):
    "extract_resume_text"       → document_intel.extract_text(arguments["blob_path"])
    "detect_language"           → translator_service.detect(arguments["text"])
    "translate_text"            → translator_service.translate(arguments["text"],
                                    arguments["source_language"])
    "check_pii_and_safety"      → content_safety_service.analyze(arguments["text"])
    "score_resume"              → openai_service.score_resume(arguments["job_description"],
                                    arguments["resume_text"])
    "compute_semantic_similarity" → openai_service.compute_similarity(
                                    arguments["job_description"],
                                    arguments["resume_text"])
    "search_similar_candidates" → search_service.find_similar(
                                    arguments["resume_embedding"],
                                    arguments.get("top_k", 3))
    "flag_for_human_review"     → cosmos_service.flag_job(arguments["job_id"],
                                    arguments["reason"], arguments["severity"])
    "generate_fit_summary"      → openai_service.generate_summary(arguments)

  All tool functions must return dict. Raise ToolExecutionError on failure.

═══════════════════════════════════════════════════════════════════════
FILE: backend/app/models/agent_models.py
═══════════════════════════════════════════════════════════════════════

Implement these Pydantic models:

class AgentTraceStep(BaseModel):
  iteration: int
  tool_name: str
  arguments: dict
  result: dict
  duration_ms: int
  timestamp: str

class AgentResult(BaseModel):
  job_id: str
  is_complete: bool
  score: int
  breakdown: dict
  matched_keywords: list[str]
  missing_keywords: list[str]
  semantic_similarity: float
  fit_summary: str
  language_detected: str
  pii_detected: bool
  human_review_required: bool
  human_review_reason: str | None
  similar_candidates: list[dict]
  agent_trace: list[AgentTraceStep]
  total_iterations: int
  total_duration_ms: int

class ToolCallEvent(BaseModel):  # SSE event type
  event_type: str = "tool_call"
  iteration: int
  tool_name: str
  arguments: dict

class ToolResultEvent(BaseModel):  # SSE event type
  event_type: str = "tool_result"
  iteration: int
  tool_name: str
  result_summary: str  # short human-readable summary, not full result

class AgentCompleteEvent(BaseModel):  # SSE event type
  event_type: str = "complete"
  result: AgentResult

═══════════════════════════════════════════════════════════════════════
BACKEND SERVICES — FULL SPECIFICATION
═══════════════════════════════════════════════════════════════════════

requirements.txt (pin these exact versions):
  fastapi==0.111.0
  uvicorn[standard]==0.29.0
  pydantic==2.7.1
  pydantic-settings==2.2.1
  azure-identity==1.16.0
  azure-storage-blob==12.27.1
  azure-ai-documentintelligence==1.0.2
  azure-cosmos==4.6.0
  azure-servicebus==7.12.1
  azure-search-documents==11.6.0
  azure-keyvault-secrets==4.8.0
  azure-ai-contentsafety==1.0.0
  openai>=1.51.0
  redis==5.0.4
  numpy==1.26.4
  requests==2.32.4
  python-dotenv==1.0.0
  structlog==24.1.0
  opencensus-ext-azure==1.1.13

config.py:
  pydantic-settings BaseSettings. All values from env vars / Key Vault refs.
  BLOB_URL, DOC_INTEL_ENDPOINT, DOC_INTEL_KEY
  AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY  (← Foundry resource, NOT original)
  CHAT_MODEL_DEPLOYMENT_NAME = "gpt-4o"
  EMBEDDING_MODEL_DEPLOYMENT_NAME = "text-embedding-ada-002"
  COSMOS_ENDPOINT, COSMOS_DATABASE = "ats-db"
  SEARCH_ENDPOINT, SEARCH_INDEX_NAME = "jd-embeddings"
  SERVICE_BUS_NAMESPACE, QUEUE_NAME = "ats-agent-jobs"
  REDIS_URL
  TRANSLATOR_ENDPOINT, TRANSLATOR_KEY
  CONTENT_SAFETY_ENDPOINT, CONTENT_SAFETY_KEY
  APPLICATIONINSIGHTS_CONNECTION_STRING
  AGENT_MAX_ITERATIONS = 12

app/main.py:
  FastAPI lifespan: on startup, start background worker (asyncio task)
  Include routers: upload, score, health
  CORS middleware (Static Web Apps URL + localhost:5173)
  Application Insights middleware (opencensus)
  Request ID middleware (UUID, returned in X-Request-ID header)
  Structured logging with structlog (JSON format, includes request_id)

routers/upload.py:
  POST /api/upload (multipart: file + job_description)
  - Validate: PDF or DOCX only, max 10MB
  - Upload to Blob "resumes-raw"
  - Create Cosmos "jobs" document:
    { id, status: "queued", filename, job_description, created_at }
  - Return immediately: { job_id, status: "queued" }
  NOTE: Azure Function blob trigger will detect upload → enqueue to Service Bus

routers/score.py:
  GET /api/score/{job_id}      → fetch Cosmos jobs doc + scores doc
  GET /api/score/{job_id}/stream → SSE endpoint
    Open asyncio.Queue for this job_id
    Register queue in a global SSE registry (dict keyed by job_id)
    Stream events as "data: {json}\n\n" until AgentCompleteEvent received
    Timeout after 5 minutes

services/translator_service.py:
  async detect(text: str) -> dict
    POST to Azure Translator /detect endpoint
    Headers: Ocp-Apim-Subscription-Key, Ocp-Apim-Subscription-Region
    Return { language_code, language_name, confidence }

  async translate(text: str, source_language: str) -> dict
    POST to Azure Translator /translate endpoint
    target language always "en"
    Return { translated_text, source_language }

services/content_safety_service.py:
  async analyze(text: str) -> dict
    Use azure-ai-contentsafety SDK ContentSafetyClient
    AnalyzeTextOptions with text[:5000]
    Also run simple regex PII detection:
      - email: r'[\w.-]+@[\w.-]+\.\w+'
      - phone: r'\+?[\d\s\-\(\)]{10,}'
      - Replace matches with [PII_REDACTED]
    Return { sanitized_text, pii_detected, pii_categories, safety_flagged }

services/openai_service.py:
  AzureOpenAI client with AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_KEY (Foundry values)
  CRITICAL NOTE IN CODE: Add this comment block at the top of the file:
  """
  AZURE OPENAI FOUNDRY ARCHITECTURE NOTE:
  When models are deployed via the Azure AI Foundry Portal, they are provisioned
  in an auto-created Foundry-managed resource — NOT in the original Azure OpenAI
  resource you created in the portal. AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY
  must be retrieved from:
  Azure Portal → [Foundry resource] → Resource Management → Keys and Endpoint
  NOT from the original Azure OpenAI resource, and NOT from the Foundry Portal UI.
  Using the wrong endpoint causes: DeploymentNotFound 404.
  """

  async score_resume(jd_text, resume_text) -> dict  (same spec as previous prompt)
  async compute_similarity(jd_text, resume_text) -> dict  (with Redis cache)
  async generate_summary(args: dict) -> dict  (2-3 sentence plain English)

services/search_service.py:
  Azure AI Search index schema for "jd-embeddings":
    fields: id (key), job_id, jd_text, embedding (Collection(Edm.Single), dims=1536,
            searchable=true, vectorSearchProfile="ats-vector-profile")
  
  async upsert_jd_embedding(job_id, jd_text, embedding)
  async find_similar(resume_embedding: list[float], top_k: int) -> dict

services/cosmos_service.py:
  Containers: jobs, candidates, scores, agent_traces
  
  async create_job(job_id, filename, jd_text) -> dict
  async update_job_status(job_id, status, **kwargs)
  async save_score(job_id, agent_result: AgentResult) -> str
  async save_agent_trace(job_id, trace: list[AgentTraceStep])
  async flag_job(job_id, reason, severity) -> dict
  async get_job(job_id) -> dict

worker.py:
  async consume_queue():
    ServiceBusClient receive loop (max_message_count=1)
    Parse message: { job_id, blob_path, jd_text }
    
    Get SSE queue from global registry (or create one)
    
    Instantiate AgentRunner(job_id, blob_path, jd_text, sse_queue)
    Update Cosmos job status → "agent_running"
    
    result = await agent_runner.run()
    
    await cosmos_service.save_score(job_id, result)
    await cosmos_service.save_agent_trace(job_id, result.agent_trace)
    await cosmos_service.update_job_status(job_id, "completed")
    
    Push AgentCompleteEvent to sse_queue
    Complete Service Bus message on success
    Abandon with exponential backoff (3 retries, 2^attempt seconds) on failure

function_trigger/function_app.py:
  Azure Function blob trigger on "resumes-raw/{name}"
  On trigger:
    - Query Cosmos DB "jobs" container for document where filename == name
    - Send Service Bus message: { job_id, blob_path: f"resumes-raw/{name}", jd_text }
  Use DefaultAzureCredential for all SDK calls

═══════════════════════════════════════════════════════════════════════
TERRAFORM — FULL SPECIFICATION
═══════════════════════════════════════════════════════════════════════

providers.tf:
  azurerm (~> 3.90), azuread (~> 2.47)
  backend "azurerm" for remote state

variables.tf — all variables:
  project_name (default "ats-agent")
  environment (default "dev")
  location (default "swedencentral")
  openai_foundry_endpoint (sensitive)
  openai_foundry_key (sensitive)
  translator_key (sensitive)
  content_safety_key (sensitive)
  allowed_ip_ranges (list)

main.tf — provision in order:
  1. azurerm_resource_group
  2. azurerm_storage_account + containers (resumes-raw, reports)
  3. azurerm_key_vault + secrets for all sensitive values
  4. azurerm_cognitive_account kind="FormRecognizer" S0 (Doc Intelligence)
  5. azurerm_cognitive_account kind="OpenAI" S0
  6. azurerm_cognitive_account kind="TextTranslation" S1 (Translator)
  7. azurerm_cognitive_account kind="ContentSafety" S0
  8. azurerm_search_service Standard tier, 1 replica
  9. azurerm_cosmosdb_account + database + 4 containers:
     jobs (pk: /id), candidates (pk: /id),
     scores (pk: /job_id), agent_traces (pk: /job_id)
  10. azurerm_servicebus_namespace Standard + queue "ats-agent-jobs"
      dead_letter_on_message_expiration = true
      max_delivery_count = 3
  11. azurerm_redis_cache C1 Basic
  12. azurerm_container_registry Basic
  13. azurerm_log_analytics_workspace
  14. azurerm_application_insights (linked to log analytics)
  15. azurerm_container_app_environment
  16. azurerm_container_app (FastAPI backend)
      SystemAssigned identity
      env vars via secretref from Key Vault
      ingress: external=true, target_port=8000
      min_replicas=1, max_replicas=10
      KEDA scale rule: azure-servicebus, queue "ats-agent-jobs", threshold=5
  17. azurerm_service_plan + azurerm_linux_function_app (blob trigger)
      SystemAssigned identity
  18. azurerm_api_management Developer SKU
      API pointing to Container App ingress URL
      rate-limit policy: 100 calls / 60 seconds / IP
  19. azurerm_static_site Free tier
  20. azurerm_cdn_profile + azurerm_cdn_endpoint (Standard Microsoft)

Role assignments for Container App SystemAssigned identity:
  Storage Blob Data Contributor → storage account
  Cognitive Services Contributor → Doc Intelligence
  Cognitive Services OpenAI Contributor → OpenAI resource
  Cognitive Services User → Translator resource
  Cognitive Services User → Content Safety resource
  Search Index Data Contributor → AI Search
  Cosmos DB Built-in Data Contributor → Cosmos account
  Azure Service Bus Data Owner → Service Bus namespace
  Key Vault Secrets User → Key Vault

Role assignments for Function App SystemAssigned identity:
  Storage Blob Data Reader → storage account
  Azure Service Bus Data Sender → Service Bus namespace
  Cosmos DB Built-in Data Reader → Cosmos account

outputs.tf: resource_group_name, container_app_url, static_web_app_url,
  api_management_gateway_url, key_vault_uri, cosmos_endpoint,
  search_endpoint, application_insights_connection_string

═══════════════════════════════════════════════════════════════════════
FRONTEND — FULL SPECIFICATION
═══════════════════════════════════════════════════════════════════════

Tech: React 18, TypeScript, Vite, Tailwind CSS, Lucide React

src/api/client.ts:
  Axios instance, baseURL from import.meta.env.VITE_API_BASE_URL
  uploadResume(file, jobDescription) → POST /api/upload
  getScore(jobId) → GET /api/score/{job_id}
  useAgentStream(jobId): custom React hook
    Opens EventSource to GET /api/score/{job_id}/stream
    Parses events: tool_call, tool_result, complete
    Returns { toolCalls, toolResults, result, status }

src/components/AgentTracePanel.tsx:
  Live panel showing agent reasoning as it happens (via SSE)
  For each tool_call event: render a card showing:
    - Tool name (with icon per tool type)
    - Arguments summary (truncated)
    - Status: pending / complete / error
  For each tool_result event: update corresponding card with result summary
  Animate cards in with subtle fade — use CSS transitions, no animation libraries
  Show iteration counter: "Agent step 3 of 12 max"
  Scroll to latest entry automatically

src/components/ScoreGauge.tsx:
  SVG circular gauge, score 0-100
  Color: red (0-40), amber (41-70), green (71-100)
  Animated stroke-dashoffset on score arrival

src/components/KeywordBadges.tsx:
  matched: green badge with check, missing: red badge with X

src/components/ScoreBreakdown.tsx:
  Horizontal bars: keyword_match/40, experience_alignment/30,
  skills_coverage/30, semantic_similarity (0-1 scaled to 0-10)

src/pages/Home.tsx:
  Layout: left column (upload + JD input + AgentTracePanel),
          right column (ScoreGauge + ScoreBreakdown + KeywordBadges +
                        fit_summary paragraph + human review badge if flagged)
  State machine: idle → uploading → agent_running → complete → error
  On upload success: open SSE stream, feed events to AgentTracePanel
  On AgentCompleteEvent: render full results in right column
  Show human_review_required banner if flagged (amber warning style)
  Show language_detected badge if non-English was detected and translated
  Show pii_detected info badge if PII was found and redacted

═══════════════════════════════════════════════════════════════════════
CI/CD PIPELINES
═══════════════════════════════════════════════════════════════════════

.github/workflows/terraform.yml:
  Trigger: PR and push to main (paths: infra/**)
  plan job (on PR): terraform init → validate → plan
  apply job (on main merge): terraform apply -auto-approve
  OIDC auth to Azure (no stored client_secret)

.github/workflows/backend.yml:
  Trigger: push to main (paths: backend/**)
  test: pytest tests/ with mocked Azure SDK calls
        Minimum 5 unit tests:
          1. test_agent_runner_calls_extract_first
          2. test_agent_runner_translates_non_english
          3. test_agent_runner_flags_low_score
          4. test_agent_runner_max_iterations_triggers_flag
          5. test_tool_executor_retries_on_failure
  build-push: docker build → az acr login → docker push
  deploy: az containerapp update --image

.github/workflows/frontend.yml:
  Trigger: push to main (paths: frontend/**)
  build: npm ci → npm run build
  deploy: Azure/static-web-apps-deploy@v1

═══════════════════════════════════════════════════════════════════════
README.md — REQUIRED SECTIONS
═══════════════════════════════════════════════════════════════════════

1. What makes this a genuine AI agent (not a pipeline)
2. Architecture overview — all layers described in prose
3. Agent reasoning loop explained — tool list, goal satisfaction criteria,
   max iteration safety, self-correction behavior
4. Prerequisites (Azure CLI, Terraform >= 1.6, Docker, Node 20, Python 3.11)
5. Quick start (clone → terraform init/apply → docker build/push → npm run dev)
6. Environment variables reference table (all vars, descriptions, where to find values)
7. CRITICAL: Azure OpenAI Foundry architecture note
   (explain Foundry resource vs original OpenAI resource — same text as code comment)
8. API reference — all endpoints with curl examples
9. Agent tool reference — all 9 tools, what triggers each, example outputs
10. Terraform module reference
11. Cost estimate table (all services, estimated monthly cost at low usage)
12. Troubleshooting:
    - Foundry DeploymentNotFound 404
    - Service Bus KEDA scale rule not triggering
    - Content Safety SDK authentication
    - Agent stuck in loop / max iterations
    - SSE stream closes prematurely
    - AI Search index not created (timing issue after Terraform apply)

═══════════════════════════════════════════════════════════════════════
CRITICAL IMPLEMENTATION RULES — NEVER VIOLATE THESE
═══════════════════════════════════════════════════════════════════════

1. ZERO hardcoded credentials anywhere. All secrets via env vars or Key Vault refs.

2. DefaultAzureCredential is the primary auth mechanism for all Azure SDK clients.
   API keys (DOC_INTEL_KEY, AZURE_OPENAI_KEY, TRANSLATOR_KEY, CONTENT_SAFETY_KEY)
   are loaded from Key Vault at startup via SecretClient, stored in config,
   and passed to SDK clients — never inlined.

3. FOUNDRY ARCHITECTURE (read carefully):
   AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY MUST point to the Foundry-managed
   resource auto-created when models are deployed via Foundry Portal.
   Source: Azure Portal → Foundry resource → Keys and Endpoint.
   NOT from the original Azure OpenAI resource. NOT from Foundry Portal UI.
   Add this as a comment in openai_service.py AND in the README.

4. The agent loop is the ONLY orchestrator. Do not add any hardcoded if/else
   logic that routes the pipeline (e.g. "if language != en then translate").
   That decision belongs to the agent. The agent's system prompt guides it.
   The tools just execute what the agent decides.

5. ALL I/O in the FastAPI app and worker must be async. Use asyncio.gather()
   for any parallel tool calls the agent may issue in the same iteration.

6. Every log line within the agent loop must include job_id and iteration number.
   Use structlog with JSON renderer. Never use print().

7. The Service Bus worker must use exponential backoff retry (2^attempt seconds,
   max 3 attempts) before dead-lettering. Dead-lettered messages must be logged
   as ERROR with full exception context.

8. SSE events must be valid: "data: {json_string}\n\n" format.
   Each event must include event_type field. Client must handle all three types:
   tool_call, tool_result, complete.

9. Docker image: multi-stage build. Builder installs deps. Final stage copies
   only site-packages + app/. Final image must be under 500MB.

10. Terraform naming convention: "${var.project_name}-${var.environment}-<type>"
    for ALL resources.

11. Python: flake8 compliant, max line length 100.
    TypeScript: ESLint + typescript-eslint rules. No any types.

12. Generate every file completely. No placeholder comments.
    No "# TODO", no "# implement later", no "pass".
    Every function body must be fully implemented.

Start with infra/ Terraform files. Then backend/. Then frontend/. Then CI/CD.
Then README.md. Output each file preceded by its full path as a header.
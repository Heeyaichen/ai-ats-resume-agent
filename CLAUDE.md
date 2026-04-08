# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered ATS (Applicant Tracking System) Resume Screening Agent. Accepts PDF/DOCX resume uploads and job descriptions, runs an agentic reasoning loop using Azure OpenAI function calling, streams agent progress via SSE, and produces recruiter-readable ATS reports.

Project name: `AI-ATS-RESUME-AGENT`.

Filesystem workspace root: `ai-ats-resume-agent/`.

Implementation code lives at the repository root. Implementation follows a phased order defined in design spec Section 16.

## Repository Structure

Implementation directories live at the repository root:
- `backend/` — FastAPI Python app (app/, tests/, function_trigger/, Dockerfile, requirements.in)
- `frontend/` — React 18 + TypeScript + Vite SPA (src/, package.json)
- `infra/` — Terraform IaC (modules for ai_services, compute, data, networking, observability, security, storage)
- `.github/workflows/` — CI/CD pipelines (terraform.yml, backend.yml, frontend.yml)

## Design Specifications

- `implementation_prompt.md` — Original implementation instructions (827 lines)
- `docs/superpowers/specs/2026-04-08-ats-agent-design.md` — Authoritative production design spec (1040 lines). **This file supersedes the original prompt** where they conflict.

Key corrections from the design spec:
- **PII detection**: Use Azure AI Language (NOT Content Safety) for PII redaction. Content Safety is only for harmful-content moderation.
- **Agent model**: "Guarded agent" — model chooses tools, runtime enforces safety/completeness invariants (not a hardcoded pipeline, not unrestricted).
- **Blob paths**: Use `resumes-raw/{job_id}/{safe_filename}`, derive job_id from blob path.
- **Tool naming**: Canonical 9 tools (Section 4.2 of design spec). `get_embedding` and `search_similar_jds` from the original prompt are obsolete.

## Tech Stack

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Lucide React — hosted on Azure Static Web Apps + Azure CDN
- **API**: FastAPI (Python 3.11) on Azure Container Apps
- **Worker**: Container Apps worker consuming Azure Service Bus queue
- **Function**: Azure Function blob trigger → enqueues Service Bus messages
- **Agent**: Azure OpenAI gpt-4o with function calling (streaming), max 12 iterations
- **AI Services**: Document Intelligence (text extraction), Translator (language detection/translation), AI Language (PII), Content Safety (moderation), OpenAI embeddings (ada-002, 1536 dims), AI Search (vector similarity)
- **Data**: Cosmos DB NoSQL, Blob Storage, Redis (embedding cache, TTL 1hr)
- **Infra**: Terraform (>=1.6), GitHub Actions CI/CD, Azure Key Vault, Managed Identity + RBAC
- **Auth**: Microsoft Entra ID (SPA sign-in, APIM JWT validation)
- **API Gateway**: Azure API Management (rate limiting, JWT policy)
- **Observability**: Azure Monitor, Application Insights, Log Analytics
- **Default region**: `swedencentral`

## Architecture Layers

```
SPA (React) → CDN → Static Web Apps
                    ↓
              API Management (JWT, rate limit)
                    ↓
              FastAPI (Container Apps) → Blob Storage → Function → Service Bus
                    ↑                                              ↓
              SSE stream ← Worker (guarded agent loop) ←──────────┘
                              ↓
                    Azure OpenAI + 9 tool functions
                    (Document Intelligence, Translator, AI Language,
                     Content Safety, Embeddings, AI Search, Cosmos DB)
```

## The 9 Canonical Agent Tools

1. `extract_resume_text` — Azure AI Document Intelligence
2. `detect_language` — Azure AI Translator detect
3. `translate_text` — Azure AI Translator translate (target: en)
4. `check_pii_and_safety` — Azure AI Language (PII) + Content Safety (moderation)
5. `score_resume` — Azure OpenAI chat completion (0-100, breakdown: 40 keyword + 30 experience + 30 skills)
6. `compute_semantic_similarity` — Azure OpenAI embeddings + Redis cache
7. `search_similar_candidates` — Azure AI Search vector query
8. `flag_for_human_review` — Cosmos DB review flag write
9. `generate_fit_summary` — Azure OpenAI plain English paragraph

## Agent Guardrail Rules

The runtime enforces these invariants (the model does NOT decide these):
- `extract_resume_text` must complete before tools needing resume text
- `check_pii_and_safety` must complete before scoring/embedding/summary
- Non-English resumes require `translate_text` or human review flag
- `score_resume`, `compute_semantic_similarity`, `generate_fit_summary` must all complete
- Auto-flag for human review when: score < 30, confidence < 0.6, safety flagged, extraction confidence low, max iterations hit, or missing required fields
- Max 12 iterations, max 2 retries per tool call
- All tool I/O validated against Pydantic models
- Never persist raw resume text in logs or traces — only sanitized summaries

## Cosmos DB Containers

- `jobs` — job records with status tracking
- `candidates` — candidate data
- `scores` — scoring results
- `agent_traces` — sanitized agent reasoning traces (audit artifact)
- `review_flags` — human review queue

## Azure OpenAI Configuration

Required env vars:
- `AZURE_OPENAI_ENDPOINT` — Must match the correct Azure OpenAI resource (not Foundry proxy if deployment names differ)
- `AZURE_OPENAI_KEY` or managed identity
- `CHAT_MODEL_DEPLOYMENT_NAME` — gpt-4o deployment
- `EMBEDDING_MODEL_DEPLOYMENT_NAME` — text-embedding-ada-002 deployment

Backend must validate endpoint/deployment resolution at startup and fail with a clear `DeploymentNotFound` error.

## Data Retention

90-day default for raw resumes, reports, and detailed traces.

## Environments

Two Terraform-managed environments: `dev` and `prod` with separate state, Key Vaults, app registrations, and resource names.

"""Pydantic models for agent tool inputs and outputs.

These define the contract between the agent's function-calling layer
and the Azure service adapters. Every tool call is validated against
these models before execution, and every tool result is validated
after execution (design spec Section 4.1).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── extract_resume_text ────────────────────────────────────────────

class ExtractResumeTextInput(BaseModel):
    blob_path: str


class ExtractResumeTextOutput(BaseModel):
    text: str
    page_count: int
    confidence: float = Field(ge=0.0, le=1.0)


# ── detect_language ────────────────────────────────────────────────

class DetectLanguageInput(BaseModel):
    text: str


class DetectLanguageOutput(BaseModel):
    language_code: str
    language_name: str
    confidence: float = Field(ge=0.0, le=1.0)


# ── translate_text ─────────────────────────────────────────────────

class TranslateTextInput(BaseModel):
    text: str
    source_language: str


class TranslateTextOutput(BaseModel):
    translated_text: str
    source_language: str


# ── check_pii_and_safety ───────────────────────────────────────────

class CheckPIIAndSafetyInput(BaseModel):
    text: str


class CheckPIIAndSafetyOutput(BaseModel):
    sanitized_text: str
    pii_detected: bool
    pii_categories: list[str] = Field(default_factory=list)
    safety_flagged: bool
    safety_categories: list[str] = Field(default_factory=list)


# ── score_resume ───────────────────────────────────────────────────

class ScoreResumeInput(BaseModel):
    job_description: str
    resume_text: str


class ScoreResumeBreakdown(BaseModel):
    keyword_match: int = Field(ge=0, le=40)
    experience_alignment: int = Field(ge=0, le=30)
    skills_coverage: int = Field(ge=0, le=30)


class ScoreResumeOutput(BaseModel):
    score: int = Field(ge=0, le=100)
    breakdown: ScoreResumeBreakdown
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


# ── compute_semantic_similarity ────────────────────────────────────

class ComputeSemanticSimilarityInput(BaseModel):
    job_description: str
    resume_text: str


class ComputeSemanticSimilarityOutput(BaseModel):
    similarity_score: float
    cache_hit: bool
    resume_embedding_ref: str
    jd_embedding_ref: str


# ── search_similar_candidates ──────────────────────────────────────

class SearchSimilarCandidatesInput(BaseModel):
    resume_embedding_ref: str
    top_k: int = Field(default=3, ge=1, le=10)


class SimilarCandidateResult(BaseModel):
    candidate_id: str
    job_id: str
    score: int
    similarity: float


class SearchSimilarCandidatesOutput(BaseModel):
    similar_candidates: list[SimilarCandidateResult] = Field(default_factory=list)


# ── flag_for_human_review ──────────────────────────────────────────

class FlagForHumanReviewInput(BaseModel):
    job_id: str
    reason: str
    severity: str = Field(default="medium", pattern="^(low|medium|high)$")


class FlagForHumanReviewOutput(BaseModel):
    review_id: str
    flagged: bool


# ── generate_fit_summary ───────────────────────────────────────────

class GenerateFitSummaryInput(BaseModel):
    score: int
    matched_keywords: list[str]
    missing_keywords: list[str]
    job_description: str
    resume_text: str


class GenerateFitSummaryOutput(BaseModel):
    summary: str

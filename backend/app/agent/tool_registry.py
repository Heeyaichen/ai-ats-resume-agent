"""Tool registry — OpenAI function-calling tool schemas.

Design spec Section 4.2: canonical 9 tools. Obsolete aliases
(get_embedding, search_similar_jds) are rejected with explicit errors.
Design spec Section 4.4: defines OpenAI tool schemas.
"""

from __future__ import annotations

from typing import Any

# Obsolete tool names from the original prompt — must not be exposed.
_OBSOLETE_ALIASES: dict[str, str] = {
    "get_embedding": "compute_semantic_similarity",
    "search_similar_jds": "search_similar_candidates",
}

CANONICAL_TOOL_NAMES: set[str] = {
    "extract_resume_text",
    "detect_language",
    "translate_text",
    "check_pii_and_safety",
    "score_resume",
    "compute_semantic_similarity",
    "search_similar_candidates",
    "flag_for_human_review",
    "generate_fit_summary",
}


def get_tool_schemas() -> list[dict[str, Any]]:
    """Return the OpenAI function-calling tool definitions for all 9 tools.

    Each tool definition follows the OpenAI function calling schema format.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "extract_resume_text",
                "description": (
                    "Extract text from the uploaded resume PDF or DOCX file. "
                    "This must be the first tool called for every job."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "blob_path": {
                            "type": "string",
                            "description": "Blob path like resumes-raw/{job_id}/{filename}",
                        },
                    },
                    "required": ["blob_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "detect_language",
                "description": (
                    "Detect the language of the provided text. "
                    "Uses the first 500 characters of input."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Text to detect language for.",
                        },
                    },
                    "required": ["text"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "translate_text",
                "description": (
                    "Translate non-English text to English. "
                    "Call after detect_language returns a non-English code."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Text to translate.",
                        },
                        "source_language": {
                            "type": "string",
                            "description": "ISO language code detected by detect_language.",
                        },
                    },
                    "required": ["text", "source_language"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "check_pii_and_safety",
                "description": (
                    "Check text for personally identifiable information and harmful content. "
                    "Returns sanitized text. Must complete before scoring or embedding tools."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Text to check for PII and safety issues.",
                        },
                    },
                    "required": ["text"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "score_resume",
                "description": (
                    "Score the resume against the job description. "
                    "Returns score 0-100 with keyword/experience/skills breakdown."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "job_description": {
                            "type": "string",
                            "description": "The job description text.",
                        },
                        "resume_text": {
                            "type": "string",
                            "description": "The sanitized resume text.",
                        },
                    },
                    "required": ["job_description", "resume_text"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "compute_semantic_similarity",
                "description": (
                    "Compute semantic similarity between the job description and resume "
                    "using embeddings. Results are cached in Redis."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "job_description": {
                            "type": "string",
                            "description": "The job description text.",
                        },
                        "resume_text": {
                            "type": "string",
                            "description": "The sanitized resume text.",
                        },
                    },
                    "required": ["job_description", "resume_text"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_similar_candidates",
                "description": (
                    "Search for historically similar candidates using vector search. "
                    "Optional for completion — returns empty list if skipped."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "resume_embedding_ref": {
                            "type": "string",
                            "description": "Reference to the resume embedding from compute_semantic_similarity.",
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of similar candidates to return. Default 3.",
                            "default": 3,
                        },
                    },
                    "required": ["resume_embedding_ref"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "flag_for_human_review",
                "description": (
                    "Flag the current job for human review. "
                    "Call when score is low, confidence is low, safety is flagged, "
                    "or the agent cannot complete normally."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "job_id": {
                            "type": "string",
                            "description": "The job ID.",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Human-readable reason for the flag.",
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                            "description": "Severity level. Default medium.",
                            "default": "medium",
                        },
                    },
                    "required": ["job_id", "reason"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "generate_fit_summary",
                "description": (
                    "Generate a 2-3 sentence recruiter-readable fit summary. "
                    "Requires score, keywords, JD, and resume text."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "score": {
                            "type": "integer",
                            "description": "The resume score (0-100).",
                        },
                        "matched_keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Keywords matched in the resume.",
                        },
                        "missing_keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Keywords missing from the resume.",
                        },
                        "job_description": {
                            "type": "string",
                            "description": "The job description text.",
                        },
                        "resume_text": {
                            "type": "string",
                            "description": "The sanitized resume text.",
                        },
                    },
                    "required": ["score", "matched_keywords", "missing_keywords",
                                 "job_description", "resume_text"],
                },
            },
        },
    ]


def validate_tool_name(name: str) -> str:
    """Validate a tool name. Returns the canonical name or raises ValueError."""
    if name in _OBSOLETE_ALIASES:
        raise ValueError(
            f"Tool '{name}' is obsolete. Use '{_OBSOLETE_ALIASES[name]}' instead."
        )
    if name not in CANONICAL_TOOL_NAMES:
        raise ValueError(
            f"Unknown tool '{name}'. Canonical tools: {sorted(CANONICAL_TOOL_NAMES)}"
        )
    return name

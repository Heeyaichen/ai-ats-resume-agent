"""Tests for application configuration."""

from __future__ import annotations


import pytest

from backend.app.config import Settings, Environment


class TestSettings:
    def test_required_field_missing_raises(self) -> None:
        """azure_openai_endpoint is required and has no default."""
        with pytest.raises(Exception):
            Settings()  # type: ignore[call-arg]

    def test_defaults(self) -> None:
        s = Settings(azure_openai_endpoint="https://test.openai.azure.com/")
        assert s.environment == Environment.DEV
        assert s.version == "0.1.0"
        assert s.agent_max_iterations == 12
        assert s.agent_max_retries_per_tool == 2
        assert s.max_upload_size_bytes == 10 * 1024 * 1024
        assert s.max_jd_length == 50_000
        assert s.allowed_extensions == (".pdf", ".docx")
        assert s.retention_days == 90
        assert s.cosmos_database_name == "ats-db"
        assert s.servicebus_queue_name == "ats-agent-jobs"
        assert s.search_index_name == "candidate-embeddings"
        assert s.redis_embedding_ttl_seconds == 3600

    def test_environment_enum(self) -> None:
        s = Settings(
            azure_openai_endpoint="https://test.openai.azure.com/",
            environment="prod",
        )
        assert s.environment == Environment.PROD

    def test_invalid_environment_raises(self) -> None:
        with pytest.raises(Exception):
            Settings(
                azure_openai_endpoint="https://test.openai.azure.com/",
                environment="staging",
            )

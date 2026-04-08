"""Shared test fixtures."""

from __future__ import annotations

import pytest

from backend.app.config import Settings


@pytest.fixture
def settings() -> Settings:
    """Settings with the minimum required fields for testing."""
    return Settings(
        azure_openai_endpoint="https://test.openai.azure.com/",
        azure_openai_key="test-key",
        chat_model_deployment_name="gpt-4o",
        embedding_model_deployment_name="text-embedding-ada-002",
    )

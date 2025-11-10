"""Application configuration helpers.

This module centralises environment-derived configuration values used across
this lightweight AI coding workflow implementation. Values are exposed as
class-level attributes for ease of import while keeping validation logic in a
single place.
"""

from __future__ import annotations

import os
from typing import Any, Dict


class Config:
    """Container for application configuration values."""

    # AI configuration
    ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
    ANTHROPIC_BASE_URL: str | None = os.getenv("ANTHROPIC_BASE_URL")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "claude-3-sonnet-20240229")

    # Git configuration
    GIT_USERNAME: str = os.getenv("GIT_USERNAME", "ai-coder-bot")
    GIT_EMAIL: str = os.getenv("GIT_EMAIL", "ai-coder@example.com")
    GITLAB_API_TOKEN: str | None = os.getenv("GITLAB_API_TOKEN")

    # Webhook configuration
    WEBHOOK_URL: str | None = os.getenv("WEBHOOK_URL")
    WEBHOOK_SECRET: str | None = os.getenv("WEBHOOK_SECRET")

    # Execution configuration
    WORKSPACE_DIR: str = os.getenv("WORKSPACE_DIR", "/workspace")
    MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "3"))

    @classmethod
    def validate(cls) -> bool:
        """Validate that all required configuration values are present.

        Returns:
            True if validation succeeds.

        Raises:
            ValueError: If a required configuration value is missing.
        """

        if not cls.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is required")
        if cls.WEBHOOK_URL is None:
            raise ValueError("WEBHOOK_URL is required for status reporting")
        return True

    @classmethod
    def git_identity(cls) -> Dict[str, str]:
        """Return the Git identity to use for commits."""

        return {"name": cls.GIT_USERNAME, "email": cls.GIT_EMAIL}

    @classmethod
    def as_dict(cls) -> Dict[str, Any]:
        """Return a serialisable snapshot of configuration values."""

        return {
            "ANTHROPIC_API_KEY": cls.ANTHROPIC_API_KEY,
            "ANTHROPIC_BASE_URL": cls.ANTHROPIC_BASE_URL,
            "MODEL_NAME": cls.MODEL_NAME,
            "GIT_USERNAME": cls.GIT_USERNAME,
            "GIT_EMAIL": cls.GIT_EMAIL,
            "GITLAB_API_TOKEN": cls.GITLAB_API_TOKEN,
            "WEBHOOK_URL": cls.WEBHOOK_URL,
            "WEBHOOK_SECRET": cls.WEBHOOK_SECRET,
            "WORKSPACE_DIR": cls.WORKSPACE_DIR,
            "MAX_ITERATIONS": cls.MAX_ITERATIONS,
        }

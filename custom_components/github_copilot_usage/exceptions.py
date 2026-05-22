"""Exceptions for GitHub Copilot Usage."""

from __future__ import annotations


class GitHubCopilotUsageApiError(Exception):
    """Base GitHub Copilot Usage API error."""


class GitHubCopilotUsageAuthenticationError(GitHubCopilotUsageApiError):
    """Raised when GitHub rejects the supplied credentials."""

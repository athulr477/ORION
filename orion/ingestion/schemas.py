"""Pydantic schemas for ingestion webhook payloads and responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Jira Webhook Schemas
# ---------------------------------------------------------------------------


class JiraIssueFields(BaseModel):
    """Subset of Jira issue fields we care about."""

    summary: str = ""
    description: str | None = None


class JiraIssue(BaseModel):
    """Jira issue object embedded in webhook payload."""

    key: str = Field(..., description="e.g. REQ-123")
    fields: JiraIssueFields = Field(default_factory=JiraIssueFields)


class JiraChangeItem(BaseModel):
    """A single field change inside a Jira changelog."""

    field: str = ""
    from_string: str | None = Field(None, alias="fromString")
    to_string: str | None = Field(None, alias="toString")

    model_config = {"populate_by_name": True}


class JiraChangelog(BaseModel):
    """Jira changelog object — present on issue_updated events."""

    items: list[JiraChangeItem] = Field(default_factory=list)


class JiraWebhookPayload(BaseModel):
    """Top-level Jira Cloud webhook payload.

    Supports ``jira:issue_created`` and ``jira:issue_updated`` events.
    """

    webhook_event: str = Field(
        ...,
        alias="webhookEvent",
        description="e.g. jira:issue_created, jira:issue_updated",
    )
    issue: JiraIssue
    changelog: JiraChangelog | None = None

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# GitHub Push Webhook Schemas
# ---------------------------------------------------------------------------


class GitHubCommit(BaseModel):
    """A single commit inside a GitHub push event."""

    id: str = ""
    added: list[str] = Field(default_factory=list)
    modified: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)


class GitHubRepository(BaseModel):
    """Repository metadata from a GitHub push event."""

    full_name: str = ""
    clone_url: str = ""


class GitHubPushPayload(BaseModel):
    """Top-level GitHub push webhook payload."""

    ref: str = ""
    commits: list[GitHubCommit] = Field(default_factory=list)
    repository: GitHubRepository = Field(default_factory=GitHubRepository)


# ---------------------------------------------------------------------------
# Simulate / Mock Payload (for offline demos and Phase 2 verification)
# ---------------------------------------------------------------------------


class SimulateTestFile(BaseModel):
    """A test file with its content, used for simulation/demo mode."""

    file_path: str = Field(..., description="Path to test file in the repo")
    content: str = Field(..., description="Full source code of the test file")


class SimulateGitHubPushPayload(BaseModel):
    """Simulated GitHub push that includes file content directly.

    Used for offline demos and verification since we don't have
    GitHub App token access until Phase 9.
    """

    ref: str = "refs/heads/main"
    repository_name: str = "orion-test-repo"
    test_files: list[SimulateTestFile] = Field(
        ..., description="Test files with their full source code"
    )


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------


class IngestionResult(BaseModel):
    """Response returned by webhook endpoints."""

    status: str = "ok"
    created: int = 0
    updated: int = 0
    linked: int = Field(0, description="Test cases successfully linked to requirements")
    unlinked: int = Field(0, description="Test cases where requirement was not found")
    details: str = ""

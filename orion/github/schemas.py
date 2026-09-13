"""Pydantic schemas for GitHub webhook payload parsing — Phase 9.

Only models the fields Orion actually reads from the pull_request webhook.
Extra fields are silently ignored (model_config extra='ignore').
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class _PRHead(BaseModel):
    """Head commit metadata from a pull_request event."""

    model_config = {"extra": "ignore"}

    sha: str = ""
    ref: str = ""


class _PullRequest(BaseModel):
    """Minimal pull request payload fields."""

    model_config = {"extra": "ignore"}

    number: int = 0
    head: _PRHead = Field(default_factory=_PRHead)
    title: str = ""


class _RepoOwner(BaseModel):
    """Repository owner login."""

    model_config = {"extra": "ignore"}

    login: str = ""


class _Repository(BaseModel):
    """Minimal repository payload fields."""

    model_config = {"extra": "ignore"}

    name: str = ""
    full_name: str = ""
    owner: _RepoOwner = Field(default_factory=_RepoOwner)

    @model_validator(mode="after")
    def _infer_owner_from_full_name(self) -> "_Repository":
        """If owner.login is empty, derive it from full_name (e.g. 'org/repo')."""
        if not self.owner.login and "/" in self.full_name:
            self.owner.login = self.full_name.split("/")[0]
        return self


class _Installation(BaseModel):
    """Installation ID from the webhook payload."""

    model_config = {"extra": "ignore"}

    id: int = 0


class GitHubPRPayload(BaseModel):
    """Top-level GitHub pull_request webhook payload.

    Only the fields Orion needs are modeled; everything else is ignored.
    """

    model_config = {"extra": "ignore"}

    action: str = ""
    pull_request: _PullRequest = Field(default_factory=_PullRequest)
    repository: _Repository = Field(default_factory=_Repository)
    installation: _Installation = Field(default_factory=_Installation)

    @property
    def owner(self) -> str:
        return self.repository.owner.login

    @property
    def repo(self) -> str:
        return self.repository.name

    @property
    def pull_number(self) -> int:
        return self.pull_request.number

    @property
    def head_sha(self) -> str:
        return self.pull_request.head.sha

    @property
    def installation_id(self) -> int:
        return self.installation.id

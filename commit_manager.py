"""Helpers for staging, committing, and pushing code changes."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from git import Actor, GitCommandError, Repo

from config import Config


class CommitManager:
    """Encapsulates high-level commit workflow operations."""

    def __init__(self, repo: Repo | None = None) -> None:
        self._repo: Repo | None = repo

    def attach_repo(self, repo: Repo | str | Path) -> None:
        """Attach to an existing repository instance or path."""

        if isinstance(repo, Repo):
            self._repo = repo
            return
        self._repo = Repo(Path(repo))

    @property
    def repo(self) -> Repo:
        if self._repo is None:
            raise RuntimeError("Repository is not initialised")
        return self._repo

    def stage_changes(self, file_pattern: str = ".") -> bool:
        """Stage changes according to the provided pattern."""

        repo = self.repo
        git = repo.git
        if file_pattern == ".":
            git.add(A=True)
        else:
            git.add(file_pattern)
        return True

    def create_commit(self, message: str) -> str:
        """Create a commit with the staged changes and return its hash."""

        if not message:
            raise ValueError("Commit message cannot be empty")

        repo = self.repo
        if not repo.is_dirty(untracked_files=True):
            raise ValueError("There are no staged changes to commit")

        identity = Config.git_identity()
        author = Actor(identity["name"], identity["email"])
        commit = repo.index.commit(message, author=author, committer=author)
        return commit.hexsha

    def push_changes(self, remote: str = "origin", branch: Optional[str] = None) -> bool:
        """Push the current branch to the remote repository."""

        repo = self.repo
        if branch is None:
            branch = repo.active_branch.name

        try:
            remote_ref = repo.remote(remote)
        except ValueError as exc:
            raise RuntimeError(f"Remote '{remote}' is not configured") from exc

        try:
            results = remote_ref.push(branch)
        except GitCommandError as exc:
            raise RuntimeError(f"Failed to push branch '{branch}': {exc}") from exc

        if not results:
            return False
        return all(result.flags & result.ERROR == 0 for result in results)

    def create_pull_request(self, title: str, description: str) -> dict:
        """Placeholder for pull request creation logic."""

        raise NotImplementedError("Pull request creation is not implemented")

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

    def push_changes(
        self,
        remote: str = "origin",
        branch: Optional[str] = None,
        credentials: Optional[dict] = None,
    ) -> bool:
        """Push the current branch to the remote repository.
        
        Args:
            remote: Remote name (default: "origin")
            branch: Branch name to push (default: current branch)
            credentials: Optional credentials dict with keys:
                - api_token: GitLab/GitHub API token
                - username: Git username
                - password: Git password
        """

        repo = self.repo
        if branch is None:
            branch = repo.active_branch.name

        try:
            remote_ref = repo.remote(remote)
        except ValueError as exc:
            raise RuntimeError(f"Remote '{remote}' is not configured") from exc

        # 如果提供了凭据，临时更新 remote URL
        original_url = None
        if credentials:
            original_url = list(remote_ref.urls)[0]
            auth_url = self._prepare_push_url(original_url, credentials)
            if auth_url != original_url:
                remote_ref.set_url(auth_url)

        try:
            results = remote_ref.push(branch)
        except GitCommandError as exc:
            raise RuntimeError(f"Failed to push branch '{branch}': {exc}") from exc
        finally:
            # 恢复原始 URL（不包含凭据）
            if original_url and credentials:
                try:
                    remote_ref.set_url(original_url)
                except Exception:
                    pass

        if not results:
            return False
        return all(result.flags & result.ERROR == 0 for result in results)

    def _prepare_push_url(self, repo_url: str, credentials: dict) -> str:
        """Prepare repository URL with credentials for push."""
        
        if not repo_url.startswith("http"):
            return repo_url
        
        username = credentials.get("username")
        password = credentials.get("password")
        api_token = credentials.get("api_token")
        auth_segment = None

        if api_token:
            # 对于 GitLab，使用 gitlab-ci-token 作为用户名
            if "gitlab" in repo_url.lower():
                auth_segment = f"gitlab-ci-token:{api_token}"
            else:
                auth_segment = f"oauth2:{api_token}"
        elif username and password:
            auth_segment = f"{username}:{password}"
        elif username:
            auth_segment = username

        if auth_segment:
            scheme, remainder = repo_url.split("//", 1)
            # 移除已存在的认证信息
            if "@" in remainder:
                remainder = remainder.split("@", 1)[1]
            return f"{scheme}//{auth_segment}@{remainder}"

        return repo_url

    def create_pull_request(self, title: str, description: str) -> dict:
        """Placeholder for pull request creation logic."""

        raise NotImplementedError("Pull request creation is not implemented")

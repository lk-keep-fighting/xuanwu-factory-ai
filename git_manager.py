"""Utility helpers for interacting with Git repositories."""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Optional

from git import GitCommandError, Repo


class GitManager:
    """High-level wrapper around Git operations used by the workflow."""

    def __init__(self) -> None:
        self._repo: Repo | None = None
        self.repo_path: Path | None = None

    @property
    def repo(self) -> Repo:
        if self._repo is None:
            raise RuntimeError("Repository is not initialised")
        return self._repo

    async def clone_repository(
        self,
        repo_url: str,
        local_path: str | None = None,
        branch: str | None = "main",
        credentials: Optional[Dict[str, str]] = None,
        retries: int = 3,
    ) -> str:
        """Clone a remote repository.

        Args:
            repo_url: Remote repository URL.
            local_path: Optional path to clone into. If omitted a temporary
                directory will be created.
            branch: The branch to checkout after cloning.
            credentials: Optional credential dictionary. Supported keys:
                ``username``, ``password``, ``api_token``.
            retries: Number of attempts to clone before failing.

        Returns:
            The path to the cloned repository.
        """

        if retries < 1:
            raise ValueError("retries must be a positive integer")

        credentials = credentials or {}
        prepared_url = self._prepare_repo_url(repo_url, credentials)
        last_error: Exception | None = None

        for attempt in range(1, retries + 1):
            target_dir = Path(local_path) if local_path else Path(
                tempfile.mkdtemp(prefix="ai-coder-")
            )
            if target_dir.exists() and any(target_dir.iterdir()):
                shutil.rmtree(target_dir)
                target_dir.mkdir(parents=True, exist_ok=True)
            elif not target_dir.exists():
                target_dir.mkdir(parents=True, exist_ok=True)

            try:
                clone_kwargs: Dict[str, str] = {}
                if branch:
                    clone_kwargs["branch"] = branch
                repo = await asyncio.to_thread(
                    Repo.clone_from,
                    prepared_url,
                    target_dir,
                    **clone_kwargs,
                )
                self._repo = repo
                self.repo_path = target_dir
                if prepared_url != repo_url:
                    try:
                        repo.remotes.origin.set_url(repo_url)
                    except Exception:
                        pass
                return str(target_dir)
            except GitCommandError as exc:
                last_error = exc
                print(f"Clone attempt {attempt}/{retries} failed: {exc}")
                if not local_path:
                    shutil.rmtree(target_dir, ignore_errors=True)
                if attempt >= retries:
                    raise RuntimeError(
                        f"Failed to clone repository after {retries} attempts: {exc}"
                    ) from exc
                await asyncio.sleep(2 ** (attempt - 1))

        assert last_error is not None
        raise last_error

    def create_feature_branch(self, branch_name: str, checkout: bool = True) -> bool:
        """Create and optionally checkout a new feature branch."""

        repo = self.repo
        git = repo.git
        existing_branches = {head.name for head in repo.heads}
        if branch_name in existing_branches:
            if checkout:
                git.checkout(branch_name)
            return False

        git.checkout("-b", branch_name)
        if not checkout:
            # Return to the previous HEAD if checkout was not requested.
            git.checkout("-")
        return True

    def get_repo_structure(self, max_depth: int = 3) -> Dict[str, Dict[str, list[str]]]:
        """Return a simplified view of the repository structure.

        Args:
            max_depth: Maximum directory depth to include in the structure
                response. This avoids overwhelming downstream consumers with
                enormous repositories.
        """

        if self.repo_path is None:
            raise RuntimeError("Repository is not initialised")

        structure: Dict[str, Dict[str, list[str]]] = {}
        base_path = self.repo_path.resolve()

        for root, dirs, files in os.walk(base_path):
            rel_root = Path(root).relative_to(base_path)
            depth = len(rel_root.parts)
            if depth > max_depth:
                dirs[:] = []
                continue
            structure[str(rel_root) if rel_root.parts else "."] = {
                "directories": sorted(dirs),
                "files": sorted(files),
            }
        return structure

    def _prepare_repo_url(self, repo_url: str, credentials: Dict[str, str]) -> str:
        """Prepare a repository URL with credentials when possible."""

        if repo_url.startswith("http"):
            username = credentials.get("username")
            password = credentials.get("password")
            api_token = credentials.get("api_token")
            auth_segment = None

            if api_token:
                auth_segment = f"oauth2:{api_token}"
            elif username and password:
                auth_segment = f"{username}:{password}"
            elif username:
                auth_segment = username

            if auth_segment:
                # Insert credentials before the hostname section of the URL.
                scheme, remainder = repo_url.split("//", 1)
                return f"{scheme}//{auth_segment}@{remainder}"

        return repo_url

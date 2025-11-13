"""Main orchestration logic for the AI coding workflow."""

from __future__ import annotations

import asyncio
import re
import unicodedata
from typing import Any, Dict

from ai_coder import AICoder
from commit_manager import CommitManager
from git_manager import GitManager
from task_status import TaskStatusStore
from webhook_client import WebhookClient


class MainController:
    """Coordinate cloning, coding, validation, and commit workflow."""

    def __init__(self, config: Dict[str, Any], status_store: TaskStatusStore | None = None):
        self.config = config
        self.git_mgr = GitManager()
        self.ai_coder = AICoder(
            api_key=config["api_key"],
            model=config.get("model", "qwen-coder"),
            base_url=config.get("base_url"),
        )
        self.commit_mgr = CommitManager()
        self.webhook = WebhookClient(config["webhook_url"], config.get("webhook_secret"))
        self.status_store = status_store

    async def execute_task(self, task_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the full AI coding workflow for a single task."""

        task_id = task_config["task_id"]
        repo_url = task_config["repo_url"]
        intent = task_config.get("intent", "")
        branch = task_config.get("branch", "main")
        feature_branch_preference = task_config.get("feature_branch")
        feature_branch: str | None = None

        if not repo_url:
            raise ValueError("A repository URL is required")

        await self._notify(task_id, "started", {})

        try:
            await self._notify(task_id, "cloning", {"repo": repo_url, "branch": branch})
            repo_path = await self.git_mgr.clone_repository(
                repo_url,
                branch=branch,
                credentials={
                    "api_token": task_config.get("gitlab_api_token"),
                    "username": task_config.get("git_username"),
                    "password": task_config.get("git_password"),
                },
            )
            feature_branch = self._generate_feature_branch_name(
                feature_branch_preference or intent,
                task_id,
            )
            self.git_mgr.create_feature_branch(feature_branch)

            self.commit_mgr.attach_repo(self.git_mgr.repo)

            await self._notify(task_id, "analyzing", {})
            plan = await self.ai_coder.analyze_requirements(intent, repo_path)

            await self._notify(task_id, "coding", {"plan": plan})
            changes = await self.ai_coder.execute_code_changes(plan, repo_path)

            await self._notify(task_id, "testing", {"changes": changes})
            test_results = await self.ai_coder.validate_changes(repo_path)

            await self._notify(task_id, "committing", {"test_results": test_results})
            self.commit_mgr.stage_changes()

            commit_hash: str | None = None
            push_result: bool | None = None
            try:
                commit_hash = self.commit_mgr.create_commit(f"AI: {intent}")
                push_branch = feature_branch or branch
                push_result = self.commit_mgr.push_changes(branch=push_branch)
            except ValueError:
                # No staged changes – skip commit/push but continue gracefully.
                push_result = False

            result = {
                "task_id": task_id,
                "status": "completed",
                "commit_hash": commit_hash,
                "changes": changes,
                "test_results": test_results,
                "feature_branch": feature_branch,
                "push_result": push_result,
            }
            await self._notify(task_id, "completed", result)
            return result
        except Exception as exc:  # noqa: BLE001 - propagate error details downstream
            error_payload = {
                "task_id": task_id,
                "status": "failed",
                "error": str(exc),
            }
            await self._notify(task_id, "failed", error_payload)
            return error_payload

    def _generate_feature_branch_name(
        self,
        preferred: str | None,
        fallback: str,
    ) -> str:
        source = preferred or fallback or "feature"
        normalized = unicodedata.normalize("NFKD", source)
        ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
        sanitized = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_only).strip("-").lower()

        if not sanitized and fallback:
            fallback_normalized = unicodedata.normalize("NFKD", fallback)
            fallback_ascii = fallback_normalized.encode("ascii", "ignore").decode("ascii")
            sanitized = re.sub(r"[^a-zA-Z0-9]+", "-", fallback_ascii).strip("-").lower()

        if not sanitized:
            sanitized = "feature"

        sanitized = sanitized[:50].strip("-")
        if not sanitized:
            sanitized = "feature"

        existing_branches = {head.name for head in self.git_mgr.repo.heads}
        branch_name = sanitized
        suffix = 1
        while branch_name in existing_branches or len(branch_name) > 50 or not branch_name:
            suffix_fragment = f"-{suffix}"
            base_length = max(1, 50 - len(suffix_fragment))
            base_segment = sanitized[:base_length].rstrip("-")
            if not base_segment:
                base_segment = "feature"
            base_segment = base_segment[:base_length].rstrip("-")
            if not base_segment:
                base_segment = "f"
            branch_name = f"{base_segment}{suffix_fragment}"
            suffix += 1

        return branch_name

    async def _notify(self, task_id: str, status: str, data: Dict[str, Any]) -> None:
        if self.status_store is not None:
            try:
                await self.status_store.update(task_id, status, data)
            except Exception:
                await asyncio.sleep(0)

        try:
            await self.webhook.send_status_update(task_id, status, data)
        except Exception:
            # Webhook failures should not interrupt the primary workflow.
            await asyncio.sleep(0)

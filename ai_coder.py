"""AI assisted coding workflow helpers."""

from __future__ import annotations

import asyncio
import json
import compileall
import os
from pathlib import Path
from typing import Any, Dict, List

import shutil


class AICoder:
    """Coordinate task analysis, execution, and validation."""

    def __init__(self, api_key: str, model: str = "qwen-coder", base_url: str | None = None) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

    async def analyze_requirements(self, intent: str, repo_path: str) -> Dict[str, Any]:
        """Generate a plan for the requested changes (placeholder, actual work done by execute_code_changes)."""
        repo_summary = self._summarise_repository(Path(repo_path))
        return {
            "intent": intent,
            "repo_path": repo_path,
            "files": [entry["path"] for entry in repo_summary.get("files", [])[:10]],
            "changes": [],
            "tests": [],
        }

    async def execute_code_changes(self, plan: Dict[str, Any], repo_path: str) -> Dict[str, Any]:
        """Execute code changes using Qwen Code CLI."""
        intent = plan.get("intent", "")
        
        if not intent:
            return {"applied": [], "skipped": [{"reason": "No task intent provided"}]}
        
        # Check if qwen CLI is available
        qwen_path = shutil.which("qwen")
        if not qwen_path:
            print("Warning: qwen CLI not found, skipping AI coding")
            return {"applied": [], "skipped": [{"reason": "qwen CLI not found"}]}
        
        # Prepare environment variables
        env = os.environ.copy()
        if self.api_key:
            env["OPENAI_API_KEY"] = self.api_key
            print(f"Set OPENAI_API_KEY: {self.api_key[:20]}...")
        if self.base_url:
            env["OPENAI_BASE_URL"] = self.base_url
            print(f"Set OPENAI_BASE_URL: {self.base_url}")
        if self.model:
            env["OPENAI_MODEL"] = self.model
            print(f"Set OPENAI_MODEL: {self.model}")
        
        # Execute qwen CLI
        try:
            print(f"Executing Qwen Code with task: {intent}")
            print(f"Using model: {self.model}")
            
            # Build command arguments
            # qwen uses positional prompt for one-shot mode (non-interactive)
            cmd_args = [
                qwen_path,
                "--yolo",   # Skip permission prompts
                intent,     # Positional prompt
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                cwd=repo_path,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            
            stdout_text = stdout.decode("utf-8", errors="ignore")
            stderr_text = stderr.decode("utf-8", errors="ignore")
            
            if process.returncode == 0:
                print(f"Qwen Code executed successfully")
                print(f"Output: {stdout_text[:500]}")
                return {
                    "applied": ["qwen execution completed"],
                    "skipped": [],
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                }
            else:
                print(f"Qwen Code failed with return code {process.returncode}")
                print(f"Error: {stderr_text[:500]}")
                return {
                    "applied": [],
                    "skipped": [{"reason": f"qwen failed: {stderr_text[:200]}"}],
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                }
        except Exception as exc:
            print(f"Failed to execute qwen: {exc}")
            return {
                "applied": [],
                "skipped": [{"reason": f"Exception: {str(exc)}"}],
            }

    async def validate_changes(self, repo_path: str) -> Dict[str, Any]:
        """Validate modified code via syntax checks and optional tests."""

        try:
            syntax_ok = await asyncio.to_thread(
                compileall.compile_dir,
                repo_path,
                quiet=1,
            )
            compilation_error = None
        except Exception as exc:  # noqa: BLE001 - capture for the result payload
            syntax_ok = False
            compilation_error = str(exc)

        test_runs: List[Dict[str, Any]] = []
        pytest_path = shutil.which("pytest")
        if pytest_path:
            process = await asyncio.create_subprocess_exec(
                pytest_path,
                "--maxfail=1",
                "--disable-warnings",
                "-q",
                cwd=repo_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            test_runs.append(
                {
                    "command": "pytest --maxfail=1 --disable-warnings -q",
                    "returncode": process.returncode,
                    "stdout": stdout.decode("utf-8"),
                    "stderr": stderr.decode("utf-8"),
                }
            )

        result = {"syntax_ok": bool(syntax_ok), "test_runs": test_runs}
        if compilation_error:
            result["compilation_error"] = compilation_error
        return result

    def _summarise_repository(self, repo_path: Path, max_entries: int = 200) -> Dict[str, Any]:
        """Collect a lightweight summary of the repository contents."""

        summary: Dict[str, Any] = {"files": []}
        total = 0
        for path in sorted(repo_path.rglob("*")):
            if path.is_dir():
                continue
            relative = path.relative_to(repo_path).as_posix()
            summary["files"].append({
                "path": relative,
                "size": path.stat().st_size,
            })
            total += 1
            if total >= max_entries:
                summary["truncated"] = True
                break
        summary.setdefault("truncated", False)
        return summary

    def _default_plan(self, intent: str, repo_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback plan when no LLM is available."""

        files = [entry["path"] for entry in repo_summary.get("files", []) if entry["path"].endswith(".py")]
        tests = ["Run pytest" if files else "Run unit tests"]
        return {
            "intent": intent,
            "files": files,
            "changes": [],
            "tests": tests,
        }

    def _build_planning_prompt(self, intent: str, repo_summary: Dict[str, Any]) -> str:
        """Create a planning prompt for the language model."""

        repo_context = json.dumps(repo_summary, ensure_ascii=False, indent=2)
        return (
            "You are assisting an autonomous coding agent. Given the repository "
            "summary and the task intent, produce a JSON plan with the fields "
            "'files', 'changes', and 'tests'. Keep the output strictly valid JSON.\n"
            f"Intent: {intent}\n"
            f"Repository Summary:\n{repo_context}\n"
        )

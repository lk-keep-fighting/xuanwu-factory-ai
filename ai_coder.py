"""AI assisted coding workflow helpers."""

from __future__ import annotations

import asyncio
import json
import compileall
from pathlib import Path
from typing import Any, Dict, List

import shutil

try:
    from anthropic import Anthropic
except ImportError:  # pragma: no cover - dependency may be optional at runtime
    Anthropic = None  # type: ignore


class AICoder:
    """Coordinate task analysis, execution, and validation."""

    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229", base_url: str | None = None) -> None:
        self.model = model
        self.api_key = api_key
        if Anthropic is not None and api_key:
            self.llm_client = Anthropic(api_key=api_key, base_url=base_url)
        else:
            self.llm_client = None

    async def analyze_requirements(self, intent: str, repo_path: str) -> Dict[str, Any]:
        """Generate a plan for the requested changes."""

        repo_summary = self._summarise_repository(Path(repo_path))

        if not self.llm_client:
            return self._default_plan(intent, repo_summary)

        prompt = self._build_planning_prompt(intent, repo_summary)
        try:
            response = await asyncio.to_thread(
                self.llm_client.messages.create,
                model=self.model,
                max_tokens=1024,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
            content = "".join(block.text for block in response.content)
            plan = json.loads(content)
        except Exception:
            plan = self._default_plan(intent, repo_summary)
        return plan

    async def execute_code_changes(self, plan: Dict[str, Any], repo_path: str) -> Dict[str, Any]:
        """Apply code changes described in the plan."""

        repo_base = Path(repo_path)
        applied: List[str] = []
        skipped: List[Dict[str, Any]] = []
        for change in plan.get("changes", []):
            file_path = change.get("file")
            operation = change.get("operation", "write")
            if not file_path:
                skipped.append({"change": change, "reason": "missing file path"})
                continue
            target_path = repo_base / file_path
            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                if operation == "write":
                    target_path.write_text(change.get("content", ""), encoding="utf-8")
                elif operation == "append":
                    with target_path.open("a", encoding="utf-8") as handle:
                        handle.write(change.get("content", ""))
                        if not change.get("content", "").endswith("\n"):
                            handle.write("\n")
                elif operation == "replace":
                    search = change.get("search")
                    replace = change.get("replace", "")
                    if search is None:
                        raise ValueError("replace operation requires 'search' field")
                    original = target_path.read_text(encoding="utf-8") if target_path.exists() else ""
                    if search not in original:
                        raise ValueError("search pattern not found")
                    target_path.write_text(original.replace(search, replace), encoding="utf-8")
                else:
                    raise ValueError(f"Unsupported operation '{operation}'")
                applied.append(f"{operation}:{file_path}")
            except Exception as exc:  # noqa: BLE001 - propagate detail in result payload
                skipped.append({
                    "change": change,
                    "reason": str(exc),
                })
        return {"applied": applied, "skipped": skipped}

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

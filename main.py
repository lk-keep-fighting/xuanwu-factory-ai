"""Entry point for the AI coding automation."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any, Dict

from config import Config
from main_controller import MainController


def _load_task_config() -> Dict[str, Any]:
    if len(sys.argv) > 1:
        return json.loads(sys.argv[1])
    return {
        "task_id": os.getenv("TASK_ID", "task_001"),
        "repo_url": os.getenv("REPO_URL"),
        "intent": os.getenv("TASK_INTENT", ""),
        "webhook_url": Config.WEBHOOK_URL,
        "gitlab_api_token": Config.GITLAB_API_TOKEN,
        "git_username": os.getenv("GIT_USERNAME"),
        "git_password": os.getenv("GIT_PASSWORD"),
        "branch": os.getenv("REPO_BRANCH", "main"),
    }


def _build_controller_config() -> Dict[str, Any]:
    return {
        "api_key": Config.ANTHROPIC_API_KEY,
        "model": Config.MODEL_NAME,
        "base_url": Config.ANTHROPIC_BASE_URL,
        "webhook_url": Config.WEBHOOK_URL,
        "webhook_secret": Config.WEBHOOK_SECRET,
    }


async def async_main() -> None:
    task_config = _load_task_config()
    Config.validate()
    controller = MainController(_build_controller_config())
    result = await controller.execute_task(task_config)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()

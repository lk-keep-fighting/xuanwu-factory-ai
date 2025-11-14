"""Task status tracking and lightweight HTTP endpoint."""

from __future__ import annotations

import asyncio
import copy
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from aiohttp import web


@dataclass(slots=True)
class TaskStatus:
    """Snapshot representing the latest known task state."""

    task_id: str
    status: str
    data: Dict[str, Any]
    updated_at: str


class TaskStatusStore:
    """In-memory store tracking the most recent task status."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._current: Optional[TaskStatus] = None

    async def update(self, task_id: str, status: str, data: Dict[str, Any]) -> TaskStatus:
        """Persist the latest task status and return the snapshot."""

        snapshot = TaskStatus(
            task_id=task_id,
            status=status,
            data=copy.deepcopy(data),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        async with self._lock:
            self._current = snapshot
        return snapshot

    async def snapshot(self) -> Optional[Dict[str, Any]]:
        """Return the most recent status snapshot, if available."""

        async with self._lock:
            if self._current is None:
                return None
            stored = self._current
        payload = asdict(stored)
        payload["is_running"] = stored.status not in {"completed", "failed"}
        return payload

    async def clear(self) -> None:
        """Reset the stored status information."""

        async with self._lock:
            self._current = None


class TaskStatusServer:
    """Minimal aiohttp server exposing the current task status."""

    def __init__(
        self,
        store: TaskStatusStore,
        *,
        host: str = "0.0.0.0",
        port: int = 8080,
        route: str = "/task/status",
    ) -> None:
        self._store = store
        self._host = host
        self._port = port
        self._route = route
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None

    async def __aenter__(self) -> "TaskStatusServer":
        await self.start()
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        await self.stop()

    async def start(self) -> None:
        """Start the aiohttp server if it is not already running."""

        if self._runner is not None:
            return

        self._app = self._build_app()
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self._host, self._port)
        await self._site.start()

    async def stop(self) -> None:
        """Stop the aiohttp server if it is currently running."""

        if self._runner is None:
            return

        if self._site is not None:
            await self._site.stop()
            self._site = None
        await self._runner.cleanup()
        self._runner = None
        self._app = None

    def _build_app(self) -> web.Application:
        app = web.Application()
        app["store"] = self._store
        app.router.add_get(self._route, self._handle_status)
        return app

    async def _handle_status(self, request: web.Request) -> web.StreamResponse:
        store: TaskStatusStore = request.app["store"]
        snapshot = await store.snapshot()
        if snapshot is None:
            return web.json_response(
                {
                    "status": "idle",
                    "task_id": None,
                    "message": "No task is currently running.",
                    "is_running": False,
                }
            )
        return web.json_response(snapshot)

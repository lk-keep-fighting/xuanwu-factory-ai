"""Webhook client responsible for pushing task updates."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any, Dict

import aiohttp


class WebhookClient:
    """Send structured task status updates to an external webhook."""

    def __init__(self, webhook_url: str | None, secret: str | None = None, *, timeout: int = 10, max_retries: int = 5) -> None:
        if not webhook_url:
            raise ValueError("A webhook URL is required")
        self.webhook_url = webhook_url
        self.secret = secret
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries

    async def send_status_update(self, task_id: str, status: str, data: Dict[str, Any]) -> bool:
        """Send a status update to the configured webhook."""

        payload = self.generate_payload(task_id, status, data)
        headers = {"Content-Type": "application/json"}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        if self.secret:
            signature = hmac.new(self.secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
            headers["X-Webhook-Signature"] = signature

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            for attempt in range(1, self.max_retries + 1):
                try:
                    async with session.post(self.webhook_url, data=body, headers=headers) as response:
                        if response.status < 400:
                            return True
                        error_text = await response.text()
                        raise RuntimeError(
                            f"Webhook responded with status {response.status}: {error_text}"
                        )
                except Exception as exc:  # noqa: BLE001 - bubbling up detailed error info
                    if attempt >= self.max_retries:
                        raise
                    await asyncio.sleep(2 ** (attempt - 1))
        return False

    def generate_payload(self, task_id: str, status: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a standardised webhook payload."""

        return {
            "task_id": task_id,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }

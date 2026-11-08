"""Long-term memory through a local ReMe server (agentscope-ai/ReMe). Disabled when REME_URL is empty."""

import logging
from datetime import date

import httpx

log = logging.getLogger("ai-partner.memory")


class Memory:
    def __init__(self, reme_url: str, user_name: str, partner_name: str):
        self.reme_url = reme_url
        self.user_name = user_name
        self.partner_name = partner_name

    @property
    def enabled(self) -> bool:
        return bool(self.reme_url)

    async def recall(self, text: str) -> str:
        if not self.enabled:
            return ""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(f"{self.reme_url}/search", json={"query": text, "limit": 3})
                r.raise_for_status()
                return (r.json().get("answer") or "").strip()
        except (httpx.HTTPError, ValueError) as e:
            log.warning("ReMe search failed: %s", e)
            return ""

    async def remember(self, messages: list[dict]) -> None:
        if not self.enabled or not messages:
            return
        names = {"user": self.user_name, "assistant": self.partner_name}
        payload = {
            "session_id": f"talk-{date.today().isoformat()}",
            "messages": [
                {"role": m["role"], "name": names[m["role"]], "content": m["content"]} for m in messages
            ],
            "memory_hint": f"{self.user_name}の好きなものと近況、パートナーと話したことを日本語で記録する",
        }
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                r = await client.post(f"{self.reme_url}/auto_memory", json=payload)
                r.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("ReMe auto_memory failed: %s", e)

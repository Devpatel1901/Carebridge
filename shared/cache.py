from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis

from shared.config import get_settings


class RedisCache:
    def __init__(self) -> None:
        self._client: aioredis.Redis | None = None

    async def connect(self) -> None:
        settings = get_settings()
        self._client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
        )

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> aioredis.Redis:
        if not self._client:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._client

    async def get(self, key: str) -> str | None:
        return await self.client.get(key)

    async def get_json(self, key: str) -> dict[str, Any] | None:
        raw = await self.client.get(key)
        return json.loads(raw) if raw else None

    async def set(
        self, key: str, value: str, expire_seconds: int | None = None
    ) -> None:
        await self.client.set(key, value, ex=expire_seconds)

    async def set_json(
        self, key: str, value: dict[str, Any], expire_seconds: int | None = None
    ) -> None:
        await self.client.set(key, json.dumps(value), ex=expire_seconds)

    async def delete(self, key: str) -> None:
        await self.client.delete(key)

    async def keys(self, pattern: str) -> list[str]:
        return [k async for k in self.client.scan_iter(match=pattern)]


cache = RedisCache()

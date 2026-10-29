"""Microsoft Agent Framework session history backed by NexaMem."""

import asyncio
import hashlib
import json
import time
from collections.abc import Sequence
from typing import Any

from agent_framework import HistoryProvider, Message

from ..new_aimemory import AsyncAIMemory


class NexaMemHistoryProvider(HistoryProvider):
    """Persist typed per-session messages while leaving the supplied facade open."""

    def __init__(
        self,
        memory: AsyncAIMemory,
        namespace: str,
        *,
        source_id: str = "nexamem",
        ttl_sec: int | None = None,
    ) -> None:
        if not namespace:
            raise ValueError("An explicit nonempty namespace is required")
        super().__init__(source_id=source_id)
        self.memory = memory
        self.namespace = namespace
        self.ttl_sec = ttl_sec
        self._lock = asyncio.Lock()

    def _scope(self, session_id: str | None) -> str:
        if not session_id:
            raise ValueError("An explicit nonempty session_id is required")
        return json.dumps(
            ["nexamem", "agent-framework", self.namespace, self.source_id, session_id]
        )

    async def get_messages(
        self, session_id: str | None, *, state: dict[str, Any] | None = None, **kwargs: Any
    ) -> list[Message]:
        """Load complete typed messages in chronological order."""
        scope = self._scope(session_id)
        async with self._lock:
            records = []
            for memory_id in await self.memory.list(scope):
                record = await self.memory.retrieve(memory_id)
                if record is not None:
                    records.append(record)
            records.sort(key=lambda record: record["metadata"]["order"])
            return [Message.from_dict(json.loads(record["content"])) for record in records]

    async def save_messages(
        self,
        session_id: str | None,
        messages: Sequence[Message],
        *,
        state: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Append messages; stable framework message IDs make retries idempotent."""
        scope = self._scope(session_id)
        async with self._lock:
            for message in messages:
                memory_id = None
                if message.message_id:
                    identity = json.dumps([scope, message.message_id])
                    memory_id = "af-" + hashlib.sha256(identity.encode()).hexdigest()
                    if await self.memory.retrieve(memory_id) is not None:
                        continue
                await self.memory.store(
                    json.dumps(message.to_dict()),
                    memory_id,
                    metadata={"order": time.time_ns()},
                    scope=scope,
                    ttl_sec=self.ttl_sec,
                )

    async def clear(self, session_id: str) -> None:
        """Delete one session's history, not other sessions or namespaces."""
        scope = self._scope(session_id)
        async with self._lock:
            await self.memory.clear_scope(scope)

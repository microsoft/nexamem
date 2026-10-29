"""Explicit Semantic Kernel ChatHistory persistence, without model or vector services."""

import hashlib
import json

from semantic_kernel.contents import ChatHistory

from ..new_aimemory import AsyncAIMemory


class NexaMemChatHistoryStore:
    """Save and restore typed history snapshots using a caller-owned async facade."""

    def __init__(
        self, memory: AsyncAIMemory, namespace: str, *, ttl_sec: int | None = None
    ) -> None:
        if not namespace:
            raise ValueError("An explicit nonempty namespace is required")
        self.memory = memory
        self.namespace = namespace
        self.ttl_sec = ttl_sec

    def _key(self, session_id: str) -> str:
        if not session_id:
            raise ValueError("An explicit nonempty session_id is required")
        identity = json.dumps(["nexamem", "semantic-kernel", self.namespace, session_id])
        return "sk-" + hashlib.sha256(identity.encode()).hexdigest()

    async def save(self, session_id: str, history: ChatHistory) -> None:
        """Replace a session snapshot; TTL restarts on each successful save."""
        key = self._key(session_id)
        await self.memory.store(history.serialize(), key, scope=key, ttl_sec=self.ttl_sec)

    async def load(self, session_id: str) -> ChatHistory:
        """Restore all typed message items, or return an empty history when absent."""
        record = await self.memory.retrieve(self._key(session_id))
        return (
            ChatHistory.restore_chat_history(record["content"])
            if record is not None
            else ChatHistory()
        )

    async def clear(self, session_id: str) -> None:
        """Delete only this namespace/session snapshot without closing the facade."""
        await self.memory.delete(self._key(session_id))

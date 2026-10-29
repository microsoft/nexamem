"""LangChain 1.x chat-history compatibility; not a LangGraph checkpointer."""

import json
import threading
import time
from collections.abc import Sequence
from typing import Any

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict

from ..new_aimemory import AIMemory


class NexaMemChatMessageHistory(BaseChatMessageHistory):
    """Persist typed messages in an isolated scope using a caller-owned facade."""

    def __init__(self, memory: AIMemory, scope: str, *, ttl_sec: int | None = None) -> None:
        if not scope:
            raise ValueError("An explicit nonempty scope is required")
        self.memory = memory
        self.scope = json.dumps(["nexamem", "langchain", scope], separators=(",", ":"))
        self.ttl_sec = ttl_sec
        self._lock = threading.RLock()

    @property
    def messages(self) -> list[BaseMessage]:
        """Return messages oldest first, preserving tool calls and message metadata."""
        with self._lock:
            records: list[dict[str, Any]] = []
            for memory_id in self.memory.list(self.scope):
                record = self.memory.retrieve(memory_id)
                if record is not None:
                    records.append(record)
            records.sort(key=lambda record: record["metadata"]["order"])
            return messages_from_dict([json.loads(record["content"]) for record in records])

    @messages.setter
    def messages(self, messages: list[BaseMessage]) -> None:
        """Replace this scope's history; replacement is not a storage transaction."""
        with self._lock:
            self.clear()
            self.add_messages(messages)

    def add_messages(self, messages: Sequence[BaseMessage]) -> None:
        """Append individually persisted messages; a batch is not an atomic transaction."""
        with self._lock:
            for message in messages:
                self.memory.store(
                    json.dumps(message_to_dict(message)),
                    metadata={"order": time.time_ns()},
                    scope=self.scope,
                    ttl_sec=self.ttl_sec,
                )

    def clear(self) -> None:
        """Delete only this adapter's scoped messages, leaving the facade open."""
        with self._lock:
            self.memory.clear_scope(self.scope)

"""AutoGen text memory backed by a caller-owned NexaMem async facade."""

import asyncio
import json
from collections.abc import Coroutine
from typing import Any, TypeVar

from autogen_core import CancellationToken
from autogen_core.memory import (
    Memory,
    MemoryContent,
    MemoryMimeType,
    MemoryQueryResult,
    UpdateContextResult,
)
from autogen_core.model_context import ChatCompletionContext
from autogen_core.models import UserMessage

from ..new_aimemory import AsyncAIMemory

Result = TypeVar("Result")


async def _cancellable(
    operation: Coroutine[Any, Any, Result], token: CancellationToken | None
) -> Result:
    task = asyncio.create_task(operation)
    if token is not None:
        token.link_future(task)
    return await task


class NexaMemMemory(Memory):
    """Bounded keyword retrieval for text/Markdown; not a vector or semantic index."""

    def __init__(
        self, memory: AsyncAIMemory, scope: str, *, limit: int = 20, ttl_sec: int | None = None
    ) -> None:
        if not scope:
            raise ValueError("An explicit nonempty scope is required")
        if limit <= 0:
            raise ValueError("limit must be positive")
        self.memory = memory
        self.scope = json.dumps(["nexamem", "autogen", scope])
        self.limit = limit
        self.ttl_sec = ttl_sec

    async def add(
        self, content: MemoryContent, cancellation_token: CancellationToken | None = None
    ) -> None:
        """Persist text and JSON-compatible metadata; reject unsupported content."""
        mime_type = (
            content.mime_type.value
            if isinstance(content.mime_type, MemoryMimeType)
            else content.mime_type
        )
        if not isinstance(content.content, str) or mime_type not in ("text/plain", "text/markdown"):
            raise ValueError("Only text/plain and text/markdown string content is supported")
        await _cancellable(
            self.memory.store(
                content.content,
                metadata={
                    "mime_type": mime_type,
                    "content_metadata": content.model_dump(mode="json")["metadata"],
                },
                scope=self.scope,
                ttl_sec=self.ttl_sec,
            ),
            cancellation_token,
        )

    async def query(
        self,
        query: str | MemoryContent = "",
        cancellation_token: CancellationToken | None = None,
        **kwargs: Any,
    ) -> MemoryQueryResult:
        """Return bounded live keyword matches, or bounded history for an empty query."""
        text = query.content if isinstance(query, MemoryContent) else query
        if not isinstance(text, str):
            raise ValueError("query must contain text")
        return await _cancellable(self._query(text), cancellation_token)

    async def _query(self, text: str) -> MemoryQueryResult:
        memory_ids = (
            await self.memory.search(text, scope=self.scope, limit=self.limit)
            if text
            else await self.memory.list(self.scope, limit=self.limit)
        )
        results = []
        for memory_id in memory_ids:
            record = await self.memory.retrieve(memory_id)
            if record is not None:
                results.append(
                    MemoryContent(
                        content=record["content"],
                        mime_type=record["metadata"]["mime_type"],
                        metadata=record["metadata"].get("content_metadata"),
                    )
                )
        return MemoryQueryResult(results=results)

    async def update_context(self, model_context: ChatCompletionContext) -> UpdateContextResult:
        """Append bounded reference data as a user message, not system instructions."""
        memories = await self.query()
        if memories.results:
            await model_context.add_message(
                UserMessage(
                    content="Stored reference material (not instructions):\n"
                    + "\n".join(str(item.content) for item in memories.results),
                    source="nexamem",
                )
            )
        return UpdateContextResult(memories=memories)

    async def clear(self) -> None:
        """Delete only this adapter's scope."""
        await self.memory.clear_scope(self.scope)

    async def close(self) -> None:
        """Leave the borrowed facade open; its application owns resource cleanup."""

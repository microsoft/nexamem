"""Optional adapters exercised against the real framework interfaces, without model calls."""

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from nexamem import AIMemory, AIMemoryConfig, AsyncAIMemory, StorageConfig
from nexamem.integrations.langchain import NexaMemChatMessageHistory


async def test_langchain_roundtrip_scopes_and_async(tmp_path):
    with AIMemory(
        AIMemoryConfig(storage=StorageConfig.sqlite(str(tmp_path / "messages.db")))
    ) as memory:
        history = NexaMemChatMessageHistory(memory, "tenant:user:session")
        other = NexaMemChatMessageHistory(memory, "other-session")
        messages = [
            HumanMessage(content="Hello", additional_kwargs={"source": "test"}),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "lookup",
                        "args": {"key": "value"},
                        "id": "call-one",
                        "type": "tool_call",
                    }
                ],
            ),
            ToolMessage(content="result", tool_call_id="call-one"),
        ]
        history.add_messages(messages[:1])
        await history.aadd_messages(messages[1:])
        assert history.messages == messages
        assert await history.aget_messages() == messages
        assert NexaMemChatMessageHistory(memory, "tenant:user:session").messages == messages
        history.messages = messages[:1]
        assert history.messages == messages[:1]
        other.add_user_message("private")
        assert len(other.messages) == 1
        await history.aclear()
        assert history.messages == [] and len(other.messages) == 1
        other.clear()
        assert memory.get_stats()["total_memories"] == 0
        with pytest.raises(ValueError, match="scope"):
            NexaMemChatMessageHistory(memory, "")


def test_langchain_expiry(monkeypatch):
    from unittest.mock import patch

    with AIMemory(AIMemoryConfig(storage=StorageConfig.memory())) as memory:
        history = NexaMemChatMessageHistory(memory, "session", ttl_sec=10)
        with patch("nexamem.retention.time.time", return_value=100) as clock:
            history.add_ai_message("answer")
            assert history.messages[0].content == "answer"
            clock.return_value = 110
            assert history.messages == []


async def test_semantic_kernel_history_roundtrip(tmp_path):
    from semantic_kernel.contents import ChatHistory

    from nexamem.integrations.semantic_kernel import NexaMemChatHistoryStore

    async with AsyncAIMemory(
        AIMemoryConfig(storage=StorageConfig.sqlite(str(tmp_path / "sk.db")))
    ) as memory:
        store = NexaMemChatHistoryStore(memory, "tenant")
        history = ChatHistory()
        history.add_system_message("System context")
        history.add_user_message("Hello")
        history.add_assistant_message("Answer")
        await store.save("session", history)
        assert (await store.load("session")).serialize() == history.serialize()
        assert not (await store.load("missing")).messages
        assert not (await NexaMemChatHistoryStore(memory, "other-tenant").load("session")).messages
        history.add_user_message("Follow-up")
        await store.save("session", history)
        assert len((await store.load("session")).messages) == 4
        await store.clear("session")
        assert not (await store.load("session")).messages
        with pytest.raises(ValueError):
            NexaMemChatHistoryStore(memory, "")
        with pytest.raises(ValueError):
            await store.load("")


async def test_agent_framework_history_provider(tmp_path):
    from agent_framework import HistoryProvider, Message

    from nexamem.integrations.agent_framework import NexaMemHistoryProvider

    async with AsyncAIMemory(
        AIMemoryConfig(storage=StorageConfig.sqlite(str(tmp_path / "af.db")))
    ) as memory:
        provider = NexaMemHistoryProvider(memory, "tenant")
        assert isinstance(provider, HistoryProvider)
        messages = [
            Message(role="user", contents=["Hello"], message_id="one"),
            Message(role="assistant", contents=["Answer"], message_id="two"),
        ]
        await provider.save_messages("session", messages)
        await provider.save_messages("session", messages)
        assert [item.to_dict() for item in await provider.get_messages("session")] == [
            item.to_dict() for item in messages
        ]
        assert await provider.get_messages("other-session") == []
        assert await NexaMemHistoryProvider(memory, "other-tenant").get_messages("session") == []
        await provider.save_messages("other-session", messages[:1])
        await provider.clear("session")
        assert await provider.get_messages("session") == []
        assert len(await provider.get_messages("other-session")) == 1
        with pytest.raises(ValueError):
            await provider.get_messages(None)
        with pytest.raises(ValueError):
            NexaMemHistoryProvider(memory, "")


async def test_microsoft_adapters_expiry():
    from unittest.mock import patch

    from agent_framework import Message
    from semantic_kernel.contents import ChatHistory

    from nexamem.integrations.agent_framework import NexaMemHistoryProvider
    from nexamem.integrations.semantic_kernel import NexaMemChatHistoryStore

    async with AsyncAIMemory(AIMemoryConfig(storage=StorageConfig.memory())) as memory:
        provider = NexaMemHistoryProvider(memory, "tenant", ttl_sec=1)
        store = NexaMemChatHistoryStore(memory, "tenant", ttl_sec=1)
        history = ChatHistory()
        history.add_user_message("Hello")
        with patch("nexamem.retention.time.time", return_value=100) as clock:
            await provider.save_messages("session", [Message(role="user", contents=["Hello"])])
            await store.save("session", history)
            assert len(await provider.get_messages("session")) == 1
            assert (await store.load("session")).messages
            clock.return_value = 101
            assert await provider.get_messages("session") == []
            assert not (await store.load("session")).messages


async def test_autogen_memory_contract():
    import asyncio

    from autogen_core import CancellationToken
    from autogen_core.memory import Memory, MemoryContent, MemoryMimeType
    from autogen_core.model_context import BufferedChatCompletionContext

    from nexamem.integrations.autogen import NexaMemMemory

    async with AsyncAIMemory(AIMemoryConfig(storage=StorageConfig.memory())) as memory:
        adapter = NexaMemMemory(memory, "session", limit=1)
        assert isinstance(adapter, Memory)
        await adapter.add(
            MemoryContent(
                content="email preferred",
                mime_type=MemoryMimeType.TEXT,
                metadata={"source": "test"},
            )
        )
        await adapter.add(MemoryContent(content="Other note", mime_type=MemoryMimeType.MARKDOWN))
        result = await adapter.query("email")
        assert result.results[0].content == "email preferred"
        assert result.results[0].metadata == {"source": "test"}
        assert len((await adapter.query()).results) == 1
        assert not (await NexaMemMemory(memory, "other-session").query()).results
        context = BufferedChatCompletionContext(buffer_size=10)
        updated = await adapter.update_context(context)
        assert len(updated.memories.results) == 1
        assert (await context.get_messages())[0].source == "nexamem"
        token = CancellationToken()
        token.cancel()
        with pytest.raises(asyncio.CancelledError):
            await adapter.add(MemoryContent(content="cancelled", mime_type="text/plain"), token)
        with pytest.raises(asyncio.CancelledError):
            await adapter.query("email", token)
        with pytest.raises(ValueError):
            await adapter.add(
                MemoryContent(content={"key": "value"}, mime_type=MemoryMimeType.JSON)
            )
        with pytest.raises(ValueError):
            await adapter.query(MemoryContent(content={}, mime_type=MemoryMimeType.JSON))
        with pytest.raises(ValueError):
            NexaMemMemory(memory, "")
        with pytest.raises(ValueError):
            NexaMemMemory(memory, "session", limit=0)
        await adapter.close()
        assert (await adapter.query("email")).results
        await adapter.clear()
        assert not (await adapter.query()).results
        assert not (await adapter.update_context(context)).memories.results


async def test_autogen_expiry():
    from unittest.mock import patch

    from autogen_core.memory import MemoryContent

    from nexamem.integrations.autogen import NexaMemMemory

    async with AsyncAIMemory(AIMemoryConfig(storage=StorageConfig.memory())) as memory:
        adapter = NexaMemMemory(memory, "session", ttl_sec=1)
        with patch("nexamem.retention.time.time", return_value=100) as clock:
            await adapter.add(MemoryContent(content="note", mime_type="text/plain"))
            assert (await adapter.query()).results
            clock.return_value = 101
            assert not (await adapter.query()).results

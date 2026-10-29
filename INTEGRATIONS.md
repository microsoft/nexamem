# Framework Integrations

These integrations target the [1.0 release candidate](PROJECT_STATUS.md), not the current stable PyPI package. Install from the repository root with pip. The base package does not import framework SDKs; direct adapter imports require the matching extra.

| Extra | Contract | Validated SDK |
| --- | --- | --- |
| `langchain` | `BaseChatMessageHistory` | langchain-core 1.6.13 |
| `autogen` | `autogen_core.memory.Memory` | autogen-core 0.7.5 |
| `semantic-kernel` | Explicit typed `ChatHistory` save/load | semantic-kernel 1.46.0 |
| `agent-framework` | `HistoryProvider` | agent-framework-core 1.22.0 |

```shell
python -m pip install -e ".[langchain,autogen,semantic-kernel,agent-framework]"
python -m pip check
```

All adapters require explicit namespaces/scopes. These isolate ordinary application records, not authorization. Validate tenant/user/session identities before constructing adapters. They borrow their facade and never close it. Use facade context managers and stop agent work before teardown. Local examples need no model service, credentials, or network.

## LangChain

```python
from langchain_core.messages import HumanMessage, AIMessage
from nexamem import AIMemory, AIMemoryConfig, StorageConfig
from nexamem.integrations.langchain import NexaMemChatMessageHistory

with AIMemory(AIMemoryConfig(storage=StorageConfig.memory())) as memory:
    history = NexaMemChatMessageHistory(memory, "tenant:user:session", ttl_sec=3600)
    history.add_messages([HumanMessage(content="Hello"), AIMessage(content="Welcome")])
    assert len(history.messages) == 2
    history.clear()
```

Typed messages, tool calls/results, and JSON-compatible message metadata round-trip through LangChain's serializers. Inherited `aget_messages`, `aadd_messages`, and `aclear` offload sync calls. Assigning `history.messages` replaces its scope. Batches/replacement are not atomic; ordering uses local timestamps and assumes a single writer per conversation. This is LangChain **1.x compatibility**, not a LangGraph checkpointer. Upstream deprecated `BaseChatMessageHistory` in 1.6.4 for removal in 2.0; do not assume future LangChain compatibility.

## AutoGen

```python
import asyncio
from autogen_core.memory import MemoryContent, MemoryMimeType
from nexamem import AsyncAIMemory, AIMemoryConfig, StorageConfig
from nexamem.integrations.autogen import NexaMemMemory

async def main():
    async with AsyncAIMemory(AIMemoryConfig(storage=StorageConfig.memory())) as memory:
        adapter = NexaMemMemory(memory, "tenant:user:session", limit=20, ttl_sec=3600)
        await adapter.add(MemoryContent(content="Prefer email", mime_type=MemoryMimeType.TEXT))
        assert (await adapter.query("email")).results[0].content == "Prefer email"
        await adapter.clear()

asyncio.run(main())
```

Pass the adapter in your AutoGen agent's memory collection. `query` uses backend text search, not semantic similarity; an empty query returns bounded history in backend order. `update_context` adds bounded reference content as a user message with source `nexamem`, not system instructions. This does not make untrusted stored content safe: authorize writes and apply your own prompt/data trust controls. Text and Markdown strings with JSON-compatible metadata are supported; binary, images, and JSON-object payloads are rejected. Cancellation tokens link to add/query tasks. AutoGen component config serialization is not implemented.

## Semantic Kernel

```python
import asyncio
from semantic_kernel.contents import ChatHistory
from nexamem import AsyncAIMemory, AIMemoryConfig, StorageConfig
from nexamem.integrations.semantic_kernel import NexaMemChatHistoryStore

async def main():
    async with AsyncAIMemory(AIMemoryConfig(storage=StorageConfig.memory())) as memory:
        store = NexaMemChatHistoryStore(memory, "tenant", ttl_sec=3600)
        history = ChatHistory()
        history.add_user_message("Hello")
        history.add_assistant_message("Welcome")
        await store.save("session", history)
        restored = await store.load("session")
        assert len(restored.messages) == 2
        await store.clear("session")

asyncio.run(main())
```

This bridge uses Semantic Kernel's `serialize`/`restore_chat_history` methods, retaining typed message items. Save explicitly after your application updates the history; it is not an automatic agent-thread, vector-store, or embedding integration. Each save replaces one session snapshot and restarts its TTL. Concurrent saves are last-writer-wins. Missing/expired sessions load as empty history. Semantic Kernel 1.46 constrains Pydantic below 2.14; dependency resolution selects compatible 2.13.x with this extra.

## Microsoft Agent Framework

```python
import asyncio
from agent_framework import Message
from nexamem import AsyncAIMemory, AIMemoryConfig, StorageConfig
from nexamem.integrations.agent_framework import NexaMemHistoryProvider

async def main():
    async with AsyncAIMemory(AIMemoryConfig(storage=StorageConfig.memory())) as memory:
        provider = NexaMemHistoryProvider(memory, "tenant", ttl_sec=3600)
        await provider.save_messages("session", [Message(role="user", contents=["Hello"], message_id="one")])
        assert len(await provider.get_messages("session")) == 1
        await provider.clear("session")

asyncio.run(main())
```

Register the provider with `Agent(..., context_providers=[provider])`; the inherited `HistoryProvider` hooks load history before a run and store inputs/outputs after it. Use a stable, explicit session ID when resuming conversations. Missing IDs are rejected, not assigned to a shared default. The default does not store context from other providers. Stable `Message.message_id` values deduplicate retries while records remain live; messages without IDs append on every save. Ordering uses local timestamps and assumes one writer per conversation; multi-message saves are not transactions. Message persistence uses the framework's `to_dict`/`from_dict` representation, excluding its nonpersistent raw representation.

## Microsoft Foundry Hosting

Foundry is a hosting/service boundary, not a separate NexaMem framework adapter. Use the Agent Framework provider inside application-managed or Foundry-hosted agent code when your application owns local conversation persistence. This does **not** replace Foundry-managed threads, conversations, checkpoints, or workflow state; choose a single owner and avoid duplicating service-managed history.

For a hosted application:

1. Install the required framework extra and, when needed, `appinsights` in your application environment.
2. Supply Azure Redis configuration as described in [passwordless Redis setup](INSTALLATION.md#azure-cache-for-redis). Give the hosted identity Redis data-plane access and network reachability. Foundry project permissions do not grant Redis access.
3. Create one application-owned `AsyncAIMemory` with Redis storage; give the provider an authorized application namespace and use stable per-conversation session IDs. Use local memory/SQLite only for development, not as durable shared hosted storage.
4. Register the provider in your Agent Framework agent. Keep Foundry/model-client setup in the host; NexaMem does not choose models, configure endpoints, create agents, or provision resources.
5. Configure OpenTelemetry/Application Insights once in the host, as in [observability](README.md#observability). Reuse an existing host pipeline rather than initializing another. Review other instrumentations for prompt/content collection separately.
6. Shut down agent work before closing the memory facade and telemetry pipeline. Validate refresh, reconnect, failover, retention, and session isolation in your actual hosted environment.

The offline adapter tests make no model calls and do not certify Foundry hosting or live Azure permissions. References: [Microsoft Agent Framework](https://learn.microsoft.com/agent-framework/), [Microsoft Foundry](https://learn.microsoft.com/azure/foundry/), and [Azure Redis Python guide](https://learn.microsoft.com/azure/redis/python-get-started).

## Retention and Concurrency

All adapters use the new facade's [logical expiry](NEW_ARCHITECTURE.md#retention-and-lifecycle). LangChain and Agent Framework TTLs apply per message; AutoGen TTL applies per note; Semantic Kernel TTL applies to the whole saved snapshot. `ttl_sec=None` inherits the facade default. No adapter guarantees physical erasure or removes audit records/backups. Reads can scan many records and are not a distributed snapshot. Per-instance locks do not coordinate other adapters/processes. Protect stored content, validate serialization-compatible metadata, bound history in your application, and use only trusted stores.
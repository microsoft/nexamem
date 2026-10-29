# NexaMem

[![CI](https://github.com/microsoft/nexamem/actions/workflows/ci.yml/badge.svg)](https://github.com/microsoft/nexamem/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

NexaMem is an Azure-focused Python storage library for chatbot history and application-managed AI memory. Keep messages, conversation summaries, user preferences, and workflow notes as text records with metadata, then retrieve, search, and delete them through a consistent API.

The shared-service implementation targets Azure Cache for Redis, with Azure identity and Key Vault configuration support. Start with in-memory storage for experiments or JSON files and SQLite for local persistence without an Azure account. Change the storage configuration without rewriting calls to the memory API.

## Why NexaMem?

- **One API across storage backends.** Store, retrieve, list, search, and delete text records without writing a separate persistence layer for each backend.
- **Context organized around your application.** Attach metadata and group records by conversation, user, or task using caller-defined scopes. Scopes organize data; they are not access controls.
- **Sync and async interfaces.** Use the interface that fits your application. Local async adapters still perform synchronous I/O; they are not nonblocking storage engines.
- **Optional observability.** Correlate memory operations with OpenTelemetry traces and metrics, including application-configured Azure Monitor/Application Insights export.

## Typical Uses

- **Chatbots:** persist conversation messages and retrieve history when assembling the next prompt.
- **Personal assistants:** save explicitly captured preferences and application-generated summaries for later conversations.
- **Agent workflows:** retain task notes and intermediate text results so subsequent steps can retrieve them by ID or search within a scope.

Your application decides what to remember and what to include in a model's context. NexaMem supplies storage and text-based search, not automatic memory extraction, embeddings, or semantic retrieval.

> [!IMPORTANT]
> This checkout is preparing an unreleased 1.0.0 stability release. Package metadata is still `0.4.2`; do not publish rebuilt artifacts under that existing version. See [release status](PROJECT_STATUS.md) and [unreleased changes](CHANGELOG.md).

## Install

This checkout requires Python 3.11 or newer. CI targets Python 3.11, 3.12, and 3.13 on Linux, Windows, and macOS. Published older versions may have different requirements.

```shell
python -m pip install nexamem
```

Published packages do not contain this checkout's unreleased fixes. For the stabilization code, create and activate a virtual environment using the platform-specific steps in [installation](INSTALLATION.md), then run from the repository root:

```shell
python -m pip install -e .
```

Contributors can install `python -m pip install -e ".[dev]"` instead to add test and development tools. No uv installation or commands are required. The local quick starts below need no Azure account, credentials, YAML configuration, or telemetry setup.

## Quick Start

```python
from nexamem import AIMemory, AIMemoryConfig, StorageConfig

memory = AIMemory(
    AIMemoryConfig(default_scope="conversation-42", storage=StorageConfig.memory())
)
memory_id = memory.store("The customer prefers email.", metadata={"source": "chat"})
record = memory.retrieve(memory_id)
assert record is not None
assert record["content"] == "The customer prefers email."
assert memory.search("email") == [memory_id]
assert memory.delete(memory_id)
```

Use `StorageConfig.file("./memory-data")` or `StorageConfig.sqlite("./memory.db")` for local persistence. Reads return a record containing `id`, `content`, `metadata`, `scope`, and timestamps, or `None` when absent.

### Async

```python
import asyncio
from nexamem import AsyncAIMemory, AIMemoryConfig, StorageConfig

async def main():
    memory = AsyncAIMemory(
        AIMemoryConfig(default_scope="conversation-42", storage=StorageConfig.memory())
    )
    memory_id = await memory.store("Remember this preference.")
    record = await memory.retrieve(memory_id)
    assert record is not None
    assert record["content"] == "Remember this preference."
    assert await memory.delete(memory_id)

asyncio.run(main())
```

The local async adapters delegate to synchronous storage; they do not make file or SQLite operations nonblocking.

### Backends

| Backend | Configuration | Notes |
| --- | --- | --- |
| Memory | `StorageConfig.memory()` | Process-local, not persistent |
| File | `StorageConfig.file("./memory-data")` | JSON records and indexes; individual record writes are atomic, not multi-file transactions |
| SQLite | `StorageConfig.sqlite("./memory.db")` | Persistent local database; no external service required |
| Azure Redis | `StorageConfig.azure_redis(AzureRedisConfig(...))` | Requires a separately configured service; see [Azure setup](INSTALLATION.md#azure-cache-for-redis) and [limitations](NEW_ARCHITECTURE.md#azure-redis-configuration) |

Redis, fakeredis, PyYAML, and Azure identity/Key Vault clients remain runtime dependencies for compatibility. There is no `azure` extra. Optional observability extras are `telemetry` and `appinsights`; development extras are `dev`, `docs`, `perf`, and `all`.

## Observability

Observability is optional. The `telemetry` extra installs the OpenTelemetry API; your application supplies its SDK, providers, sampling, exporters, and shutdown/flush lifecycle. Without the API, operations run normally. With the API but no configured providers, telemetry is a no-op. NexaMem never configures global providers or starts an exporter itself.

For generic OpenTelemetry support in this unreleased checkout:

```shell
python -m pip install -e ".[telemetry]"
```

For Azure Monitor/Application Insights, the `appinsights` extra also installs the Azure Monitor OpenTelemetry distribution:

```shell
python -m pip install -e ".[appinsights]"
```

Set `APPLICATIONINSIGHTS_CONNECTION_STRING` in the application's environment. Configure Azure Monitor once at application startup, before using NexaMem; do not initialize a second pipeline if your host already provides one. For Azure-hosted production applications, prefer managed identity with the required Application Insights permissions:

```python
from azure.identity import DefaultAzureCredential
from azure.monitor.opentelemetry import configure_azure_monitor

configure_azure_monitor(
    credential=DefaultAzureCredential(),
    logger_name="my_application",
    enable_live_metrics=False,
)

from nexamem import AIMemory, AIMemoryConfig, StorageConfig

memory = AIMemory(AIMemoryConfig(storage=StorageConfig.memory()))
memory.store("The customer prefers email.")
```

See the [Azure Monitor Python configuration reference](https://learn.microsoft.com/python/api/overview/azure/monitor-opentelemetry-readme?view=azure-python) and [Microsoft Entra authentication requirements](https://learn.microsoft.com/azure/azure-monitor/app/azure-ad-authentication).

The public `AIMemory` and `AsyncAIMemory` data operations, including compatibility `write()`/`read()`, emit `nexamem.<operation>` spans under instrumentation scope `nexamem`, an operation counter (`nexamem.operations`), and a duration histogram in seconds (`nexamem.operation.duration`). Spans retain the caller's active context across sync calls and awaits; independently instrumented backend calls can become child spans. Counter and duration attributes contain only the operation name and success/error outcome. Exceptions and cancellations propagate unchanged; spans record only their exception class, not messages or stack traces. Missing records and unsuccessful boolean results are normal results, not exceptions.

NexaMem's instrumentation does not capture content, metadata, search queries, record IDs, scopes, user/session IDs, or credentials. Review your application's other instrumentations and logging separately: their data collection is outside this guarantee. No trace context is automatically stored with memories or passed between agents/processes. The retained legacy facades and standalone storage APIs are not instrumented by this integration; the legacy in-process metrics collector remains separate.

## Channels and Guarantees

`AIMemory` and `AsyncAIMemory` retain `write()`/`read()` channel compatibility methods. Configure channels through [YAML](YAML_SCHEMA_VALIDATION.md) or `register_channel()`. Channel scopes include environment, agent, user, session, and channel; UTF-8 bytes are decoded on write.

> [!WARNING]
> Scope names are logical namespaces, not authorization. The new facade records TTL, quota, encryption, and PII options but does not enforce those policies or implement client-side encryption. Compatibility `read()` enforces `max_msgs`, not `since_sec`, `max_bytes`, or `max_tokens`. Enforce security and retention requirements in the application and backing service.

Policy/content-processing helpers and the retained Redis-oriented legacy facade are separate APIs. Do not assume their behavior applies automatically to the new facade. See [compatibility and migration](LEGACY_API.md) and [security limitations](SECURITY.md).

## Development

```shell
python -m pip install -e ".[dev]"
python -m pytest tests/ -m "not integration" --cov=nexamem --cov-report=term-missing --cov-fail-under=90
python -m ruff check src/ tests/ build_and_test.py
python -m ruff format --check src/ tests/ build_and_test.py
python -m mypy src/
python build_and_test.py --dist-dir dist-release
```

The line-coverage gate covers the complete package, including retained legacy modules. Tests use local backends, fakeredis, and mocked Azure identity; passing unit tests is not live Azure certification. Strict mypy passes across the complete package and remains a blocking gate.

## Documentation

- [Installation and dependency policy](INSTALLATION.md)
- [Architecture and backend limitations](NEW_ARCHITECTURE.md)
- [Legacy API and data migration](LEGACY_API.md)
- [Channel YAML validation](YAML_SCHEMA_VALIDATION.md)
- [Async testing](ASYNC_TESTING.md)
- [Contributor and release workflow](CONTRIBUTING.md)
- [Release status](PROJECT_STATUS.md)
- [Security reporting](SECURITY.md)

Licensed under the [MIT License](LICENSE).
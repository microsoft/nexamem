# Installation

## Python Support

The release candidate requires Python **3.11+**. The stabilization baseline passed CI on CPython 3.11, 3.12, and 3.13 on Linux, macOS, and Windows; candidate changes must pass the matrix again. Python 3.8, 3.9, and 3.10 are no longer supported by this checkout. Newer Python versions are not yet certified by the CI matrix.

Published packages predate this stabilization work. Installing from PyPI does not install the unreleased features described here; see [release status](PROJECT_STATUS.md) for the current package version and publication gates.

## Set Up With pip

The quick starts and new features in this documentation require the release-candidate source checkout. If you have not already cloned or downloaded it:

```shell
git clone https://github.com/microsoft/nexamem.git
cd nexamem
```

Create an isolated environment using your selected supported interpreter:

```shell
python --version
python -m venv .venv
```

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```shell
source .venv/bin/activate
```

From the repository root after activating the environment:

```shell
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip check
```

The pip upgrade uses your configured package index. If PowerShell blocks activation, use `.venv\Scripts\python.exe` instead of `python` in subsequent commands; activation is optional.

For contributors who also need tests, lint, typing, and packaging tools:

```shell
python -m pip install -e ".[dev]"
python -m pip check
```

Alternatively, `python -m pip install -r requirements-test.txt` installs the same development extra. `requirements.txt` installs the local project. No uv tooling is used.

For the currently published release instead, use `python -m pip install nexamem` in an isolated environment and follow documentation matching that release. It does not include this checkout's unreleased features.

## Extras

| Extra | Purpose |
| --- | --- |
| `telemetry` | OpenTelemetry API; your application supplies its SDK and exporter |
| `appinsights` | Telemetry API plus the Azure Monitor OpenTelemetry distribution |
| `langchain` | LangChain 1.x typed chat-history adapter |
| `autogen` | AutoGen 0.7 text/Markdown memory adapter |
| `semantic-kernel` | Semantic Kernel 1.x `ChatHistory` save/load integration |
| `agent-framework` | Microsoft Agent Framework 1.22 `HistoryProvider` |
| `dev` | Tests, lint, typing, packaging, OpenTelemetry SDK, and all four frameworks for offline interface tests |
| `docs` | MkDocs and Python API documentation tooling |
| `perf` | Benchmark and memory-profiling tools |
| `all` | The three development extras: `dev`, `docs`, and `perf`; not `appinsights` |

Azure identity, Key Vault, Redis, and fakeredis dependencies remain included in the base package. Do not use the nonexistent `nexamem[azure]` extra.

For optional observability in this checkout, install `python -m pip install -e ".[telemetry]"` or `python -m pip install -e ".[appinsights]"`. Combine extras as needed, for example `python -m pip install -e ".[dev,appinsights]"`. See [observability setup](README.md#observability) for application-owned provider/exporter configuration and privacy limits.

## First Local Run

Run the [sync or async quick start](README.md#quick-start) after installation. Both use process-local memory, so they require no Azure account or environment variables. Successful assertions produce no output. Use `StorageConfig.file("./memory-data")` or `StorageConfig.sqlite("./memory.db")` for persistence between processes; relative paths are resolved from the application's working directory. File/SQLite async data operations run in worker threads; construction is still synchronous. See [framework examples](INTEGRATIONS.md) for optional integrations.

In a notebook with an event loop already running, define `main()` from the async example and call `await main()` instead of `asyncio.run(main())`.

To verify local persistence across facade lifetimes, run this example from a writable directory. It creates `nexamem-demo.db`; the stored note is deleted at the end, but the database file remains:

```python
from nexamem import AIMemory, AIMemoryConfig, StorageConfig

config = AIMemoryConfig(
	default_scope="local-demo", storage=StorageConfig.sqlite("./nexamem-demo.db")
)
with AIMemory(config) as memory:
	memory_id = memory.store("Persist this note.")

with AIMemory(config) as memory:
	record = memory.retrieve(memory_id)
	assert record is not None
	assert record["content"] == "Persist this note."
	assert memory.delete(memory_id)
```

## Azure Cache for Redis

Azure services are provisioned separately; installing NexaMem does not create resources. Prefer passwordless Entra ID authentication:

1. Provide an existing endpoint ending in `.redis.azure.net` (Azure Managed Redis, TLS port `10000`) or `.redis.cache.windows.net` (Azure Cache for Redis, TLS port `6380`). Explicit ports are respected. Managed Redis requires database `0`.
2. Enable Entra authentication and grant the application identity Redis **data-plane** access. Subscription/resource management roles alone do not grant Redis commands. In Azure, use the host's system-assigned or user-assigned managed identity; locally use a supported `DefaultAzureCredential` identity with equivalent Redis permissions.
3. Configure network access, DNS, firewall/private endpoint connectivity, and a Redis-compatible noncluster/proxy endpoint. This adapter uses `Redis`, not `RedisCluster`; it does not route OSS cluster `MOVED` responses.
4. Set the hostname in the application environment, then construct the facade:

| Variable | Value |
| --- | --- |
| `AZURE_REDIS_HOSTNAME` | Endpoint hostname without a URL scheme or port |
| `AZURE_REDIS_AUTH_METHOD` | `entra_id` when using `AzureRedisConfig.from_env()` |
| `AZURE_CLIENT_ID` | Optional user-assigned managed identity client ID; omit for system identity |

```python
import os

from nexamem import AIMemory, AIMemoryConfig, AzureRedisConfig, StorageConfig

redis_config = AzureRedisConfig(
	hostname=os.environ["AZURE_REDIS_HOSTNAME"],
	auth_method="entra_id",
	use_entra_id=True,
	client_id=os.environ.get("AZURE_CLIENT_ID"),
)
with AIMemory(
	AIMemoryConfig(default_scope="application", storage=StorageConfig.azure_redis(redis_config))
) as memory:
	memory_id = memory.store("The customer prefers email.")
	record = memory.retrieve(memory_id)
	assert record is not None
	assert record["content"] == "The customer prefers email."
	assert memory.delete(memory_id)
```

The redis-entraid streaming provider derives the Redis username from the token's object ID and refreshes credentials for pooled connections. Async token acquisition runs off the event loop. Closing the backend stops owned renewal resources and closes its Azure credential; stop application operations before closing. Do not reuse a closed facade/provider concurrently with ongoing work.

For Key Vault-backed access keys, use `auth_method="keyvault"`, `keyvault_url=os.environ["AZURE_KEYVAULT_URL"]`, and `secret_name=os.environ["AZURE_REDIS_SECRET_NAME"]` instead of the Entra fields. Grant the application identity secret-read access, such as Key Vault Secrets User. That identity authenticates to Key Vault; Redis still uses the retrieved access key. Recreate the connection after key rotation. Direct access-key configurations also forward `username` when supplied.

Never embed credentials in source code. References: [Microsoft Redis Python authentication example](https://learn.microsoft.com/azure/redis/python-get-started), [DefaultAzureCredential](https://learn.microsoft.com/python/api/azure-identity/azure.identity.defaultazurecredential), and [Key Vault RBAC](https://learn.microsoft.com/azure/key-vault/general/rbac-guide).

> [!WARNING]
> These paths are tested offline with synthetic tokens, mocked identity, and fakeredis, not a live Azure service. Verify long-lived connections across token refresh, reconnect/failover, chosen endpoint policy, network restrictions, and least-privilege permissions against your deployment before production.

## Dependency Policy

`pyproject.toml` is the authoritative dependency manifest. Runtime requirements use bounded compatibility ranges. Prefer an actual upstream-designated LTS release where one exists; otherwise use maintained stable releases. Do not label ordinary package releases as LTS.

Semantic Kernel 1.46 currently requires Pydantic below 2.14. The base range starts at maintained Pydantic 2.13.5 so this optional extra resolves without conflicting with NexaMem. The `dev` extra includes all framework dependencies and is substantially larger than a base install; applications should install only the extras they need. The Agent Framework adapter targets the public 1.22 history-provider contract; newer minor versions require revalidation.

`requirements-dev.lock` contains exact development pins generated with pip-tools under **Windows and Python 3.13**. It is not a universal lock and contains no artifact hashes. It deliberately omits machine-specific index settings. Use it only with a compatible platform/interpreter and a trusted configured package index:

```shell
python -m pip install -r requirements-dev.lock
python -m pip install --no-deps -e .
```

To regenerate under that platform/runtime:

```shell
python -m piptools compile pyproject.toml --extra dev --strip-extras --no-emit-index-url --no-emit-trusted-host --output-file requirements-dev.lock
```

CI resolves declared ranges for each supported runtime instead of imposing a Windows 3.13 lock on other systems. The lock is reproducible version selection for its stated environment, not hash-verified or cross-platform supply-chain assurance. Keep TLS certificate verification enabled and use your organization's approved package source.

## Verify

```shell
python -c "import nexamem; print(nexamem.__version__)"
```

For contributors with the `dev` extra installed, run the offline suite from the repository root:

```shell
python -m pytest tests/ -m "not integration" --cov=nexamem --cov-report=term-missing --cov-fail-under=90
```

For isolated wheel/source verification and release gates, see [contributing](CONTRIBUTING.md). If an existing virtual environment refers to a removed interpreter, create a new environment rather than mixing installations.
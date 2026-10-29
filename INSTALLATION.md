# Installation

## Python Support

The stabilization branch requires Python **3.11+**. CI targets CPython 3.11, 3.12, and 3.13 on Linux, macOS, and Windows; remote matrix verification is still pending. Python 3.8, 3.9, and 3.10 are no longer supported by this checkout. Newer Python versions are not yet certified by the CI matrix.

Published `0.4.2` artifacts predate this work. Installing from PyPI does not install these unreleased fixes.

## Set Up With pip

Create an isolated environment using your selected supported interpreter:

```shell
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

For a published release:

```shell
python -m pip install nexamem
```

For this unreleased checkout, run from the repository root after activating the environment:

```shell
python -m pip install -e .
python -m pip check
```

For contributors who also need tests, lint, typing, and packaging tools:

```shell
python -m pip install -e ".[dev]"
python -m pip check
```

Alternatively, `python -m pip install -r requirements-test.txt` installs the same development extra. `requirements.txt` installs the local project. No uv tooling is used.

## Extras

| Extra | Purpose |
| --- | --- |
| `telemetry` | OpenTelemetry API; your application supplies its SDK and exporter |
| `appinsights` | Telemetry API plus the Azure Monitor OpenTelemetry distribution |
| `dev` | pytest, coverage, Ruff, mypy, build, Twine, pip-tools, OpenTelemetry SDK for tests, and contributor tooling |
| `docs` | MkDocs and Python API documentation tooling |
| `perf` | Benchmark and memory-profiling tools |
| `all` | The three development extras: `dev`, `docs`, and `perf`; not `appinsights` |

Azure identity, Key Vault, Redis, and fakeredis dependencies remain included in the base package. Do not use the nonexistent `nexamem[azure]` extra.

For optional observability in this checkout, install `python -m pip install -e ".[telemetry]"` or `python -m pip install -e ".[appinsights]"`. Combine extras as needed, for example `python -m pip install -e ".[dev,appinsights]"`. These extras are unreleased; do not expect published `0.4.2` to provide them. See [observability setup](README.md#observability) for application-owned provider/exporter configuration and privacy limits.

## First Local Run

Run the [sync or async quick start](README.md#quick-start) after installation. Both use process-local memory, so they require no Azure account or environment variables. Successful assertions produce no output. Use `StorageConfig.file("./memory-data")` or `StorageConfig.sqlite("./memory.db")` for persistence between processes; relative paths are resolved from the application's working directory. Local async storage still performs synchronous I/O.

In a notebook with an event loop already running, define `main()` from the async example and call `await main()` instead of `asyncio.run(main())`.

## Azure Cache for Redis

Azure services are provisioned separately; installing NexaMem does not create resources. For a Key Vault-backed configuration:

1. Provide an existing Azure Cache for Redis endpoint ending in `.redis.cache.windows.net`. The default connection uses TLS on port `6380`; allow the application through the cache's network/firewall controls. Azure Managed Redis hostnames are not supported by this adapter.
2. Store a Redis access key as a Key Vault secret. Give the application's managed identity permission to read that secret, such as the Key Vault Secrets User role scoped to the vault or secret. For local development, provide a credential supported by `DefaultAzureCredential` with equivalent access.
3. Set these environment variables in the application host, then construct the memory facade:

| Variable | Value |
| --- | --- |
| `AZURE_REDIS_HOSTNAME` | Cache hostname without a URL scheme |
| `AZURE_KEYVAULT_URL` | Vault URL, such as `https://your-vault.vault.azure.net/` |
| `AZURE_REDIS_SECRET_NAME` | Name of the secret containing the Redis access key |

```python
import os

from nexamem import AIMemory, AIMemoryConfig, AzureRedisConfig, StorageConfig

redis_config = AzureRedisConfig(
	hostname=os.environ["AZURE_REDIS_HOSTNAME"],
	auth_method="keyvault",
	keyvault_url=os.environ["AZURE_KEYVAULT_URL"],
	secret_name=os.environ["AZURE_REDIS_SECRET_NAME"],
)
memory = AIMemory(
	AIMemoryConfig(default_scope="application", storage=StorageConfig.azure_redis(redis_config))
)
memory_id = memory.store("The customer prefers email.")
record = memory.retrieve(memory_id)
assert record is not None
assert record["content"] == "The customer prefers email."
assert memory.delete(memory_id)
```

The application identity authenticates to Key Vault; Redis still uses the retrieved access key. Do not embed keys in source code or documentation. This example needs real Azure connectivity and permissions and has not been validated against a live service. See [DefaultAzureCredential](https://learn.microsoft.com/python/api/azure-identity/azure.identity.defaultazurecredential) and [Key Vault RBAC](https://learn.microsoft.com/azure/key-vault/general/rbac-guide).

> [!WARNING]
> Entra ID configuration fields are present, but the current Redis adapter does not forward the configured Redis username or renew access tokens. Do not treat direct Entra ID Redis authentication as a production-ready setup. Key Vault secret rotation also requires recreating the connection to load a changed key. Review the [backend limitations](NEW_ARCHITECTURE.md#azure-redis-configuration) before deployment.

## Dependency Policy

`pyproject.toml` is the authoritative dependency manifest. Runtime requirements use bounded compatibility ranges. Prefer an actual upstream-designated LTS release where one exists; otherwise use maintained stable releases. Do not label ordinary package releases as LTS.

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
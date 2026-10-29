# Changelog

## 1.0.0 - Unreleased

Stability work in progress. This is not a published release; package metadata remains `0.4.2` pending completion of release gates.

### Added

- Optional `telemetry` and `appinsights` extras for OpenTelemetry operation spans, counters, and duration histograms on the public sync/async memory facade. Providers and exporters remain application-owned; memory contents and identifiers are not emitted.
- Azure Monitor/Application Insights setup guidance with managed identity and explicit Azure-focused positioning.
- Passwordless Redis authentication through redis-entraid streaming credentials, token-derived usernames, renewal callbacks, and owned-resource cleanup. Accept Azure Managed Redis hostnames with TLS port 10000 and database 0 constraints; retain Azure Cache for Redis defaults.
- Portable logical expiry via `default_ttl_sec`, per-write `ttl_sec`, channel TTL, and `purge_expired`, with reserved persisted expiry metadata and live-record filtering across all backends.
- Sync/async context managers and caller-owned DI storage semantics. File/SQLite async data I/O runs in worker threads and remains serialized through repeated cancellation.
- Optional LangChain typed history, AutoGen text/Markdown memory, Semantic Kernel typed history snapshots, and Microsoft Agent Framework `HistoryProvider` integrations, with real-interface offline tests.
- Framework setup examples and Microsoft Foundry hosting guidance; no separate Foundry adapter or replacement of service-managed state.

### Changed

- Raise the minimum Python version to 3.11; target CI on 3.11, 3.12, and 3.13.
- Upgrade maintained dependency ranges and use pip, venv, pip-tools, setuptools, build, and Twine without requiring uv.
- Allow Pydantic from 2.13.5 for compatibility with Semantic Kernel's current below-2.14 constraint; keep framework SDKs optional outside the development extra.
- Consolidate CI and require offline unit line coverage of at least 90%, including legacy modules, plus blocking lint, format, typing, and installed-distribution checks.
- Build one wheel and sdist per CI run; separate manual candidate publishing from exact stable-tag production publishing. TestPyPI retries skip existing files; production errors remain blocking.

### Fixed

- Preserve creation timestamps and remove stale scope-index entries when memories move between scopes.
- Encode file identifiers safely and atomically replace record files so serialization errors do not destroy previous content.
- Close SQLite adapter connections explicitly and handle actual JSON serialization exceptions.
- Restore real legacy initialization/configuration helpers and avoid reading Redis index keys as message strings.
- Avoid metrics snapshot lock recursion and use valid Redis stream range parameters for sync audit retrieval.
- Validate authentication settings after all fields have been parsed; require TLS certificate verification on repaired Redis connections.
- Preserve Redis scope indexes during overwrites and erase targeted collection fields without deleting other users' payloads.
- Include environment in new-facade compatibility channel scopes and decode UTF-8 byte writes as text.
- Resolve strict typing errors across the complete package, including legacy modules, without weakening the gate.
- Handle Redis audit stream response layouts and byte/text fields; reject missing Key Vault values and mismatched backend configurations explicitly.

### Compatibility and Limitations

- Legacy API exports remain available. No automatic file-key or channel-scope migration is provided; see [migration notes](LEGACY_API.md).
- Encryption, quota/PII enforcement, immutable audit retention, physical-erasure deadlines, and live Azure certification are not supplied. Logical expiry is facade-level and does not change legacy/raw-storage guarantees. See [architecture](NEW_ARCHITECTURE.md).
- Redis uses a standalone/proxy client, not OSS-cluster routing. LangChain support targets the deprecated 1.x history interface, not LangGraph. Adapter ordering is single-writer, not distributed transactional persistence.
- Full CI-matrix verification remains a release gate. Local strict mypy passes across the package. See [status](PROJECT_STATUS.md).
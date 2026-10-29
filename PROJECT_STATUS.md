# Release Status

## 1.0.0rc1: Release Candidate

The target is a 1.0.0 stability release with approved authentication, lifecycle, retention, and optional integration improvements. Package and module versions are `1.0.0rc1`; stable 1.0.0 is not released. The TestPyPI candidate path is approved, not a production release tag or PyPI upload. Existing PyPI/TestPyPI versions are immutable: changed content requires a new version.

| Area | State |
| --- | --- |
| Python floor | Raised to 3.11; CI matrix targets 3.11, 3.12, 3.13 |
| Dependency tooling | pip, venv, pip-tools, setuptools, build, Twine; no uv requirement |
| Unit coverage | Complete offline package suite, including legacy modules and real framework interfaces; blocking 90% overall line-coverage gate |
| Regression fixes | Storage index updates, safe file writes, SQLite closure, legacy initialization, metrics deadlock, audit stream reads, Redis scope handling and TLS |
| CI | Consolidated reusable workflow; tests, Ruff, mypy, and installed artifacts are blocking |
| Distribution verification | Wheel and sdist metadata plus independent clean installations |
| Strict typing | All 33 package source files pass strict mypy without relaxing settings |
| Authentication | Renewable Entra Redis credentials, owned cleanup, Managed Redis endpoint defaults; live Azure validation still pending |
| Async/lifecycle | Thread-backed local data I/O, cancellation serialization, facade context managers and borrowed-storage semantics |
| Retention | Logical per-record expiry and explicit purge; not audit/backup erasure or background physical deletion |
| Integrations | LangChain, AutoGen, Semantic Kernel, Agent Framework; Foundry hosting documentation, not a fifth adapter |
| Cross-platform verification | Published candidate commit `442f201` passed all 17 reusable CI jobs across the supported matrix |
| Publication | `1.0.0rc1` published to TestPyPI through OIDC and independently verified; no production upload authorized |

## Remote Verification

Commit `79f0d66` passed [CI run 40905994705](https://github.com/microsoft/nexamem/actions/runs/40905994705) and [CodeQL run 40905993954](https://github.com/microsoft/nexamem/actions/runs/40905993954). All nine Python 3.11/3.12/3.13 test jobs across Linux, macOS, and Windows, quality checks, package build, and six clean distribution-install jobs succeeded. This verifies that baseline, not a subsequently changed candidate or live Azure deployment.

Candidate commit `442f201` passed [publish workflow 40916874870](https://github.com/microsoft/nexamem/actions/runs/40916874870), including version validation, all 17 reusable CI jobs, and TestPyPI publication. The production PyPI job was skipped. The [TestPyPI release](https://test.pypi.org/project/nexamem/1.0.0rc1/) contains wheel and source archives whose SHA-256 digests exactly match that workflow's build artifacts:

```text
nexamem-1.0.0rc1-py3-none-any.whl  004c13c2fdbe31052a33448ef9c0f5bb3e52995233d4cc9713e0faa558af1be2
nexamem-1.0.0rc1.tar.gz           1391d57c68d9e305e3dd89fdde25efd2ce1cd09ff32812167668e68fb2a13e8b
```

Both downloaded TestPyPI archives passed strict Twine checks and independent clean installations on Windows/Python 3.11.12 and 3.13.15. Dependencies came from the approved package feed, not a combined TestPyPI/PyPI index. Isolated smoke tests ran outside the checkout and verified version metadata, local persistence, async operations, logical expiry, legacy APIs, and shipped adapter modules. This documentation follow-up does not rebuild or replace the published archives.

## Local Verification

- Windows/Python 3.11.12 and 3.13.15: 203 offline tests pass on each runtime, with 92.61% whole-package line coverage (3290 statements), including legacy modules and all four adapters.
- Strict mypy passes across 33 source modules on both runtimes. Ruff lint and formatting checks pass; both development environments pass `pip check`.
- Eight local README, SQLite persistence, and framework examples execute successfully on both Python 3.11 and 3.13. A fresh Python 3.11 source install passes `pip check` and all four base examples without framework extras. Local documentation links and example syntax are checked separately from live-service behavior.
- Validation-only wheel and sdist in `dist-release/frameworks/` pass strict Twine checks and independent clean base installations on Python 3.11 and 3.13. Smoke tests cover local CRUD, logical expiry, context managers, legacy APIs, and shipped adapter modules without installing framework extras.
- The Windows/Python 3.13 development lock was regenerated with pip-tools. Candidate metadata is now `1.0.0rc1`; prior local artifacts remain validation-only and must not be uploaded under a reused version.

## Remaining Gates

- Review the published candidate and migration notes; candidate CI and installed-distribution verification are complete.
- Recheck offline unit line coverage, lint, formatting, dependency consistency, the supported CI matrix, and clean installed artifacts after any code changes or the final stable version bump.
- Validate live Azure/Foundry networking, data-plane permissions, token refresh/reconnect/failover, and intended Managed Redis endpoint policy before production use.
- Confirm production PyPI trusted publishing and appropriate environment/review protections separately; successful TestPyPI OIDC publishing does not verify production settings.
- Approve a final stable version/tag and protected production environment before publication.

Passing local tests does not establish live Azure compatibility, regulatory compliance, automatic encryption, quota/PII enforcement, or physical-erasure guarantees. The documentation records those limitations rather than promising them.

See [changes](CHANGELOG.md), [contributor commands](CONTRIBUTING.md), [architecture](NEW_ARCHITECTURE.md), and [security](SECURITY.md).
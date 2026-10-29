# Release Status

## 1.0.0 Stabilization: Unreleased

The target is a stability release with approved authentication, lifecycle, retention, and optional integration improvements. Package and module versions remain `0.4.2` until the release gates pass. Existing PyPI/TestPyPI versions are immutable: locally rebuilt `0.4.2` artifacts must not be uploaded as new content.

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
| Cross-platform certification | Pending successful GitHub Actions matrix; local Windows checks are not equivalent |
| Publication | Not performed; no release tag or production upload authorized |

## Local Verification

- Windows/Python 3.11.12 and 3.13.15: 203 offline tests pass on each runtime, with 92.61% whole-package line coverage (3290 statements), including legacy modules and all four adapters.
- Strict mypy passes across 33 source modules on both runtimes. Ruff lint and formatting checks pass; both development environments pass `pip check`.
- Eight local README, SQLite persistence, and framework examples execute successfully on both Python 3.11 and 3.13. A fresh Python 3.11 source install passes `pip check` and all four base examples without framework extras. Local documentation links and example syntax are checked separately from live-service behavior.
- Validation-only wheel and sdist in `dist-release/frameworks/` pass strict Twine checks and independent clean base installations on Python 3.11 and 3.13. Smoke tests cover local CRUD, logical expiry, context managers, legacy APIs, and shipped adapter modules without installing framework extras.
- The Windows/Python 3.13 development lock was regenerated with pip-tools. No commit, release tag, version bump, or upload was performed.

## Remaining Gates

- Run the complete supported Python/OS CI matrix after review.
- Recheck offline unit line coverage, lint, formatting, dependency consistency, and clean installed artifacts on the final candidate.
- Validate live Azure/Foundry networking, data-plane permissions, token refresh/reconnect/failover, and intended Managed Redis endpoint policy before production use.
- Choose a unique candidate version, update both version locations, review migration notes, and authorize TestPyPI verification.
- Approve a final stable version/tag and protected production environment before publication.

Passing local tests does not establish live Azure compatibility, regulatory compliance, automatic encryption, quota/PII enforcement, or physical-erasure guarantees. The documentation records those limitations rather than promising them.

See [changes](CHANGELOG.md), [contributor commands](CONTRIBUTING.md), [architecture](NEW_ARCHITECTURE.md), and [security](SECURITY.md).
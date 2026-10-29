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
| Cross-platform verification | Stabilization baseline passed all 17 CI jobs; rerun the matrix for candidate changes |
| Publication | TestPyPI candidate publication/verification is a separate gate; no production upload authorized |

## Remote Baseline Verification

Commit `79f0d66` passed [CI run 40905994705](https://github.com/microsoft/nexamem/actions/runs/40905994705) and [CodeQL run 40905993954](https://github.com/microsoft/nexamem/actions/runs/40905993954). All nine Python 3.11/3.12/3.13 test jobs across Linux, macOS, and Windows, quality checks, package build, and six clean distribution-install jobs succeeded. This verifies that baseline, not a subsequently changed candidate or live Azure deployment.

## Local Verification

- Windows/Python 3.11.12 and 3.13.15: 203 offline tests pass on each runtime, with 92.61% whole-package line coverage (3290 statements), including legacy modules and all four adapters.
- Strict mypy passes across 33 source modules on both runtimes. Ruff lint and formatting checks pass; both development environments pass `pip check`.
- Eight local README, SQLite persistence, and framework examples execute successfully on both Python 3.11 and 3.13. A fresh Python 3.11 source install passes `pip check` and all four base examples without framework extras. Local documentation links and example syntax are checked separately from live-service behavior.
- Validation-only wheel and sdist in `dist-release/frameworks/` pass strict Twine checks and independent clean base installations on Python 3.11 and 3.13. Smoke tests cover local CRUD, logical expiry, context managers, legacy APIs, and shipped adapter modules without installing framework extras.
- The Windows/Python 3.13 development lock was regenerated with pip-tools. Candidate metadata is now `1.0.0rc1`; prior local artifacts remain validation-only and must not be uploaded under a reused version.

## Remaining Gates

- Run the complete supported Python/OS CI matrix on the release-candidate commit; baseline verification is complete.
- Recheck offline unit line coverage, lint, formatting, dependency consistency, and clean installed artifacts on the final candidate.
- Validate live Azure/Foundry networking, data-plane permissions, token refresh/reconnect/failover, and intended Managed Redis endpoint policy before production use.
- Publish the approved unique candidate to TestPyPI, then verify the uploaded distributions in clean environments. Registry trusted-publisher configuration must match the workflow and environment.
- Approve a final stable version/tag and protected production environment before publication.

Passing local tests does not establish live Azure compatibility, regulatory compliance, automatic encryption, quota/PII enforcement, or physical-erasure guarantees. The documentation records those limitations rather than promising them.

See [changes](CHANGELOG.md), [contributor commands](CONTRIBUTING.md), [architecture](NEW_ARCHITECTURE.md), and [security](SECURITY.md).
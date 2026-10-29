# Release Status

## 1.0.0 Stabilization: Unreleased

The target is a stability release, not a new feature architecture. Package and module versions remain `0.4.2` until the release gates pass. Existing PyPI/TestPyPI versions are immutable: locally rebuilt `0.4.2` artifacts must not be uploaded as new content.

| Area | State |
| --- | --- |
| Python floor | Raised to 3.11; CI matrix targets 3.11, 3.12, 3.13 |
| Dependency tooling | pip, venv, pip-tools, setuptools, build, Twine; no uv requirement |
| Unit coverage | 171 offline unit tests pass on Windows/Python 3.11 and 3.13; at least 90% overall line coverage, including legacy code |
| Regression fixes | Storage index updates, safe file writes, SQLite closure, legacy initialization, metrics deadlock, audit stream reads, Redis scope handling and TLS |
| CI | Consolidated reusable workflow; tests, Ruff, mypy, and installed artifacts are blocking |
| Distribution verification | Wheel and sdist metadata plus independent clean installations |
| Strict typing | All 24 package source files pass the blocking mypy check; previous 284 errors resolved without relaxing settings |
| Cross-platform certification | Pending successful GitHub Actions matrix; local Windows checks are not equivalent |
| Publication | Not performed; no release tag or production upload authorized |

## Remaining Gates

- Run the complete supported Python/OS CI matrix after review.
- Recheck offline unit line coverage, lint, formatting, dependency consistency, and clean installed artifacts on the final candidate.
- Choose a unique candidate version, update both version locations, review migration notes, and authorize TestPyPI verification.
- Approve a final stable version/tag and protected production environment before publication.

Passing local tests does not establish live Azure compatibility, regulatory compliance, automatic encryption, or policy enforcement. The documentation records those limitations rather than promising them.

See [changes](CHANGELOG.md), [contributor commands](CONTRIBUTING.md), [architecture](NEW_ARCHITECTURE.md), and [security](SECURITY.md).